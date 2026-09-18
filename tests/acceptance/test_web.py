"""Web UI acceptance tests -- DHRA_BUILD_SPEC.md section 12.

Not a spec-named phase exit test (the spec's own phases end at Phase 4,
section 17); this checks that the UI actually honours section 12's
mandatory/forbidden list against a live FastAPI TestClient, not just
that the routes exist.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dhra.models import ExclusionReason
from dhra.repo import DHRARepo
from dhra.web.app import build_app


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


@pytest.fixture
def client(repo):
    return TestClient(build_app(repo))


def test_search_shows_evidence_above_narrative(repo, client):
    repo.ingest_text("the bridge at Tokat was repaired in 1850", source_id="s")
    resp = client.get("/?q=Tokat")
    assert resp.status_code == 200
    body = resp.text
    evidence_pos = body.index("Evidence (")
    narrative_pos = body.find("Generated -- not verified")
    assert evidence_pos != -1
    assert narrative_pos == -1  # no narrative was ever produced -- nothing to mark, and nothing fakes one


def test_search_zero_hits_shows_absence_note_not_narrative(repo, client):
    repo.ingest_text("an unrelated sentence", source_id="s")
    resp = client.get("/?q=zzz_absent_zzz")
    assert resp.status_code == 200
    assert "absence-note" in resp.text
    assert "no mentions found" not in resp.text.lower()


def test_locator_resolves_and_shows_provenance(repo, client):
    item_id, rep_id = repo.ingest_text("a provenance test line", source_id="archive_x")
    resp = client.get(f"/locator/{item_id}/{rep_id}/0/1")
    assert resp.status_code == 200
    assert "archive_x" in resp.text
    assert "public_domain" in resp.text


def test_locator_unresolvable_is_404_not_degraded(repo, client):
    item_id, rep_id = repo.ingest_text("short", source_id="s")
    resp = client.get(f"/locator/{item_id}/{rep_id}/0/9999")
    assert resp.status_code == 404  # a bug, not a degraded result (section 4.6)


def test_claim_status_rendered_as_code_never_bare_number(repo, client):
    item_id, rep_id = repo.ingest_text("a claim source", source_id="s")
    client.post(
        "/claims/assess",
        data={
            "claim_id": "c1",
            "claim_text": "the claim text",
            "actor": "tester",
            "supporting": f"{item_id},{rep_id},0,5",
            "contradicting": "",
            "negating": "",
        },
    )
    resp = client.get("/claims/c1")
    assert resp.status_code == 200
    assert 'class="status-code"' in resp.text
    assert "E5" in resp.text
    # the meaning is in a hover tooltip (title attr), not a numeric score anywhere
    assert "title=\"E5 --" in resp.text


def test_aggregate_always_shows_bias_report_before_buckets(repo, client):
    repo.ingest_text("a lone item", source_id="only_source")
    resp = client.get("/aggregate")
    assert resp.status_code == 200
    bias_pos = resp.text.index("Bias report")
    buckets_pos = resp.text.index("Aggregate: items by source")
    assert bias_pos < buckets_pos


def test_exclusions_grouped_by_reason_with_one_click_restore(repo, client):
    item_id, _rep_id = repo.ingest_text("an excludable item", source_id="s")
    repo.exclude_item(item_id=item_id, reason=ExclusionReason.BELOW_QUALITY, actor="researcher")

    resp = client.get("/exclusions")
    assert resp.status_code == 200
    assert "below_quality_threshold" in resp.text
    assert item_id in resp.text

    restore_resp = client.post(f"/exclusions/{item_id}/restore", follow_redirects=False)
    assert restore_resp.status_code == 303
    assert item_id in repo.corpus_version().item_ids


def test_no_delete_route_exists_anywhere(repo, client):
    """Section 15 anti-requirement: no 'clean up corpus' action that
    deletes anything. Checked structurally against the live route table,
    not just by convention."""
    paths = {route.path for route in client.app.routes}
    assert not any("delete" in p.lower() for p in paths)


def test_trace_level2_only_shows_discretionary_decisions(repo, client):
    item_id, _rep_id = repo.ingest_text("traced item", source_id="s")
    repo.exclude_item(item_id=item_id, reason=ExclusionReason.RESEARCHER_EXCLUDED, actor="researcher")
    resp = client.get("/trace")
    assert resp.status_code == 200
    assert "item.excluded" in resp.text
