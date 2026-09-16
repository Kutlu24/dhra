"""Corpus versioning -- DHRA_BUILD_SPEC.md section 5.2.

A corpus version is an immutable manifest: the set of included item ids,
their active representation ids, the active exclusion set, and the
assertion-preference set. Its id is the hash of the manifest.

`corpus_version_at` is a pure function: fold events up to `seq`, no I/O
beyond reading the log. Every search result, aggregate, claim and export
must record the corpus version it was computed against (I8).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from dhra.store.events import EventLog
from dhra.store.projection import Projection, fold


@dataclass(frozen=True)
class CorpusVersion:
    seq: int
    item_ids: tuple[str, ...]
    active_rep_ids: tuple[tuple[str, str], ...]  # (item_id, rep_id), sorted
    exclusions: tuple[tuple[str, str], ...]  # (item_id, reason), sorted
    assertion_preferences: tuple[tuple[str, str, str], ...]  # (item_id, predicate, assertion_id)
    manifest_hash: str

    def to_manifest_dict(self) -> dict:
        return {
            "seq": self.seq,
            "item_ids": list(self.item_ids),
            "active_rep_ids": [list(pair) for pair in self.active_rep_ids],
            "exclusions": [list(pair) for pair in self.exclusions],
            "assertion_preferences": [list(triple) for triple in self.assertion_preferences],
        }


def _hash_manifest(manifest_without_hash: dict) -> str:
    canonical = json.dumps(manifest_without_hash, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def corpus_version_from_projection(projection: Projection) -> CorpusVersion:
    item_ids = tuple(projection.active_item_ids())
    active_rep_ids = tuple(
        sorted(
            (item_id, rep_id)
            for item_id in projection.items
            if (rep_id := projection.active_representation_id(item_id)) is not None
        )
    )
    exclusions = tuple(
        sorted((item_id, excl.reason.value) for item_id, excl in projection.active_exclusions.items())
    )
    assertion_preferences = tuple(
        sorted((item_id, predicate, assertion_id) for (item_id, predicate), assertion_id in projection.assertion_preferences.items())
    )
    manifest = {
        "seq": projection.last_seq,
        "item_ids": list(item_ids),
        "active_rep_ids": [list(pair) for pair in active_rep_ids],
        "exclusions": [list(pair) for pair in exclusions],
        "assertion_preferences": [list(triple) for triple in assertion_preferences],
    }
    manifest_hash = _hash_manifest(manifest)
    return CorpusVersion(
        seq=projection.last_seq,
        item_ids=item_ids,
        active_rep_ids=active_rep_ids,
        exclusions=exclusions,
        assertion_preferences=assertion_preferences,
        manifest_hash=manifest_hash,
    )


def corpus_version_at(event_log: EventLog, seq: int | None = None) -> CorpusVersion:
    """Fold events up to `seq` (or the full log, if None) into a manifest."""
    if seq is None:
        events = event_log.read_all()
    else:
        events = event_log.read_up_to(seq)
    projection = fold(events)
    return corpus_version_from_projection(projection)
