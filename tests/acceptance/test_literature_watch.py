"""dhra.literature_watch -- external new-publication tracking via
OpenAlex. No real network calls: exercised against a fake
`requests.Session` returning the real OpenAlex works-search response
shape (verified live against https://api.openalex.org/works before
writing literature_watch.py, not assumed).
"""

from __future__ import annotations

import pytest
import requests

from dhra.literature_watch import (
    LiteratureWatchError,
    add_watch_query,
    check_for_updates,
    dismiss_candidate,
    list_candidates,
    list_dismissed_candidates,
    list_watch_queries,
    remove_watch_query,
    restore_candidate,
)
from dhra.repo import DHRARepo


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


def _openalex_work(work_id: str, title: str, pub_date: str = "2026-09-15") -> dict:
    return {
        "id": f"https://openalex.org/{work_id}",
        "doi": f"https://doi.org/10.1234/{work_id}",
        "title": title,
        "display_name": title,
        "publication_date": pub_date,
        "primary_location": {"landing_page_url": f"https://doi.org/10.1234/{work_id}"},
        "authorships": [
            {"author": {"display_name": "Jane Historian"}},
            {"author": {"display_name": "John Scholar"}},
        ],
    }


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _FakeSession:
    def __init__(self, results: list[dict]):
        self.results = results
        self.calls: list[dict] = []

    def get(self, url, *, params, headers, timeout):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return _FakeResponse({"results": self.results})


# --- watch queries -------------------------------------------------------------


def test_add_and_list_watch_queries(repo):
    add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")
    add_watch_query(repo, query_text="Tokat archive", actor="researcher")
    queries = list_watch_queries(repo)
    assert [q.query_text for q in queries] == ["Ottoman manuscripts", "Tokat archive"]


def test_remove_watch_query_is_reversible_not_a_delete(repo):
    watch_id = add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")
    remove_watch_query(repo, watch_id, actor="researcher")
    assert list_watch_queries(repo) == []
    # nothing was deleted from the log -- both events are still there
    types = [e["type"] for e in repo.events.read_all()]
    assert "literature_watch_query.added" in types
    assert "literature_watch_query.removed" in types


# --- checking for updates --------------------------------------------------------


def test_check_for_updates_with_no_queries_makes_no_call(repo):
    session = _FakeSession([])
    result = check_for_updates(repo, session=session)
    assert result == []
    assert session.calls == []


def test_check_for_updates_finds_real_candidates_and_logs_them(repo):
    add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")
    session = _FakeSession([_openalex_work("W111", "A new find in the Tokat archive")])

    result = check_for_updates(repo, session=session)
    assert len(result) == 1
    assert result[0].work_id == "W111"
    assert result[0].title == "A new find in the Tokat archive"
    assert result[0].authors == ("Jane Historian", "John Scholar")
    assert result[0].link == "https://doi.org/10.1234/W111"

    assert session.calls[0]["params"]["search"] == '"Ottoman manuscripts"'  # exact phrase, not loose word matching
    assert session.calls[0]["params"]["sort"] == "publication_date:desc"

    candidates = list_candidates(repo)
    assert len(candidates) == 1
    assert candidates[0].work_id == "W111"


def test_check_for_updates_never_resurfaces_a_previously_seen_work(repo):
    add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")
    session = _FakeSession([_openalex_work("W111", "First find")])
    first = check_for_updates(repo, session=session)
    assert len(first) == 1

    # same work still shows up in OpenAlex's response on a second check --
    # must not be reported as new again
    second = check_for_updates(repo, session=session)
    assert second == []
    assert len(list_candidates(repo)) == 1


def test_check_for_updates_raises_llm_watch_error_on_backend_failure(repo):
    add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")

    class _FailingSession:
        def get(self, *a, **kw):
            raise requests.exceptions.ConnectionError("Name or service not known")

    with pytest.raises(LiteratureWatchError):
        check_for_updates(repo, session=_FailingSession())


def test_check_for_updates_raises_on_http_error_status(repo):
    add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")

    class _ErrorResponse:
        def raise_for_status(self):
            raise requests.exceptions.HTTPError("429 Client Error: Too Many Requests")

    class _ErrorSession:
        def get(self, *a, **kw):
            return _ErrorResponse()

    with pytest.raises(LiteratureWatchError):
        check_for_updates(repo, session=_ErrorSession())


# --- dismiss / restore -----------------------------------------------------------


def test_dismiss_candidate_hides_it_from_the_active_list(repo):
    add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")
    session = _FakeSession([_openalex_work("W111", "A new find")])
    check_for_updates(repo, session=session)

    dismiss_candidate(repo, "W111", actor="researcher")
    assert list_candidates(repo) == []
    dismissed = list_dismissed_candidates(repo)
    assert len(dismissed) == 1
    assert dismissed[0].work_id == "W111"


def test_restore_candidate_brings_it_back(repo):
    add_watch_query(repo, query_text="Ottoman manuscripts", actor="researcher")
    session = _FakeSession([_openalex_work("W111", "A new find")])
    check_for_updates(repo, session=session)
    dismiss_candidate(repo, "W111", actor="researcher")

    restore_candidate(repo, "W111", actor="researcher")
    assert len(list_candidates(repo)) == 1
    assert list_dismissed_candidates(repo) == []
