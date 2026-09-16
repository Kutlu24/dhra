"""Fold events.jsonl into an in-memory projection, and materialise it into
derived.db (SQLite) -- DHRA_BUILD_SPEC.md section 3 & 5.2.

`fold()` is the pure function everything else is built on: corpus
versioning (dhra.corpus), the SQLite projection below, and the acceptance
test that deletes derived.db/index/ and rebuilds them, must all produce
identical state from the same event prefix.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dhra.models import (
    Acquisition,
    Assertion,
    Exclusion,
    ExclusionReason,
    Item,
    Quality,
    Representation,
)


@dataclass
class Projection:
    """Mutable fold accumulator. Never constructed except by `fold()`."""

    last_seq: int = 0
    items: dict[str, Item] = field(default_factory=dict)
    representations: dict[str, Representation] = field(default_factory=dict)
    reps_by_item: dict[str, list[str]] = field(default_factory=dict)
    assertions: dict[str, Assertion] = field(default_factory=dict)
    assertions_by_item: dict[str, list[str]] = field(default_factory=dict)
    assertion_preferences: dict[tuple[str, str], str] = field(default_factory=dict)
    active_exclusions: dict[str, Exclusion] = field(default_factory=dict)
    exclusion_history: dict[str, list[Exclusion]] = field(default_factory=dict)

    def active_item_ids(self) -> list[str]:
        return sorted(i for i in self.items if i not in self.active_exclusions)

    def active_representation_id(self, item_id: str) -> str | None:
        reps = self.reps_by_item.get(item_id) or []
        return reps[-1] if reps else None

    def representation_chain(self, rep_id: str) -> list[Representation]:
        """Walk parent_rep_id back to the blob. Raises if the chain is broken."""
        chain: list[Representation] = []
        current: str | None = rep_id
        seen: set[str] = set()
        while current is not None:
            if current in seen:
                raise ValueError(f"Cycle detected in representation chain at {current}")
            seen.add(current)
            rep = self.representations.get(current)
            if rep is None:
                raise ValueError(f"Representation chain broken: {current} not found")
            chain.append(rep)
            current = rep.parent_rep_id
        return chain


def _parse_dt(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)


def fold(events: Iterable[dict]) -> Projection:
    p = Projection()
    for event in events:
        p.last_seq = event["seq"]
        etype = event["type"]

        if etype == "item.acquired":
            acquisition = Acquisition(
                source_id=event["source_id"],
                retrieved_at=_parse_dt(event["retrieved_at"]),
                method=event["method"],
                request=event.get("request"),
                access_basis=event["access_basis"],
                licence_id=event.get("licence_id"),
                redistributable=event.get("redistributable"),
                original_reference=event.get("original_reference"),
            )
            item = Item(
                item_id=event["item_id"],
                blob_sha256=event["blob_sha256"],
                media_type=event["media_type"],
                byte_length=event["byte_length"],
                acquisition=acquisition,
            )
            p.items[item.item_id] = item
            p.reps_by_item.setdefault(item.item_id, [])
            p.assertions_by_item.setdefault(item.item_id, [])

        elif etype == "representation.created":
            quality_raw = event.get("quality")
            quality = (
                Quality(
                    mean_char_confidence=quality_raw.get("mean_char_confidence"),
                    per_span_confidence=tuple(
                        tuple(span) for span in quality_raw.get("per_span_confidence", [])
                    ),
                    script=quality_raw.get("script"),
                    manually_corrected=quality_raw.get("manually_corrected", False),
                    notes=quality_raw.get("notes"),
                )
                if quality_raw
                else None
            )
            rep = Representation(
                rep_id=event["rep_id"],
                item_id=event["item_id"],
                parent_rep_id=event.get("parent_rep_id"),
                kind=event["kind"],
                producer=event["producer"],
                producer_version=event["producer_version"],
                parameters=event.get("parameters", {}),
                created_at=_parse_dt(event["created_at"]),
                text=event["text"],
                quality=quality,
            )
            p.representations[rep.rep_id] = rep
            p.reps_by_item.setdefault(rep.item_id, []).append(rep.rep_id)

        elif etype == "assertion.added":
            loc_raw = event.get("evidence_locator")
            from dhra.models import Locator

            locator = Locator(**loc_raw) if loc_raw else None
            assertion = Assertion(
                assertion_id=event["assertion_id"],
                subject_item_id=event["subject_item_id"],
                predicate=event["predicate"],
                value=event["value"],
                original_expression=event["original_expression"],
                asserted_by=event["asserted_by"],
                asserted_at=_parse_dt(event["asserted_at"]),
                confidence=event["confidence"],
                evidence_locator=locator,
            )
            p.assertions[assertion.assertion_id] = assertion
            p.assertions_by_item.setdefault(assertion.subject_item_id, []).append(assertion.assertion_id)

        elif etype == "assertion.preference_set":
            key = (event["item_id"], event["predicate"])
            p.assertion_preferences[key] = event["assertion_id"]

        elif etype == "item.excluded":
            excl = Exclusion(
                item_id=event["item_id"],
                reason=ExclusionReason(event["reason"]),
                actor=event["actor"],
                ts=_parse_dt(event["ts"]),
                threshold=event.get("threshold"),
                observed=event.get("observed"),
                reversible=event.get("reversible", True),
            )
            p.active_exclusions[excl.item_id] = excl
            p.exclusion_history.setdefault(excl.item_id, []).append(excl)

        elif etype == "item.restored":
            p.active_exclusions.pop(event["item_id"], None)

        # model.invoked / tool.invoked carry no corpus state -- they feed the
        # trace views only (dhra.trace), not the projection.

    return p


def materialise_sqlite(projection: Projection, db_path: str | Path) -> None:
    """Rebuild derived.db from scratch as a queryable projection of `projection`.

    derived.db is disposable: delete it and call this again from a fresh
    fold() and the result is byte-for-byte the same tables (I8, test_projection_rebuild).
    """
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE items (
                item_id TEXT PRIMARY KEY,
                blob_sha256 TEXT NOT NULL,
                media_type TEXT NOT NULL,
                byte_length INTEGER NOT NULL,
                source_id TEXT NOT NULL,
                access_basis TEXT NOT NULL,
                excluded INTEGER NOT NULL DEFAULT 0,
                exclusion_reason TEXT
            );
            CREATE TABLE representations (
                rep_id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL,
                parent_rep_id TEXT,
                kind TEXT NOT NULL,
                producer TEXT NOT NULL,
                producer_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                text TEXT NOT NULL
            );
            CREATE TABLE assertions (
                assertion_id TEXT PRIMARY KEY,
                subject_item_id TEXT NOT NULL,
                predicate TEXT NOT NULL,
                value TEXT NOT NULL,
                original_expression TEXT NOT NULL,
                asserted_by TEXT NOT NULL,
                confidence TEXT NOT NULL
            );
            """
        )
        for item in projection.items.values():
            excl = projection.active_exclusions.get(item.item_id)
            conn.execute(
                "INSERT INTO items VALUES (?,?,?,?,?,?,?,?)",
                (
                    item.item_id,
                    item.blob_sha256,
                    item.media_type,
                    item.byte_length,
                    item.acquisition.source_id,
                    item.acquisition.access_basis,
                    1 if excl else 0,
                    excl.reason.value if excl else None,
                ),
            )
        for rep in projection.representations.values():
            conn.execute(
                "INSERT INTO representations VALUES (?,?,?,?,?,?,?,?)",
                (
                    rep.rep_id,
                    rep.item_id,
                    rep.parent_rep_id,
                    rep.kind,
                    rep.producer,
                    rep.producer_version,
                    rep.created_at.isoformat(),
                    rep.text,
                ),
            )
        for a in projection.assertions.values():
            conn.execute(
                "INSERT INTO assertions VALUES (?,?,?,?,?,?,?)",
                (
                    a.assertion_id,
                    a.subject_item_id,
                    a.predicate,
                    a.value,
                    a.original_expression,
                    a.asserted_by,
                    a.confidence,
                ),
            )
        conn.commit()
    finally:
        conn.close()
