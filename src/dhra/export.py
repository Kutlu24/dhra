"""Export and reconstruction -- DHRA_BUILD_SPEC.md I12 / section 13.1 test_export_round_trip.

`export_corpus` writes a self-describing, flat, JSONL/JSON export that a
generic script -- not this application -- can walk to reconstruct corpus
state and verify every checksum. `reconstruct_from_export` is exactly
that generic script: it imports nothing from dhra.models or dhra.store,
only stdlib, to keep the "application code absent from the
reconstruction path" property honest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dhra.corpus import corpus_version_at
from dhra.store.blobs import BlobStore
from dhra.store.events import EventLog
from dhra.store.projection import fold

README_TEMPLATE = """\
# DHRA corpus export

This directory is a complete, self-contained record of one corpus version.
It can be reconstructed and audited without the DHRA application:

- `manifest.json` -- the corpus version: included item ids, active
  representation per item, active exclusions, assertion preferences, and
  `manifest_hash` (sha256 of the canonical manifest).
- `items.jsonl` -- one JSON object per acquired item (one line each),
  including its `blob_sha256`.
- `blobs/<sha256[0:2]>/<sha256>` -- the original bytes of every item
  referenced above. Verify each with: sha256(file bytes) == filename.
- `representations.jsonl` -- every derived representation (transcription,
  translation, ...), each carrying `parent_rep_id` so the chain back to
  the blob is walkable, and `producer`/`producer_version` for
  reproducibility.
- `assertions.jsonl` -- every catalogue/researcher/tool claim about an
  item, with `original_expression` preserved verbatim alongside any
  normalised `value`.
- `exclusions.jsonl` -- full exclusion history (not just active
  exclusions), each with `reason`, `actor`, timestamp, and whether it was
  later reversed.
- `events.jsonl` -- verbatim copy of the underlying event log up to this
  version's `seq`, for anyone who does want to replay it.

To reconstruct: read `items.jsonl`, verify each blob against its file in
`blobs/`, then attach representations/assertions/exclusions by
`item_id`. `manifest.json` tells you which item ids and which
representation ids are the *active* corpus (the rest is history).

Note (spec section 10.2): this export gives **process reproducibility**
(corpus, provenance, exclusions) only. It contains no generated prose,
and none is promised to be reproducible even if it existed.
"""


def export_corpus(store_root: str | Path, out_dir: str | Path, seq: int | None = None) -> Path:
    store_root = Path(store_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    event_log = EventLog(store_root / "events.jsonl")
    blob_store = BlobStore(store_root / "blobs")

    version = corpus_version_at(event_log, seq)
    events = list(event_log.read_up_to(seq) if seq is not None else event_log.read_all())
    projection = fold(events)

    (out_dir / "manifest.json").write_text(
        json.dumps({**version.to_manifest_dict(), "manifest_hash": version.manifest_hash}, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with (out_dir / "events.jsonl").open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n")

    with (out_dir / "items.jsonl").open("w", encoding="utf-8") as f:
        for item in projection.items.values():
            excl = projection.active_exclusions.get(item.item_id)
            f.write(
                json.dumps(
                    {
                        "item_id": item.item_id,
                        "blob_sha256": item.blob_sha256,
                        "media_type": item.media_type,
                        "byte_length": item.byte_length,
                        "source_id": item.acquisition.source_id,
                        "retrieved_at": item.acquisition.retrieved_at.isoformat(),
                        "method": item.acquisition.method,
                        "access_basis": item.acquisition.access_basis,
                        "licence_id": item.acquisition.licence_id,
                        "redistributable": item.acquisition.redistributable,
                        "original_reference": item.acquisition.original_reference,
                        "currently_excluded": excl is not None,
                        "exclusion_reason": excl.reason.value if excl else None,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
            blob_dir = out_dir / "blobs" / item.blob_sha256[:2]
            blob_dir.mkdir(parents=True, exist_ok=True)
            (blob_dir / item.blob_sha256).write_bytes(blob_store.get(item.blob_sha256))

    with (out_dir / "representations.jsonl").open("w", encoding="utf-8") as f:
        for rep in projection.representations.values():
            f.write(
                json.dumps(
                    {
                        "rep_id": rep.rep_id,
                        "item_id": rep.item_id,
                        "parent_rep_id": rep.parent_rep_id,
                        "kind": rep.kind,
                        "producer": rep.producer,
                        "producer_version": rep.producer_version,
                        "parameters": rep.parameters,
                        "created_at": rep.created_at.isoformat(),
                        "text": rep.text,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    with (out_dir / "assertions.jsonl").open("w", encoding="utf-8") as f:
        for a in projection.assertions.values():
            f.write(
                json.dumps(
                    {
                        "assertion_id": a.assertion_id,
                        "subject_item_id": a.subject_item_id,
                        "predicate": a.predicate,
                        "value": a.value,
                        "original_expression": a.original_expression,
                        "asserted_by": a.asserted_by,
                        "confidence": a.confidence,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    with (out_dir / "exclusions.jsonl").open("w", encoding="utf-8") as f:
        for item_id, history in projection.exclusion_history.items():
            still_active = item_id in projection.active_exclusions
            last_index = len(history) - 1
            for idx, excl in enumerate(history):
                f.write(
                    json.dumps(
                        {
                            "item_id": excl.item_id,
                            "reason": excl.reason.value,
                            "actor": excl.actor,
                            "ts": excl.ts.isoformat(),
                            "threshold": excl.threshold,
                            "observed": excl.observed,
                            "currently_active": still_active and idx == last_index,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )

    (out_dir / "README.md").write_text(README_TEMPLATE, encoding="utf-8")
    return out_dir


# --- Generic reconstruction: stdlib only, no dhra.models / dhra.store imports ---


def reconstruct_from_export(export_dir: str | Path) -> dict:
    """Rebuild corpus state from an export directory using nothing but stdlib.

    This stands in for "a researcher with the export but not this
    software" (I12 / test_export_round_trip). It must not import
    dhra.models or dhra.store.
    """
    export_dir = Path(export_dir)

    def _read_jsonl(name: str) -> list[dict]:
        path = export_dir / name
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    manifest = json.loads((export_dir / "manifest.json").read_text(encoding="utf-8"))
    items = {rec["item_id"]: rec for rec in _read_jsonl("items.jsonl")}
    representations = {rec["rep_id"]: rec for rec in _read_jsonl("representations.jsonl")}
    assertions = {rec["assertion_id"]: rec for rec in _read_jsonl("assertions.jsonl")}
    exclusions = _read_jsonl("exclusions.jsonl")

    checksum_errors = []
    for item_id, rec in items.items():
        sha256 = rec["blob_sha256"]
        blob_path = export_dir / "blobs" / sha256[:2] / sha256
        if not blob_path.exists():
            checksum_errors.append(f"{item_id}: blob file missing for {sha256}")
            continue
        actual = hashlib.sha256(blob_path.read_bytes()).hexdigest()
        if actual != sha256:
            checksum_errors.append(f"{item_id}: blob checksum mismatch ({actual} != {sha256})")

    manifest_body = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    canonical = json.dumps(manifest_body, sort_keys=True, ensure_ascii=False)
    recomputed_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    manifest_hash_ok = recomputed_hash == manifest["manifest_hash"]

    return {
        "manifest": manifest,
        "manifest_hash_ok": manifest_hash_ok,
        "items": items,
        "representations": representations,
        "assertions": assertions,
        "exclusions": exclusions,
        "checksum_errors": checksum_errors,
    }
