"""Aggregates / corpus maps -- DHRA_BUILD_SPEC.md section 8.4 and 12.

"Every element of every aggregate view ... carries the locator set that
produced it and opens to those passages in one action" -- here, the
locator set is the bucket's `item_ids`, sufficient to resolve every
representation of every item in it.

"Bias report reachable from every aggregate view, and shown *before*
first aggregate results in a session" -- enforced structurally:
`AggregateResponse.bias_report` is not optional, and `aggregate_by_source`
is the only way to get bucket data, so there is no code path that
returns buckets without the report attached alongside them.
"""

from __future__ import annotations

from dataclasses import dataclass

from dhra.bias import BiasReport, compute_bias_report
from dhra.repo import DHRARepo


@dataclass(frozen=True)
class AggregateBucket:
    label: str
    item_ids: tuple[str, ...]  # drill-down set (section 8.4)


@dataclass(frozen=True)
class AggregateResponse:
    bias_report: BiasReport
    buckets: tuple[AggregateBucket, ...]
    corpus_version: str


def aggregate_by_source(repo: DHRARepo, *, expected_languages: set[str] | None = None) -> AggregateResponse:
    """One representative corpus map (section 6 Phase 2: "corpus maps
    with drill-down to passage"): active items grouped by acquisition
    source. Not a visualisation layer -- there is no UI yet -- but a
    real, drillable, bias-qualified aggregate."""
    projection = repo.projection()
    version = repo.corpus_version()
    bias_report = compute_bias_report(projection, expected_languages=expected_languages)

    buckets_map: dict[str, list[str]] = {}
    for item_id in projection.active_item_ids():
        source_id = projection.items[item_id].acquisition.source_id
        buckets_map.setdefault(source_id, []).append(item_id)
    buckets = tuple(
        AggregateBucket(label=source_id, item_ids=tuple(sorted(ids)))
        for source_id, ids in sorted(buckets_map.items())
    )
    return AggregateResponse(bias_report=bias_report, buckets=buckets, corpus_version=version.manifest_hash)
