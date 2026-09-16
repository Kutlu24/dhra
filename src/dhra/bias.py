"""Bias report -- DHRA_BUILD_SPEC.md section 6 (Phase 2) and section 12
("Bias report reachable from every aggregate view, and shown *before*
first aggregate results in a session").

There is no UI/session here yet (that's later), so "shown before" is
enforced structurally instead: `dhra.aggregate.compute_aggregate` always
computes and attaches a `BiasReport` to its result -- there is no code
path that returns aggregate data without one (section 8.4's own rule,
applied to bias reporting too: an aggregate that can't show its own
skew is not one this system should present unqualified).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from dhra.store.projection import Projection

YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")


@dataclass(frozen=True)
class SourceConcentration:
    source_id: str
    item_count: int
    share: float  # 0..1 of the included corpus


@dataclass(frozen=True)
class PeriodBucket:
    year: int
    item_count: int


@dataclass(frozen=True)
class BiasReport:
    total_items: int
    source_concentration: tuple[SourceConcentration, ...]
    dominant_source_warning: str | None
    period_buckets: tuple[PeriodBucket, ...]
    period_gap_warning: str | None
    missing_languages: tuple[str, ...]
    access_failure_count: int
    access_failures: tuple[dict, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def has_warnings(self) -> bool:
        return bool(self.warnings)


def compute_bias_report(
    projection: Projection,
    *,
    expected_languages: set[str] | None = None,
    dominant_source_threshold: float = 0.5,
) -> BiasReport:
    included = projection.active_item_ids()
    total = len(included)
    warnings: list[str] = []

    # --- source concentration ---
    counts: dict[str, int] = {}
    for item_id in included:
        source_id = projection.items[item_id].acquisition.source_id
        counts[source_id] = counts.get(source_id, 0) + 1
    concentration = tuple(
        SourceConcentration(source_id=s, item_count=c, share=(c / total if total else 0.0))
        for s, c in sorted(counts.items(), key=lambda kv: -kv[1])
    )
    dominant_warning = None
    if concentration and concentration[0].share > dominant_source_threshold:
        dominant_warning = (
            f"{concentration[0].source_id} supplies {concentration[0].share:.0%} of the corpus "
            f"({concentration[0].item_count}/{total} items) -- findings may reflect that source's "
            "editorial choices more than the underlying history."
        )
        warnings.append(dominant_warning)

    # --- period distribution (from assertion predicate="date", first 4-digit year found) ---
    year_counts: dict[int, int] = {}
    for item_id in included:
        for assertion_id in projection.assertions_by_item.get(item_id, []):
            a = projection.assertions[assertion_id]
            if a.predicate != "date":
                continue
            match = YEAR_RE.search(a.value) or YEAR_RE.search(a.original_expression)
            if match:
                year_counts[int(match.group(1))] = year_counts.get(int(match.group(1)), 0) + 1
    period_buckets = tuple(PeriodBucket(year=y, item_count=c) for y, c in sorted(year_counts.items()))
    period_gap_warning = None
    if len(period_buckets) >= 2:
        years = [b.year for b in period_buckets]
        span = range(min(years), max(years) + 1)
        thin_years = [y for y in span if year_counts.get(y, 0) <= max(1, sum(year_counts.values()) // (10 * len(span)))]
        dense_years = [b.year for b in period_buckets if b.item_count >= max(year_counts.values()) * 0.6]
        if thin_years and dense_years:
            period_gap_warning = (
                f"Coverage is uneven across time: dense around {dense_years}, thin around {thin_years}."
            )
            warnings.append(period_gap_warning)

    # --- language coverage ---
    seen_languages = {
        projection.assertions[aid].value.lower()
        for item_id in included
        for aid in projection.assertions_by_item.get(item_id, [])
        if projection.assertions[aid].predicate == "language"
    }
    missing = tuple(sorted(lang for lang in (expected_languages or set()) if lang.lower() not in seen_languages))
    if missing:
        warning = f"Expected language(s) not present in the corpus at all: {', '.join(missing)}."
        warnings.append(warning)

    # --- access failures ---
    access_failures = tuple(projection.access_failures)
    if access_failures:
        warnings.append(
            f"{len(access_failures)} acquisition attempt(s) failed/were refused and are not represented in the corpus."
        )

    return BiasReport(
        total_items=total,
        source_concentration=concentration,
        dominant_source_warning=dominant_warning,
        period_buckets=period_buckets,
        period_gap_warning=period_gap_warning,
        missing_languages=missing,
        access_failure_count=len(access_failures),
        access_failures=access_failures,
        warnings=tuple(warnings),
    )
