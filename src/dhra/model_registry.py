"""Read-only view of the lab's shared model registry (`models.yaml`), plus
the seam where a model gateway will plug in.

The registry is *published* by the serving-atr-inference gateway ("Do not
edit -- the next start overwrites it"), so this module only reads it. DHRA
works with or without it: `DHRA_MODELS_REGISTRY` unset (e.g. the Render
demo) means no model picker is shown and nothing here runs.

Calling a model needs the gateway's address and request contract, which are
not yet configured. Until `DHRA_ATR_GATEWAY_URL` is set AND `_call` below is
filled in from the gateway's real `/recognize` contract, choosing a registry
model fails with an explicit `ModelGatewayError` -- never a silent fallback
to a different engine, because the engine that produced a transcription is
recorded as provenance (spec section 4.3).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from dhra.transcribe import TranscriptionResult

REGISTRY_ENV = "DHRA_MODELS_REGISTRY"
GATEWAY_ENV = "DHRA_ATR_GATEWAY_URL"


class ModelGatewayError(Exception):
    """A registry model was chosen but cannot be run (user-facing text)."""


@dataclass(frozen=True)
class ModelEntry:
    id: str
    engine: str
    kind: str  # "htr" (image -> text) or "llm" (general instruction model)
    task: str
    level: str
    languages: tuple[str, ...]
    scripts: tuple[str, ...]
    centuries: tuple[int, ...]
    description: str
    enabled: bool
    hf_repo: str | None = None
    local_path: str | None = None

    @property
    def label(self) -> str:
        bits = [b for b in (",".join(self.languages), ",".join(self.scripts)) if b]
        if self.centuries:
            bits.append(f"{min(self.centuries)}-{max(self.centuries)}c")
        meta = " · ".join(bits)
        return f"{self.id} [{self.engine}{', ' + self.level if self.level else ''}]" + (f" — {meta}" if meta else "")


def _kind(raw: dict) -> str:
    # The registry labels the general-purpose Apertus instruction model
    # task=htr like the resolution probes built on it; its own description
    # is the only thing that says it is not an HTR model.
    if "general multimodal instruction model" in (raw.get("description") or ""):
        return "llm"
    return "htr"


def _entry(raw: dict) -> ModelEntry:
    return ModelEntry(
        id=str(raw["id"]),
        engine=str(raw.get("engine", "")),
        kind=_kind(raw),
        task=str(raw.get("task", "")),
        level=str(raw.get("level", "") or ""),
        languages=tuple(raw.get("languages") or ()),
        scripts=tuple(raw.get("scripts") or ()),
        centuries=tuple(int(c) for c in (raw.get("centuries") or ())),
        description=str(raw.get("description", "") or ""),
        enabled=bool(raw.get("enabled", True)),
        hf_repo=raw.get("hf_repo"),
        local_path=raw.get("local_path"),
    )


def registry_path_from_env() -> Path | None:
    raw = os.environ.get(REGISTRY_ENV)
    return Path(raw) if raw else None


def load_registry(path: str | Path) -> list[ModelEntry]:
    """`models.yaml` plus the per-model files in a sibling `trained/`
    directory (the trainer writes one yaml per model there; the file name
    is the id). Unreadable entries are skipped, not fatal."""
    path = Path(path)
    entries: dict[str, ModelEntry] = {}
    docs: list[dict] = []
    main = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    docs.extend(main.get("models") or [])
    trained = path.parent / "trained"
    if trained.is_dir():
        for f in sorted(trained.glob("*.yaml")):
            try:
                doc = yaml.safe_load(f.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError):
                continue
            if isinstance(doc, dict) and "id" in doc:
                docs.append(doc)
    for raw in docs:
        try:
            entry = _entry(raw)
        except (KeyError, TypeError, ValueError):
            continue
        entries.setdefault(entry.id, entry)
    return sorted(entries.values(), key=lambda e: e.id)


def usable(entries: list[ModelEntry], kind: str) -> list[ModelEntry]:
    return [e for e in entries if e.kind == kind and e.enabled]


def gateway_url_from_env() -> str | None:
    return os.environ.get(GATEWAY_ENV) or None


def require_gateway() -> str:
    url = gateway_url_from_env()
    if not url:
        raise ModelGatewayError(
            f"The model gateway is not configured yet (set {GATEWAY_ENV}). "
            "Choose the default engine, or try again once the gateway address is set."
        )
    raise ModelGatewayError(
        f"{GATEWAY_ENV} is set, but the gateway client is not implemented: "
        "the /recognize request/response contract has not been added yet."
    )


class GatewayTranscriber:
    """Transcriber backed by a registry model, via the gateway."""

    def __init__(self, entry: ModelEntry):
        self.entry = entry

    def transcribe(self, data: bytes) -> TranscriptionResult:
        require_gateway()  # raises until the contract is wired in
        raise AssertionError("unreachable")  # pragma: no cover

    # When the contract is known, replace the body above with a call that
    # returns TranscriptionResult(text, producer=f"gateway:{entry.id}",
    # producer_version=<model revision>, quality=Quality(...)).


__all__ = [
    "GatewayTranscriber", "ModelEntry", "ModelGatewayError",
    "gateway_url_from_env", "load_registry", "registry_path_from_env", "require_gateway", "usable",
]
