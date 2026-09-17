"""Source registry -- DHRA_BUILD_SPEC.md section 9.2.

"The tool layer checks these BEFORE every request." A registry entry is
data, loaded from YAML exactly in the spec's own example shape; nothing
here executes network I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RateLimitSpec:
    requests: int
    per_seconds: float


@dataclass(frozen=True)
class SourceEntry:
    id: str
    name: str
    access: str  # "api" | "download" | "manual_upload" | ...
    rate_limit: RateLimitSpec
    identify_as: str
    bulk_download: str  # "permitted" | "prohibited"
    redistribution: str  # "permitted" | "prohibited"
    tdm_basis: str  # matches Acquisition.access_basis vocabulary
    robots_respected: bool
    notes: str = ""


def load_registry(path: str | Path) -> dict[str, SourceEntry]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    registry: dict[str, SourceEntry] = {}
    for entry in raw:
        rl = entry["rate_limit"]
        registry[entry["id"]] = SourceEntry(
            id=entry["id"],
            name=entry["name"],
            access=entry["access"],
            rate_limit=RateLimitSpec(requests=rl["requests"], per_seconds=rl["per_seconds"]),
            identify_as=entry["identify_as"],
            bulk_download=entry["bulk_download"],
            redistribution=entry["redistribution"],
            tdm_basis=entry["tdm_basis"],
            robots_respected=entry.get("robots_respected", True),
            notes=entry.get("notes", ""),
        )
    return registry
