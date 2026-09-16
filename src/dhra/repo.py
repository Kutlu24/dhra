"""High-level, ergonomic entry point over blobs + events -- ties together
DHRA_BUILD_SPEC.md sections 4 and 5 for callers (tests, and later the
tool layer). Every mutating method appends exactly one event; nothing
here mutates state outside the event log.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dhra.corpus import CorpusVersion, corpus_version_at
from dhra.models import ExclusionReason, Locator, Quality, ResolvedPassage
from dhra.store.blobs import BlobStore
from dhra.store.events import EventLog
from dhra.store.projection import Projection, fold
from dhra.ulid import new_ulid


class DHRARepo:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.blobs = BlobStore(self.root / "blobs")
        self.events = EventLog(self.root / "events.jsonl")

    # --- writes: each appends exactly one event -----------------------------

    def acquire_item(
        self,
        data: bytes,
        *,
        source_id: str,
        method: str,
        access_basis: str,
        media_type: str,
        licence_id: str | None = None,
        redistributable: bool | None = None,
        original_reference: str | None = None,
        request: dict | None = None,
        item_id: str | None = None,
        task: str | None = None,
    ) -> str:
        sha256 = self.blobs.put(data)
        item_id = item_id or new_ulid()
        self.events.append(
            "item.acquired",
            item_id=item_id,
            blob_sha256=sha256,
            media_type=media_type,
            byte_length=len(data),
            source_id=source_id,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            method=method,
            request=request,
            access_basis=access_basis,
            licence_id=licence_id,
            redistributable=redistributable,
            original_reference=original_reference,
            task=task,
        )
        return item_id

    def create_representation(
        self,
        *,
        item_id: str,
        kind: str,
        producer: str,
        producer_version: str,
        text: str,
        parent_rep_id: str | None = None,
        parameters: dict | None = None,
        quality: Quality | None = None,
        rep_id: str | None = None,
        task: str | None = None,
    ) -> str:
        if not producer_version:
            raise ValueError("producer_version is mandatory (unversioned transformations are rejected at write time)")
        rep_id = rep_id or new_ulid()
        quality_dict = None
        if quality is not None:
            quality_dict = {
                "mean_char_confidence": quality.mean_char_confidence,
                "per_span_confidence": [list(span) for span in quality.per_span_confidence],
                "script": quality.script,
                "manually_corrected": quality.manually_corrected,
                "notes": quality.notes,
            }
        self.events.append(
            "representation.created",
            rep_id=rep_id,
            item_id=item_id,
            parent_rep_id=parent_rep_id,
            kind=kind,
            producer=producer,
            producer_version=producer_version,
            parameters=parameters or {},
            created_at=datetime.now(timezone.utc).isoformat(),
            text=text,
            quality=quality_dict,
            task=task,
        )
        return rep_id

    def add_assertion(
        self,
        *,
        subject_item_id: str,
        predicate: str,
        value: str,
        original_expression: str,
        asserted_by: str,
        confidence: str,
        evidence_locator: Locator | None = None,
        assertion_id: str | None = None,
        task: str | None = None,
    ) -> str:
        assertion_id = assertion_id or new_ulid()
        locator_dict = None
        if evidence_locator is not None:
            locator_dict = {
                "item_id": evidence_locator.item_id,
                "rep_id": evidence_locator.rep_id,
                "start": evidence_locator.start,
                "end": evidence_locator.end,
                "page": evidence_locator.page,
                "iiif_region": evidence_locator.iiif_region,
            }
        self.events.append(
            "assertion.added",
            assertion_id=assertion_id,
            subject_item_id=subject_item_id,
            predicate=predicate,
            value=value,
            original_expression=original_expression,
            asserted_by=asserted_by,
            asserted_at=datetime.now(timezone.utc).isoformat(),
            confidence=confidence,
            evidence_locator=locator_dict,
            task=task,
        )
        return assertion_id

    def set_assertion_preference(self, *, item_id: str, predicate: str, assertion_id: str, task: str | None = None) -> None:
        self.events.append(
            "assertion.preference_set",
            item_id=item_id,
            predicate=predicate,
            assertion_id=assertion_id,
            task=task,
        )

    def exclude_item(
        self,
        *,
        item_id: str,
        reason: ExclusionReason,
        actor: str,
        threshold: float | None = None,
        observed: float | None = None,
        task: str | None = None,
    ) -> None:
        self.events.append(
            "item.excluded",
            item_id=item_id,
            reason=ExclusionReason(reason).value,
            actor=actor,
            threshold=threshold,
            observed=observed,
            reversible=True,
            task=task,
        )

    def restore_item(self, *, item_id: str, actor: str, task: str | None = None) -> None:
        """Single-action reversal (I5). Emits a compensating event; the
        excluding event is never edited or removed (I4)."""
        self.events.append("item.restored", item_id=item_id, actor=actor, task=task)

    # --- reads ---------------------------------------------------------------

    def projection(self, seq: int | None = None) -> Projection:
        events = self.events.read_up_to(seq) if seq is not None else self.events.read_all()
        return fold(events)

    def corpus_version(self, seq: int | None = None) -> CorpusVersion:
        return corpus_version_at(self.events, seq)

    def resolve(self, locator: Locator) -> ResolvedPassage:
        """A Locator that does not resolve is a bug, not a degraded result (section 4.6)."""
        projection = self.projection()
        rep = projection.representations.get(locator.rep_id)
        if rep is None or rep.item_id != locator.item_id:
            raise ValueError(f"Locator does not resolve: rep {locator.rep_id} not found on item {locator.item_id}")
        if not (0 <= locator.start <= locator.end <= len(rep.text)):
            raise ValueError(f"Locator does not resolve: [{locator.start}:{locator.end}] out of range for rep {rep.rep_id}")
        return ResolvedPassage(
            item_id=locator.item_id,
            rep_id=locator.rep_id,
            text=rep.text[locator.start : locator.end],
            page=locator.page,
            iiif_region=locator.iiif_region,
        )
