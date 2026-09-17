"""High-level, ergonomic entry point over blobs + events -- ties together
DHRA_BUILD_SPEC.md sections 4 and 5 for callers (tests, and later the
tool layer). Every mutating method appends exactly one event; nothing
here mutates state outside the event log.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dhra.corpus import CorpusVersion, corpus_version_at
from dhra.independence import DescentCluster, IndependenceVerdict, PairVerdict, cluster_by_descent, dedupe_by_descent
from dhra.models import ExclusionReason, Locator, Quality, ResolvedPassage
from dhra.status import ClaimAssessment, assess_claim, check_monotonicity
from dhra.store.blobs import BlobStore
from dhra.store.events import EventLog
from dhra.store.projection import Projection, fold
from dhra.transcribe import (
    ManualTranscriber,
    PdfToTextTranscriber,
    TeiTranscriber,
    TesseractTranscriber,
    Transcriber,
)
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

    # --- ingestion: acquire + transcribe in one call (section 6, Phase 1) ---

    def _ingest(
        self,
        data: bytes,
        *,
        transcriber: Transcriber,
        media_type: str,
        source_id: str,
        method: str,
        access_basis: str,
        licence_id: str | None = None,
        redistributable: bool | None = None,
        original_reference: str | None = None,
        task: str | None = None,
    ) -> tuple[str, str]:
        item_id = self.acquire_item(
            data,
            source_id=source_id,
            method=method,
            access_basis=access_basis,
            media_type=media_type,
            licence_id=licence_id,
            redistributable=redistributable,
            original_reference=original_reference,
            task=task,
        )
        result = transcriber.transcribe(data)
        rep_id = self.create_representation(
            item_id=item_id,
            kind="transcription",
            producer=result.producer,
            producer_version=result.producer_version,
            text=result.text,
            quality=result.quality,
            task=task,
        )
        return item_id, rep_id

    def ingest_text(
        self,
        text: str,
        *,
        source_id: str,
        access_basis: str = "public_domain",
        licence_id: str | None = None,
        redistributable: bool | None = None,
        original_reference: str | None = None,
        task: str | None = None,
    ) -> tuple[str, str]:
        return self._ingest(
            text.encode("utf-8"),
            transcriber=ManualTranscriber(),
            media_type="text/plain",
            source_id=source_id,
            method="manual_upload",
            access_basis=access_basis,
            licence_id=licence_id,
            redistributable=redistributable,
            original_reference=original_reference,
            task=task,
        )

    def ingest_pdf(
        self,
        data: bytes,
        *,
        source_id: str,
        access_basis: str = "public_domain",
        licence_id: str | None = None,
        redistributable: bool | None = None,
        original_reference: str | None = None,
        task: str | None = None,
    ) -> tuple[str, str]:
        return self._ingest(
            data,
            transcriber=PdfToTextTranscriber(),
            media_type="application/pdf",
            source_id=source_id,
            method="download",
            access_basis=access_basis,
            licence_id=licence_id,
            redistributable=redistributable,
            original_reference=original_reference,
            task=task,
        )

    def ingest_tei(
        self,
        data: bytes,
        *,
        source_id: str,
        access_basis: str = "public_domain",
        licence_id: str | None = None,
        redistributable: bool | None = None,
        original_reference: str | None = None,
        task: str | None = None,
    ) -> tuple[str, str]:
        return self._ingest(
            data,
            transcriber=TeiTranscriber(),
            media_type="application/tei+xml",
            source_id=source_id,
            method="download",
            access_basis=access_basis,
            licence_id=licence_id,
            redistributable=redistributable,
            original_reference=original_reference,
            task=task,
        )

    def ingest_image(
        self,
        data: bytes,
        *,
        source_id: str,
        media_type: str = "image/png",
        lang: str = "eng",
        access_basis: str = "public_domain",
        licence_id: str | None = None,
        redistributable: bool | None = None,
        original_reference: str | None = None,
        task: str | None = None,
    ) -> tuple[str, str]:
        """OCR via the real system `tesseract` binary. `lang` must be one
        of `tesseract --list-langs`; only `eng` is installed in this
        environment (see OPEN_QUESTIONS.md #6 -- manuscript-script OCR
        needs its own trained data, not assumed present)."""
        return self._ingest(
            data,
            transcriber=TesseractTranscriber(lang=lang),
            media_type=media_type,
            source_id=source_id,
            method="manual_upload",
            access_basis=access_basis,
            licence_id=licence_id,
            redistributable=redistributable,
            original_reference=original_reference,
            task=task,
        )

    # --- epistemic status (section 7) ----------------------------------------

    def assess_claim(
        self,
        *,
        claim_id: str,
        claim_text: str,
        supporting: list[Locator] | None = None,
        contradicting: list[Locator] | None = None,
        negating: list[Locator] | None = None,
        out_of_scope: bool = False,
        search_scope: str = "",
        independence_confirmed: bool = False,
        independence_note: str = "",
        task: str | None = None,
    ) -> ClaimAssessment:
        """Status is assigned per claim, never per document (rule 1), by
        deterministic code over evidence the caller has already decided
        on -- the model may propose candidates but never assigns status
        itself (section 10). Rejects a status rise that isn't backed by
        strictly new evidence (rule 2); a fall is always allowed (rule 3).

        `independence_confirmed` must only be set by a caller that has
        actually run the descent-clustering pipeline over `supporting`
        (see `assess_claim_with_independence` below) -- passing it
        without doing that check is how I6 gets violated."""
        version = self.corpus_version()
        previous = self.get_claim_assessment(claim_id)
        new = assess_claim(
            claim_id=claim_id,
            claim_text=claim_text,
            corpus_version=version.manifest_hash,
            supporting=supporting,
            contradicting=contradicting,
            negating=negating,
            out_of_scope=out_of_scope,
            search_scope=search_scope,
            independence_confirmed=independence_confirmed,
            independence_note=independence_note,
        )
        check_monotonicity(previous, new)

        def _loc_dicts(locs: tuple[Locator, ...]) -> list[dict]:
            return [
                {
                    "item_id": loc.item_id,
                    "rep_id": loc.rep_id,
                    "start": loc.start,
                    "end": loc.end,
                    "page": loc.page,
                    "iiif_region": loc.iiif_region,
                }
                for loc in locs
            ]

        self.events.append(
            "claim.assessed",
            claim_id=new.claim_id,
            claim_text=new.claim_text,
            status=new.status.value,
            supporting=_loc_dicts(new.supporting),
            contradicting=_loc_dicts(new.contradicting),
            negating=_loc_dicts(new.negating),
            note=new.note,
            corpus_version=new.corpus_version,
            task=task,
        )
        return new

    def get_claim_assessment(self, claim_id: str) -> ClaimAssessment | None:
        return self.projection().claims.get(claim_id)

    def claim_history(self, claim_id: str) -> list[ClaimAssessment]:
        return list(self.projection().claim_history.get(claim_id, []))

    # --- independence / descent clustering (section 7.3, Phase 2) -----------

    def assess_claim_with_independence(
        self,
        *,
        claim_id: str,
        claim_text: str,
        supporting: list[Locator],
        actor: str = "independence_engine",
        task: str | None = None,
    ) -> tuple[ClaimAssessment, list[DescentCluster], list[PairVerdict]]:
        """Runs the real descent-clustering pipeline over `supporting`
        before assessing the claim: reprint-family duplicates collapse to
        their representative (section 18's "37 passages, 11 share a
        descent, count as one"), non-representative members are excluded
        reversibly (`ExclusionReason.DESCENT_CLUSTER_MEMBER`), and E2 is
        only used when every remaining distinct-item pair was actually
        checked and verdicted INDEPENDENT -- never on textual similarity
        or co-occurrence alone (section 7.3)."""
        projection = self.projection()
        texts: dict[str, str] = {}
        for loc in supporting:
            rep = projection.representations[loc.rep_id]
            texts[loc.item_id] = rep.text
        candidates = sorted(texts.items())

        clusters, verdicts = cluster_by_descent(candidates)

        for cluster in clusters:
            for member in cluster.members:
                if member == cluster.representative:
                    continue
                if member in projection.active_exclusions:
                    continue
                self.exclude_item(item_id=member, reason=ExclusionReason.DESCENT_CLUSTER_MEMBER, actor=actor, task=task)

        deduped = dedupe_by_descent(supporting, clusters)
        distinct_items = sorted({loc.item_id for loc in deduped})

        independence_confirmed = False
        independence_note = ""
        if len(distinct_items) > 1:
            verdict_map: dict[tuple[str, str], PairVerdict] = {}
            for v in verdicts:
                verdict_map[(v.a, v.b)] = v
                verdict_map[(v.b, v.a)] = v
            checked_notes = []
            all_independent = True
            for i in range(len(distinct_items)):
                for j in range(i + 1, len(distinct_items)):
                    pair = verdict_map.get((distinct_items[i], distinct_items[j]))
                    if pair is None or pair.verdict != IndependenceVerdict.INDEPENDENT:
                        all_independent = False
                        continue
                    checked_notes.append(f"{distinct_items[i]}~{distinct_items[j]} (jaccard {pair.similarity:.2f})")
            independence_confirmed = all_independent
            if checked_notes:
                independence_note = "Independent pairs checked: " + "; ".join(checked_notes) + "."

        assessment = self.assess_claim(
            claim_id=claim_id,
            claim_text=claim_text,
            supporting=deduped,
            independence_confirmed=independence_confirmed,
            independence_note=independence_note,
            task=task,
        )
        return assessment, clusters, verdicts

    # --- access failures (section 11.4 methods export; bias reporting) ------

    def record_access_failure(self, *, source_id: str, reason: str, request: dict | None = None, task: str | None = None) -> None:
        """Section 9.2/11.4: "where terms prohibit automated access, the
        correct behaviour is to say so ... never to route around it."
        This records that a source was tried and refused/failed -- no
        item exists (nothing was acquired), so there is no blob to
        store; the failure itself is the event."""
        self.events.append("access.failed", source_id=source_id, reason=reason, request=request, task=task)

    # --- tool-layer approvals (section 9.1) ----------------------------------

    def grant_approval(self, *, tool: str, summary: str, details: dict | None = None, actor: str, task: str | None = None) -> None:
        """Scoped to this exact (tool, summary) action, never to the
        session (section 9.1); consumed on first matching use."""
        self.events.append("approval.granted", tool=tool, summary=summary, details=details or {}, actor=actor, task=task)

    def deny_approval(self, *, tool: str, summary: str, reason: str, actor: str, task: str | None = None) -> None:
        self.events.append("approval.denied", tool=tool, summary=summary, reason=reason, actor=actor, task=task)

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
