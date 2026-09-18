"""LLM-backed features -- dhra.llm, dhra.research_assistant, dhra.teaching,
dhra.peer_review.

No real network calls: GLM hosting (Uni Bern, per the researcher's own
choice -- see OPEN_QUESTIONS.md) doesn't exist yet to call, so
`LLMClient` is exercised against a fake `requests.Session` that returns
real OpenAI-compatible-shaped responses. This proves the request/response
handling is correct; it does not prove the real endpoint, once it
exists, behaves identically -- that needs a live smoke test once Adrian's
hosting is up, the same caveat `test_live_zenodo_acquisition_end_to_end`
records for a different real backend.
"""

from __future__ import annotations

import os

import pytest

from dhra.llm import LLMClient, LLMConfig, LLMError, log_and_complete
from dhra.peer_review import extract_claims, review_paper
from dhra.repo import DHRARepo
from dhra.research_assistant import suggest_research_questions
from dhra.teaching import assess_paper_against_rubric, draft_exam_questions, draft_reading_list


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


class _FakeResponse:
    def __init__(self, content: str):
        self._content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


class _FakeSession:
    """Records every request; always returns `content` -- good enough to
    prove dhra.llm's request-building and response-parsing are correct
    against the real OpenAI-compatible shape (verified against
    docs.z.ai before writing dhra.llm, not assumed)."""

    def __init__(self, content: str):
        self.content = content
        self.calls: list[dict] = []

    def post(self, url, *, headers, json, timeout):
        self.calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(self.content)


def _client(content: str) -> tuple[LLMClient, _FakeSession]:
    config = LLMConfig(base_url="https://glm.example.unibe.ch/v1", api_key="test-key", model="glm-4.6")
    session = _FakeSession(content)
    return LLMClient(config, session=session), session


# --- dhra.llm ----------------------------------------------------------------


def test_config_from_env_requires_vars(monkeypatch):
    monkeypatch.delenv("DHRA_GLM_BASE_URL", raising=False)
    monkeypatch.delenv("DHRA_GLM_API_KEY", raising=False)
    with pytest.raises(LLMError):
        LLMConfig.from_env()


def test_config_from_env_reads_real_vars(monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example.unibe.ch/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "secret")
    config = LLMConfig.from_env()
    assert config.base_url == "https://glm.example.unibe.ch/v1"
    assert config.model == "glm-4.6"  # default


def test_client_complete_posts_openai_compatible_request_and_parses_response():
    client, session = _client("a real completion")
    result = client.complete([{"role": "user", "content": "hello"}])
    assert result == "a real completion"
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"] == "https://glm.example.unibe.ch/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer test-key"
    assert call["json"]["model"] == "glm-4.6"
    assert call["json"]["messages"] == [{"role": "user", "content": "hello"}]


def test_client_complete_raises_on_unexpected_shape():
    config = LLMConfig(base_url="https://x", api_key="k", model="m")

    class _BadSession:
        def post(self, *a, **kw):
            return _FakeResponseRaw({"unexpected": "shape"})

    class _FakeResponseRaw:
        def __init__(self, d):
            self._d = d

        def raise_for_status(self):
            pass

        def json(self):
            return self._d

    client = LLMClient(config, session=_BadSession())
    with pytest.raises(LLMError):
        client.complete([{"role": "user", "content": "hi"}])


def test_log_and_complete_records_a_real_model_invoked_event(repo):
    client, _session = _client("ok")
    log_and_complete(client, repo, purpose="test_purpose", messages=[{"role": "user", "content": "hi"}])
    from dhra.methods_export import build_methods_statement

    statement = build_methods_statement(repo.events)
    assert len(statement.model_invocations) == 1
    assert statement.model_invocations[0].model == "glm-4.6"
    assert statement.model_invocations[0].purpose == "test_purpose"


# --- dhra.research_assistant --------------------------------------------------


def test_suggest_research_questions_uses_real_search_results(repo):
    repo.ingest_text("The bridge at Tokat was repaired in 1849 after a storm.", source_id="s")
    client, session = _client("1. Was the 1849 storm part of a wider regional weather event?")

    draft_id = suggest_research_questions(repo, client, context_query="Tokat", actor="researcher")
    from dhra.drafting import get_draft

    draft = get_draft(repo, draft_id)
    assert draft is not None
    assert "wider regional weather event" in draft.text
    assert "Tokat" in draft.text  # the query that prompted it is recorded

    # the model only ever saw real corpus excerpts, not an empty prompt
    sent_content = session.calls[0]["json"]["messages"][1]["content"]
    assert "Tokat" in sent_content  # the matched excerpt, not the full sentence -- search returns matched spans


def test_suggest_research_questions_refuses_without_evidence(repo):
    repo.ingest_text("an unrelated sentence", source_id="s")
    client, _session = _client("irrelevant")
    with pytest.raises(ValueError):
        suggest_research_questions(repo, client, context_query="zzz_absent_zzz", actor="researcher")


# --- dhra.teaching -------------------------------------------------------------


def test_draft_exam_questions_creates_a_reviewable_draft(repo):
    client, _session = _client("1. Describe the causes of the 1849 flood.")
    draft_id = draft_exam_questions(repo, client, source_text="Lecture notes on the 1849 flood.", n_questions=1, actor="instructor")
    from dhra.drafting import DraftStatus, get_draft

    draft = get_draft(repo, draft_id)
    assert draft.status == DraftStatus.PENDING  # never auto-used
    assert "1849 flood" in draft.text


def test_assess_paper_against_rubric_never_assigns_a_grade(repo):
    client, session = _client("Criterion 1: the student quotes the primary source directly. Met.")
    draft_id = assess_paper_against_rubric(
        repo, client, paper_text="My essay argues that...", rubric_text="1. Uses primary sources.", actor="instructor"
    )
    from dhra.drafting import get_draft

    draft = get_draft(repo, draft_id)
    assert draft is not None
    sent_system_prompt = session.calls[0]["json"]["messages"][0]["content"]
    assert "do not assign a grade" in sent_system_prompt.lower() or "not assign a grade" in sent_system_prompt.lower()


def test_draft_reading_list_separates_corpus_from_unverified_suggestions(repo):
    repo.ingest_text("The bridge at Tokat was repaired in 1849.", source_id="s")
    content = (
        "PRIMARY SOURCES FROM YOUR CORPUS:\n1. The Tokat bridge repair record.\n\n"
        "UNVERIFIED SUGGESTIONS (check before using -- not grounded in retrieved evidence):\n1. Some Book, Ch. 3."
    )
    client, session = _client(content)

    draft_id = draft_reading_list(repo, client, course_topic="Tokat", actor="instructor")
    from dhra.drafting import get_draft

    draft = get_draft(repo, draft_id)
    assert "PRIMARY SOURCES FROM YOUR CORPUS" in draft.text
    assert "UNVERIFIED SUGGESTIONS" in draft.text
    assert "not grounded in retrieved evidence" in draft.text

    # the model saw the real matched excerpt, not an empty corpus section
    sent_content = session.calls[0]["json"]["messages"][1]["content"]
    assert "Tokat" in sent_content


def test_draft_reading_list_works_with_no_corpus_matches(repo):
    repo.ingest_text("an unrelated sentence", source_id="s")
    client, session = _client("UNVERIFIED SUGGESTIONS (check before using -- not grounded in retrieved evidence):\n1. Some Book.")

    draft_id = draft_reading_list(repo, client, course_topic="zzz_absent_zzz", actor="instructor")
    from dhra.drafting import get_draft

    draft = get_draft(repo, draft_id)
    assert draft is not None  # does not raise, unlike suggest_research_questions
    sent_content = session.calls[0]["json"]["messages"][1]["content"]
    assert "no matching items found" in sent_content


# --- dhra.peer_review ----------------------------------------------------------


_EXTRACTION_RESPONSE = (
    "CLAIM: The bridge at Tokat was destroyed, not merely damaged, in 1849.\n"
    "QUERY: bridge at Tokat\n"
    "QUERY: destroyed\n"
    "---\n"
)


def test_extract_claims_parses_the_requested_format(repo):
    client, _session = _client(_EXTRACTION_RESPONSE)
    claims = extract_claims(client, repo, paper_text="Some paper text.")
    assert claims == [("The bridge at Tokat was destroyed, not merely damaged, in 1849.", ["bridge at Tokat", "destroyed"])]


def test_review_paper_finds_real_candidate_evidence_and_never_assigns_status(repo):
    repo.ingest_text("The bridge at Tokat was repaired in 1849 after a storm.", source_id="s")
    client, _session = _client(_EXTRACTION_RESPONSE)

    draft_id = review_paper(repo, client, paper_text="Some paper text.", actor="reviewer")
    from dhra.drafting import get_draft

    draft = get_draft(repo, draft_id)
    assert "bridge at Tokat" in draft.text  # real candidate evidence (the matched span), found by real search
    assert "E1" not in draft.text and "E5" not in draft.text  # no status assigned -- that's still assess_claim's job

    # no claim.assessed event exists from this -- confirmed at the projection level, not just text-absence
    assert repo.projection().claims == {}


def test_review_paper_raises_when_nothing_extracted(repo):
    client, _session = _client("no claims here, malformed output")
    with pytest.raises(ValueError):
        review_paper(repo, client, paper_text="text", actor="reviewer")
