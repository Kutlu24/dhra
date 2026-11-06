"""Markdown status table: every model in the lab registry vs. what is
actually present in the local-to-the-share copy (`<models_dir>`).

    python scripts/models_status.py <models_dir> [--source <Textrecognition_Training dir>]

Status per model:
  copied     files present (HF repos: every file size matches the Hub)
  partial    some files present, not all (copy/download still running?)
  pending    not present yet, but the source exists (still to be copied)
  blocked    private or gated on Hugging Face (needs a token)
  missing    not present and no known source
Adapters (LoRA) are flagged: they need their base model to run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from huggingface_hub import HfApi

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dhra.model_registry import load_registry  # noqa: E402

import yaml  # noqa: E402


def _has_files(d: Path) -> bool:
    return d.is_dir() and any(p.is_file() and p.suffix != ".part" and p.name != "SOURCE.json" for p in d.rglob("*"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("models_dir", type=Path)
    ap.add_argument("--source", type=Path, default=None, help="original Textrecognition_Training dir")
    args = ap.parse_args()
    md = args.models_dir
    raw = {}
    main_doc = yaml.safe_load((md / "registry" / "models.yaml").read_text(encoding="utf-8"))
    for r in main_doc["models"]:
        raw[r["id"]] = r
    entries = load_registry(md / "registry" / "models.yaml")
    api = HfApi()
    rows = []
    for e in entries:
        r = raw.get(e.id, {})
        base = r.get("base_model") or ""
        note = "adapter (needs base)" if base else ""
        status, where = "missing", ""
        zen = md / "zenodo" / e.id
        if r.get("zenodo_id"):
            where = f"zenodo/{e.id}"
            status = "copied" if _has_files(zen) else "pending"
        elif r.get("hf_repo"):
            name = r["hf_repo"].replace("/", "__")
            hfd = md / "hf" / name
            alt = [md / "trained-ubelix" / e.id, md / "trained" / e.id]
            try:
                info = api.model_info(r["hf_repo"], files_metadata=True)
                if info.gated:
                    status, where = "blocked", f"gated: {r['hf_repo']}"
                else:
                    want = {s.rfilename: s.size for s in info.siblings}
                    have = {k for k, v in want.items() if (hfd / k).is_file() and (hfd / k).stat().st_size == v}
                    where = f"hf/{name}"
                    status = "copied" if have == set(want) else ("partial" if have else "pending")
            except Exception:
                found = next((a for a in alt if _has_files(a)), None)
                if found is not None:
                    status, where = "copied", f"{found.parent.name}/{found.name} (private on HF; lab copy)"
                else:
                    src_ok = args.source and any(
                        (args.source / sub / e.id).exists() for sub in ("trained-ubelix", "training_folder/trained"))
                    status = "pending" if src_ok else "blocked"
                    where = f"private: {r['hf_repo']}" + (" (source on share)" if src_ok else "")
        else:  # per-model yaml from registry/trained/ (kraken-*, trocr-*, ...)
            found = next((a for a in (md / "trained" / e.id, md / "trained-ubelix" / e.id) if _has_files(a)), None)
            if found is not None:
                status, where = "copied", f"{found.parent.name}/{found.name}"
            else:
                src_ok = args.source and any(
                    (args.source / sub / e.id).exists() for sub in ("trained-ubelix", "training_folder/trained"))
                status = "pending" if src_ok else "missing"
                where = "(source on share)" if src_ok else ""
        if not e.enabled:
            note = (note + "; " if note else "") + "disabled in registry"
        rows.append((e.id, e.kind, e.engine, status, where, base, note))
    order = {"blocked": 0, "missing": 1, "partial": 2, "pending": 3, "copied": 4}
    rows.sort(key=lambda x: (order[x[3]], x[0]))
    counts = {k: sum(1 for r in rows if r[3] == k) for k in order}
    print("# Model copy status\n")
    print("Totals: " + ", ".join(f"{k} {v}" for k, v in counts.items() if v) + f" (of {len(rows)})\n")
    print("| model | kind | engine | status | where | base model | note |\n|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(x or "" for x in r) + " |")


if __name__ == "__main__":
    main()
