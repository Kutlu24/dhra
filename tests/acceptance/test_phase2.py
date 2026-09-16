"""Phase 2 exit test battery -- DHRA_BUILD_SPEC.md section 6 (Phase 2).

Exit test (spec wording): "The seeded reprint-family fixture is
correctly collapsed to a single witness, with the shared error cited as
the basis; the skewed-corpus fixture produces an unprompted bias report
before any aggregate is returned."
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "fixtures"))
from phase2_fixtures import build_reprint_family, build_skewed_corpus  # noqa: E402

from dhra.aggregate import aggregate_by_source
from dhra.disconfirm import disconfirm_search
from dhra.independence import IndependenceVerdict, cluster_by_descent
from dhra.models import ExclusionReason, Locator
from dhra.repo import DHRARepo
from dhra.status import Status


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


def _reprint_candidates(repo: DHRARepo, item_ids: list[str]) -> list[tuple[str, str]]:
    projection = repo.projection()
    return [(iid, projection.representations[projection.reps_by_item[iid][0]].text) for iid in item_ids]


# --- Phase 2 exit test: reprint_family --------------------------------------


def test_reprint_family_collapses_to_single_witness_with_shared_error_cited(repo):
    gt = build_reprint_family(repo)
    candidates = _reprint_candidates(repo, gt["all_ids"])
    clusters, verdicts = cluster_by_descent(candidates)

    assert len(clusters) == 1, "exactly one descent cluster expected (the reprint family)"
    cluster = clusters[0]
    assert set(cluster.members) == set(gt["reprint_ids"]), "cluster must be exactly the 11 reprints, not the 6 independents"

    # "with the shared error cited as the basis" -- the decisive signal
    # must actually be present and actually name the garbled token.
    error_signals = [s for s in cluster.signals if s.kind == "shared_error"]
    assert error_signals, "cluster must cite a shared_error signal, not just phrasing similarity"
    assert any("reshud" in s.detail.lower() for s in error_signals)

    distinct_witnesses = len(gt["all_ids"]) - sum(len(c.members) - 1 for c in clusters)
    assert distinct_witnesses == gt["expected_witnesses"] == 7, "17 raw items -> 7 witnesses, not 17"

    # The 6 independent accounts must never be swept into the cluster,
    # and must not spuriously cluster with each other either.
    independent_set = set(gt["independent_ids"])
    assert not (independent_set & set(cluster.members))
    other_clusters_among_independents = [
        c for c in clusters if set(c.members) & independent_set and len(set(c.members) & independent_set) > 1
    ]
    assert other_clusters_among_independents == []


def test_descent_cluster_members_excluded_reversibly(repo):
    gt = build_reprint_family(repo)
    supporting = [
        Locator(item_id=iid, rep_id=repo.projection().reps_by_item[iid][0], start=0, end=10)
        for iid in gt["all_ids"]
    ]
    assessment, clusters, verdicts = repo.assess_claim_with_independence(
        claim_id="bridge-claim", claim_text="the bridge at Tokat was damaged", supporting=supporting
    )
    version = repo.corpus_version()
    reprint_members = set(clusters[0].members)
    representative = clusters[0].representative

    active_ids = set(version.item_ids)
    non_representative = reprint_members - {representative}
    assert non_representative, "there must be excluded (non-representative) members to check"
    assert not (non_representative & active_ids), "non-representative reprints must be excluded from the corpus"
    assert representative in active_ids, "the representative stays in the corpus"

    # I5: reversible in one action.
    one_member = next(iter(non_representative))
    repo.restore_item(item_id=one_member, actor="researcher")
    assert one_member in repo.corpus_version().item_ids


def test_e2_corroborated_reachable_after_independence_check(repo):
    """I6 finally satisfied end to end: E2 requires a passed independence
    check, and here one actually ran, over genuinely independent items."""
    gt = build_reprint_family(repo)
    projection = repo.projection()
    # Two of the six genuinely independent accounts -- real independence check.
    ids = gt["independent_ids"][:2]
    supporting = [Locator(item_id=iid, rep_id=projection.reps_by_item[iid][0], start=0, end=15) for iid in ids]

    assessment, clusters, verdicts = repo.assess_claim_with_independence(
        claim_id="tokat-flood", claim_text="a bridge at Tokat was damaged by flooding", supporting=supporting
    )
    assert assessment.status == Status.CORROBORATED
    assert "independent" in assessment.note.lower()


def test_e2_not_granted_for_reprint_family_alone(repo):
    """The reprint family must NOT reach E2 -- after collapsing, it is a
    single witness (E5), which is exactly the point of this fixture."""
    gt = build_reprint_family(repo)
    projection = repo.projection()
    supporting = [Locator(item_id=iid, rep_id=projection.reps_by_item[iid][0], start=0, end=10) for iid in gt["reprint_ids"]]

    assessment, clusters, verdicts = repo.assess_claim_with_independence(
        claim_id="reprint-only-claim", claim_text="the bridge at Tokat was damaged", supporting=supporting
    )
    assert assessment.status == Status.SINGLE_WITNESS
    assert assessment.status != Status.CORROBORATED


# --- Phase 2 exit test: skewed_corpus + unprompted bias report -------------


def test_skewed_corpus_bias_report_unprompted_before_aggregate(repo):
    gt = build_skewed_corpus(repo)
    response = aggregate_by_source(repo, expected_languages=gt["expected_languages"])

    # The bias report is not optional and not requested separately --
    # it is structurally part of the same response as the aggregate data.
    assert response.bias_report is not None
    assert response.bias_report.has_warnings()
    assert response.bias_report.dominant_source_warning is not None
    assert "70%" in response.bias_report.dominant_source_warning
    assert response.bias_report.period_gap_warning is not None
    assert set(response.bias_report.missing_languages) == {"armenian", "greek"}
    assert response.bias_report.access_failure_count == 2

    # The aggregate data itself is still real and drillable (section 8.4).
    assert response.buckets
    total_drilldown_items = sum(len(b.item_ids) for b in response.buckets)
    assert total_drilldown_items == len(gt["all_ids"])


def test_aggregate_always_carries_bias_report_even_when_clean(repo):
    """Structural invariant, not just for the skewed fixture: there is no
    code path to get aggregate buckets without a bias report attached."""
    repo.ingest_text("a perfectly unremarkable, balanced item", source_id="only_source")
    response = aggregate_by_source(repo)
    assert response.bias_report is not None
    assert response.buckets


# --- Disconfirmation search (section 11.2) ----------------------------------


def test_disconfirm_search_runs_real_queries_against_the_corpus(repo):
    repo.ingest_text("the bridge at Tokat was fully repaired by the autumn", source_id="s")
    result = disconfirm_search(
        repo,
        "the bridge was never repaired",
        negated_queries=["bridge was never repaired", "repair was abandoned"],
    )
    assert len(result.outcomes) == 2
    assert result.outcomes[0].query == "bridge was never repaired"
    # Neither negated query is actually in the corpus -- no refutation found.
    assert result.found_refuting_evidence() is False
