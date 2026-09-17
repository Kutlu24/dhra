"""Methods-statement export -- DHRA_BUILD_SPEC.md section 11.4 and the
Phase 4 exit test: "A generated methods statement contains everything
Section 11.4 requires and round-trips through the export test."

Section 11.4 requires: corpus definition and version hash; acquisition
sources with dates, access conditions and licence basis; the
transformation chain with tool versions; selection criteria with counts
at each stage; exclusion summary by reason; the full query set; model
identities and versions used, with purposes; and a statement of known
limitations drawn from the bias report (including access failures).

Every field here is read from real event-log state -- nothing is
templated prose. `model_invocations` is real and (truthfully) empty in
this repo: no LLM-calling layer exists yet to emit `model.invoked`
events (OPEN_QUESTIONS.md #7/#11/#14) -- an empty list is the honest
answer, not a gap to paper over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from dhra.bias import BiasReport, compute_bias_report
from dhra.corpus import CorpusVersion, corpus_version_from_projection
from dhra.store.events import EventLog
from dhra.store.projection import Projection, fold


@dataclass(frozen=True)
class SourceSummary:
    source_id: str
    item_count: int
    access_basis: tuple[str, ...]  # distinct values seen
    licence_ids: tuple[str, ...]  # distinct, non-null
    earliest_retrieved_at: str
    latest_retrieved_at: str


@dataclass(frozen=True)
class TransformationSummary:
    producer: str
    producer_version: str
    kind: str
    count: int


@dataclass(frozen=True)
class QueryRecord:
    query: str
    variants: tuple[str, ...]
    ts: str


@dataclass(frozen=True)
class ModelInvocationRecord:
    model: str
    purpose: str
    ts: str


@dataclass(frozen=True)
class MethodsStatement:
    corpus_version: str
    corpus_item_count: int
    generated_at: str
    acquisition_sources: tuple[SourceSummary, ...]
    transformation_chain: tuple[TransformationSummary, ...]
    selection_criteria: dict
    exclusion_summary: tuple[dict, ...]
    query_set: tuple[QueryRecord, ...]
    model_invocations: tuple[ModelInvocationRecord, ...]
    limitations: tuple[str, ...]
    bias_report: BiasReport

    def to_dict(self) -> dict:
        return {
            "corpus_version": self.corpus_version,
            "corpus_item_count": self.corpus_item_count,
            "generated_at": self.generated_at,
            "acquisition_sources": [
                {
                    "source_id": s.source_id,
                    "item_count": s.item_count,
                    "access_basis": list(s.access_basis),
                    "licence_ids": list(s.licence_ids),
                    "earliest_retrieved_at": s.earliest_retrieved_at,
                    "latest_retrieved_at": s.latest_retrieved_at,
                }
                for s in self.acquisition_sources
            ],
            "transformation_chain": [
                {"producer": t.producer, "producer_version": t.producer_version, "kind": t.kind, "count": t.count}
                for t in self.transformation_chain
            ],
            "selection_criteria": self.selection_criteria,
            "exclusion_summary": list(self.exclusion_summary),
            "query_set": [{"query": q.query, "variants": list(q.variants), "ts": q.ts} for q in self.query_set],
            "model_invocations": [{"model": m.model, "purpose": m.purpose, "ts": m.ts} for m in self.model_invocations],
            "limitations": list(self.limitations),
            "bias_report": {
                "total_items": self.bias_report.total_items,
                "warnings": list(self.bias_report.warnings),
                "dominant_source_warning": self.bias_report.dominant_source_warning,
                "period_gap_warning": self.bias_report.period_gap_warning,
                "missing_languages": list(self.bias_report.missing_languages),
                "access_failure_count": self.bias_report.access_failure_count,
            },
        }


def build_methods_statement(event_log: EventLog, *, expected_languages: set[str] | None = None, seq: int | None = None) -> MethodsStatement:
    events = list(event_log.read_up_to(seq) if seq is not None else event_log.read_all())
    projection = fold(events)
    version = corpus_version_from_projection(projection)
    bias_report = compute_bias_report(projection, expected_languages=expected_languages)

    by_source: dict[str, list] = {}
    for item_id in version.item_ids:
        item = projection.items[item_id]
        by_source.setdefault(item.acquisition.source_id, []).append(item)
    acquisition_sources = tuple(
        SourceSummary(
            source_id=source_id,
            item_count=len(items),
            access_basis=tuple(sorted({i.acquisition.access_basis for i in items})),
            licence_ids=tuple(sorted({i.acquisition.licence_id for i in items if i.acquisition.licence_id})),
            earliest_retrieved_at=min(i.acquisition.retrieved_at for i in items).isoformat(),
            latest_retrieved_at=max(i.acquisition.retrieved_at for i in items).isoformat(),
        )
        for source_id, items in sorted(by_source.items())
    )

    by_transform: dict[tuple[str, str, str], int] = {}
    for rep in projection.representations.values():
        key = (rep.producer, rep.producer_version, rep.kind)
        by_transform[key] = by_transform.get(key, 0) + 1
    transformation_chain = tuple(
        TransformationSummary(producer=p, producer_version=v, kind=k, count=c)
        for (p, v, k), c in sorted(by_transform.items())
    )

    total_acquired = len(projection.items)
    total_included = len(version.item_ids)
    total_excluded = total_acquired - total_included
    selection_criteria = {
        "total_acquired": total_acquired,
        "total_excluded": total_excluded,
        "total_included": total_included,
    }

    exclusion_counts: dict[str, int] = {}
    for excl in projection.active_exclusions.values():
        exclusion_counts[excl.reason.value] = exclusion_counts.get(excl.reason.value, 0) + 1
    exclusion_summary = tuple({"reason": r, "count": c} for r, c in sorted(exclusion_counts.items()))

    query_events = [e for e in events if e["type"] == "tool.invoked" and e.get("tool") == "search_evidence"]
    query_set = tuple(
        QueryRecord(
            query=e["parameters"]["query"],
            variants=tuple(e["parameters"].get("variants") or ()),
            ts=e["ts"],
        )
        for e in query_events
    )

    model_events = [e for e in events if e["type"] == "model.invoked"]
    model_invocations = tuple(ModelInvocationRecord(model=e["model"], purpose=e["purpose"], ts=e["ts"]) for e in model_events)

    return MethodsStatement(
        corpus_version=version.manifest_hash,
        corpus_item_count=total_included,
        generated_at=datetime.now(timezone.utc).isoformat(),
        acquisition_sources=acquisition_sources,
        transformation_chain=transformation_chain,
        selection_criteria=selection_criteria,
        exclusion_summary=exclusion_summary,
        query_set=query_set,
        model_invocations=model_invocations,
        limitations=bias_report.warnings,
        bias_report=bias_report,
    )
