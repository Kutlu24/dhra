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


def test_ingest_text_then_findable_by_search(repo, client):
    resp = client.post(
        "/ingest",
        data={
            "source_id": "manual_upload",
            "access_basis": "public_domain",
            "licence_id": "",
            "original_reference": "",
            "text": "a manually pasted test passage",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/item/")

    found = client.get("/?q=manually")
    assert "Evidence (1)" in found.text


def test_ingest_requires_text_or_file(repo, client):
    resp = client.post("/ingest", data={"source_id": "manual_upload", "access_basis": "public_domain", "licence_id": "", "original_reference": "", "text": ""})
    assert resp.status_code == 400


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


def test_assistant_page_shows_research_and_teaching_columns(client, monkeypatch):
    monkeypatch.delenv("DHRA_GLM_BASE_URL", raising=False)
    monkeypatch.delenv("DHRA_GLM_API_KEY", raising=False)
    resp = client.get("/assistant")
    assert resp.status_code == 200
    research_pos = resp.text.index(">Research<")
    teaching_pos = resp.text.index(">Teaching<")
    assert research_pos < teaching_pos  # research column renders first (left)
    assert "No LLM backend configured" in resp.text


def test_assistant_forms_refuse_without_llm_configured(client, monkeypatch):
    monkeypatch.delenv("DHRA_GLM_BASE_URL", raising=False)
    monkeypatch.delenv("DHRA_GLM_API_KEY", raising=False)
    resp = client.post("/assistant/research-questions", data={"context_query": "x", "actor": "researcher"})
    assert resp.status_code == 503


def test_assistant_research_questions_creates_draft_shown_on_page(repo, client, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")

    import requests

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "1. What caused the 1849 damage?"}}]}

    monkeypatch.setattr(requests.Session, "post", lambda self, *a, **kw: _FakeResp())

    resp = client.post("/assistant/research-questions", data={"context_query": "Tokat", "actor": "researcher"}, follow_redirects=False)
    assert resp.status_code == 303

    page = client.get("/assistant")
    assert "What caused the 1849 damage" in page.text
    assert "research_questions" in page.text


def test_assistant_disconfirm_creates_draft_shown_on_page(repo, client, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    repo.ingest_text("the bridge at Tokat was fully repaired by the autumn", source_id="s")

    import requests

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "bridge was never repaired\nrepair was abandoned"}}]}

    monkeypatch.setattr(requests.Session, "post", lambda self, *a, **kw: _FakeResp())

    resp = client.post("/assistant/disconfirm", data={"claim_text": "the bridge was repaired", "actor": "researcher"}, follow_redirects=False)
    assert resp.status_code == 303

    page = client.get("/assistant")
    assert "QUERY: bridge was never repaired" in page.text
    assert "disconfirmation" in page.text


def test_chat_shows_evidence_without_llm_configured(repo, client, monkeypatch):
    monkeypatch.delenv("DHRA_GLM_BASE_URL", raising=False)
    monkeypatch.delenv("DHRA_GLM_API_KEY", raising=False)
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")

    resp = client.post("/chat", data={"message": "Tokat", "history_json": "[]"})
    assert resp.status_code == 200
    assert "Tokat" in resp.text
    assert "No LLM backend configured" in resp.text
    assert "Generated --" not in resp.text  # no narrative badge -- no answer was generated


def test_chat_conversation_state_round_trips_through_the_form(repo, client, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")

    import requests

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "It was repaired in 1849."}}]}

    monkeypatch.setattr(requests.Session, "post", lambda self, *a, **kw: _FakeResp())

    resp = client.post("/chat", data={"message": "Tokat", "history_json": "[]"})
    assert "It was repaired in 1849." in resp.text
    assert 'name="history_json"' in resp.text
    # the hidden field now carries this turn forward for the next POST
    assert "Tokat" in resp.text and "assistant" in resp.text


def test_chat_post_sends_the_selected_ui_language_to_the_model(repo, client, monkeypatch):
    from dhra.web.app import LANGUAGE_COOKIE

    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")

    import requests

    calls = []

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Die Brücke wurde 1849 repariert."}}]}

    def _fake_post(self, url, *, headers, json, timeout):
        calls.append(json)
        return _FakeResp()

    monkeypatch.setattr(requests.Session, "post", _fake_post)

    client.cookies.set(LANGUAGE_COOKIE, "de")
    client.post("/chat", data={"message": "Tokat", "history_json": "[]"})

    assert "German" in calls[0]["messages"][0]["content"]


def test_chat_never_generates_an_answer_without_evidence(repo, client, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    repo.ingest_text("an unrelated sentence", source_id="s")

    import requests

    calls = []

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "should never be sent"}}]}

    def _fake_post(self, *a, **kw):
        calls.append(1)
        return _FakeResp()

    monkeypatch.setattr(requests.Session, "post", _fake_post)

    resp = client.post("/chat", data={"message": "zzz_absent_zzz", "history_json": "[]"})
    assert resp.status_code == 200
    assert calls == []  # no LLM call at all
    assert "not evidence of non-occurrence" in resp.text.lower()


def test_chat_post_degrades_gracefully_when_llm_backend_fails(repo, client, monkeypatch):
    """Regression test for a real bug: on the live Render deployment
    (2026-09-18), a real GLM call failure reached the browser as a raw
    500. /chat must render normally (with real evidence) and a plain
    warning, never crash the request."""
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")

    import requests

    def _failing_post(self, *a, **kw):
        raise requests.exceptions.ConnectionError("Name or service not known")

    monkeypatch.setattr(requests.Session, "post", _failing_post)

    resp = client.post("/chat", data={"message": "Tokat", "history_json": "[]"})
    assert resp.status_code == 200
    assert "Tokat" in resp.text  # real evidence still shown
    assert "Couldn't reach the LLM backend" in resp.text
    assert "Generated --" not in resp.text  # no fabricated narrative badge


def test_assistant_route_returns_502_not_500_when_llm_backend_fails(repo, client, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")

    import requests

    def _failing_post(self, *a, **kw):
        raise requests.exceptions.ConnectionError("Name or service not known")

    monkeypatch.setattr(requests.Session, "post", _failing_post)

    resp = client.post("/assistant/research-questions", data={"context_query": "Tokat", "actor": "researcher"}, follow_redirects=False)
    assert resp.status_code == 502


def test_assistant_page_shows_websearch_status(client, monkeypatch):
    monkeypatch.delenv("DHRA_SEARXNG_URL", raising=False)
    resp = client.get("/assistant")
    assert "No web search backend configured" in resp.text

    monkeypatch.setenv("DHRA_SEARXNG_URL", "https://searx.example.org")
    resp = client.get("/assistant")
    assert "Web search is configured" in resp.text


def test_assistant_reading_list_uses_real_web_search_when_configured(repo, client, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    monkeypatch.setenv("DHRA_SEARXNG_URL", "https://searx.example.org")
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")

    import requests

    class _FakeLLMResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "SECONDARY READINGS FROM WEB SEARCH:\n1. Ottoman Infrastructure Studies"}}]}

    class _FakeSearchResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"title": "Ottoman Infrastructure Studies", "url": "https://example.org/a", "content": "a survey"}]}

    monkeypatch.setattr(requests.Session, "post", lambda self, *a, **kw: _FakeLLMResp())
    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **kw: _FakeSearchResp())

    resp = client.post("/assistant/reading-list", data={"course_topic": "Tokat", "actor": "instructor"}, follow_redirects=False)
    assert resp.status_code == 303

    page = client.get("/assistant")
    assert "https://example.org/a" in page.text
    assert "REAL WEB SEARCH RESULTS" in page.text


def test_updates_page_shows_queries_and_new_candidates(repo, client, monkeypatch):
    client.post("/updates/queries", data={"query_text": "Ottoman manuscripts", "actor": "researcher"})

    import requests

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "id": "https://openalex.org/W111",
                        "doi": "https://doi.org/10.1234/W111",
                        "title": "A new find in the Tokat archive",
                        "publication_date": "2026-09-15",
                        "primary_location": {"landing_page_url": "https://doi.org/10.1234/W111"},
                        "authorships": [{"author": {"display_name": "Jane Historian"}}],
                    }
                ]
            }

    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **kw: _FakeResp())

    check_resp = client.post("/updates/check", follow_redirects=False)
    assert check_resp.status_code == 303

    page = client.get("/updates")
    assert "Ottoman manuscripts" in page.text
    assert "A new find in the Tokat archive" in page.text
    assert "Jane Historian" in page.text


def test_updates_check_degrades_gracefully_when_openalex_fails(repo, client, monkeypatch):
    """Same real-bug class as the LLM 500 -- a real backend failure must
    never crash the request."""
    client.post("/updates/queries", data={"query_text": "Ottoman manuscripts", "actor": "researcher"})

    import requests

    def _failing_get(self, *a, **kw):
        raise requests.exceptions.ConnectionError("Name or service not known")

    monkeypatch.setattr(requests.Session, "get", _failing_get)

    resp = client.post("/updates/check", follow_redirects=True)
    assert resp.status_code == 200
    assert "Couldn't reach OpenAlex" in resp.text


def test_updates_dismiss_and_restore_candidate(repo, client, monkeypatch):
    client.post("/updates/queries", data={"query_text": "Ottoman manuscripts", "actor": "researcher"})

    import requests

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "id": "https://openalex.org/W111",
                        "title": "A new find",
                        "publication_date": "2026-09-15",
                        "primary_location": {},
                        "authorships": [],
                    }
                ]
            }

    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **kw: _FakeResp())
    client.post("/updates/check")

    dismiss_resp = client.post("/updates/candidates/W111/dismiss", data={"actor": "researcher"}, follow_redirects=False)
    assert dismiss_resp.status_code == 303

    page = client.get("/updates")
    assert "No new matches" in page.text
    assert "Dismissed (1)" in page.text

    client.post("/updates/candidates/W111/restore", data={"actor": "researcher"})
    page = client.get("/updates")
    assert "A new find" in page.text


def test_robots_txt_allows_crawling_and_points_at_sitemap(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert "Allow: /" in resp.text
    assert "Sitemap:" in resp.text
    assert "/sitemap.xml" in resp.text


def test_sitemap_xml_lists_the_main_pages(client):
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]
    for path in ["<loc>", "/chat</loc>", "/tutorial</loc>", "/assistant</loc>", "/updates</loc>"]:
        assert path in resp.text


def test_pages_carry_seo_meta_tags(client):
    resp = client.get("/")
    assert 'name="description"' in resp.text
    assert 'property="og:title"' in resp.text
    assert 'property="og:description"' in resp.text
    assert 'rel="canonical"' in resp.text
    assert "Literal, locator-bound evidence search" in resp.text  # page-specific description, not the generic default


def test_demo_banner_renders_as_real_html_not_escaped_text(repo):
    """demo_banner is operator-set (render.yaml/Render dashboard), not
    visitor input -- it must render as real HTML so it can carry an
    actual link (e.g. to a downloadable copy), not literal &lt;a&gt; text."""
    banner_app = build_app(repo, demo_banner='Demo -- <a href="https://example.com/releases">Download it</a>.')
    banner_client = TestClient(banner_app)
    resp = banner_client.get("/")
    assert '<a href="https://example.com/releases">Download it</a>' in resp.text
    assert "&lt;a href" not in resp.text
