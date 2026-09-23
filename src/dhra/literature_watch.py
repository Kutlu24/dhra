"""External literature watch -- new publications matching saved queries,
via OpenAlex's open, keyless works API (https://api.openalex.org,
verified live before writing this, not assumed). `PermissionClass.READ`
(permissions.py): search/retrieve/compare, no approval checkpoint, fully
logged -- the same class as `dhra.evidence.search` and `dhra.monitoring`,
and for the same reason: this only ever surfaces public bibliographic
metadata (title/authors/date/DOI/link) for the researcher to look at.
It never ingests anything into the corpus and never touches licensed
full-text content, so it carries none of the licensing-tracking concerns
`dhra.zenodo`'s RateLimiter/SourceEntry apparatus exists for.

No scheduler/daemon here either, same reasoning as `dhra.monitoring`
(see that module's docstring): `check_for_updates` runs whenever the
researcher decides to -- the web UI's "Check now" button, or
`dhra watch check` from the researcher's own cron if they want real
periodicity -- never a background process DHRA pretends is watching
continuously when none is running.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

from dhra.repo import DHRARepo
from dhra.ulid import new_ulid

OPENALEX_API_BASE = "https://api.openalex.org"


class LiteratureWatchError(Exception):
    pass


@dataclass(frozen=True)
class WatchQuery:
    watch_id: str
    query_text: str
    actor: str
    created_ts: str


@dataclass(frozen=True)
class LiteratureCandidate:
    work_id: str  # short OpenAlex ID, e.g. "W7213458047"
    watch_id: str
    title: str
    authors: tuple[str, ...]
    publication_date: str | None
    doi: str | None
    link: str | None
    found_ts: str


def add_watch_query(repo: DHRARepo, *, query_text: str, actor: str, task: str | None = None) -> str:
    watch_id = new_ulid()
    repo.events.append("literature_watch_query.added", watch_id=watch_id, query_text=query_text, actor=actor, task=task)
    return watch_id


def remove_watch_query(repo: DHRARepo, watch_id: str, *, actor: str, task: str | None = None) -> None:
    """Reversible, like item exclusion (I4) -- the query can be re-added;
    nothing about it is deleted from the event log."""
    repo.events.append("literature_watch_query.removed", watch_id=watch_id, actor=actor, task=task)


def list_watch_queries(repo: DHRARepo) -> list[WatchQuery]:
    queries: dict[str, WatchQuery] = {}
    removed: set[str] = set()
    for event in repo.events.read_all():
        if event["type"] == "literature_watch_query.added":
            queries[event["watch_id"]] = WatchQuery(
                watch_id=event["watch_id"],
                query_text=event["query_text"],
                actor=event["actor"],
                created_ts=event["ts"],
            )
        elif event["type"] == "literature_watch_query.removed":
            removed.add(event["watch_id"])
    return sorted((q for wid, q in queries.items() if wid not in removed), key=lambda q: q.created_ts)


def _previously_seen_work_ids(repo: DHRARepo) -> set[str]:
    return {event["work_id"] for event in repo.events.read_all() if event["type"] == "literature_candidate.found"}


def check_for_updates(
    repo: DHRARepo,
    *,
    session: requests.Session | None = None,
    per_query_limit: int = 10,
    timeout: float = 20.0,
    task: str | None = None,
) -> list[LiteratureCandidate]:
    """Runs every active watch query against OpenAlex. A real backend
    failure (network, rate limit, malformed response) is wrapped as
    LiteratureWatchError rather than left to propagate as a raw
    exception -- see dhra.llm.LLMClient.complete's docstring for why
    that distinction matters to every caller of this function."""
    queries = list_watch_queries(repo)
    if not queries:
        return []
    session = session or requests.Session()
    already_seen = _previously_seen_work_ids(repo)
    new_candidates: list[LiteratureCandidate] = []
    for wq in queries:
        try:
            resp = session.get(
                f"{OPENALEX_API_BASE}/works",
                # quoted -- OpenAlex's unquoted `search` matches each word
                # independently (very loose: "Ottoman manuscripts" pulled
                # in an unrelated smoking-prevalence paper in testing,
                # 2026-09-18); an exact phrase is what "watch this topic"
                # actually means here.
                params={"search": f'"{wq.query_text}"', "sort": "publication_date:desc", "per_page": per_query_limit},
                headers={"User-Agent": "DHRA/0.0.1 (Digital Humanities Research Assistant)"},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            raise LiteratureWatchError(f"OpenAlex request failed for query {wq.query_text!r}: {exc}") from exc
        except ValueError as exc:
            raise LiteratureWatchError(f"OpenAlex returned a non-JSON response for query {wq.query_text!r}: {exc}") from exc

        for work in data.get("results", []):
            raw_id = work.get("id") or ""
            work_id = raw_id.rsplit("/", 1)[-1]
            if not work_id or work_id in already_seen:
                continue
            authors = tuple(
                a["author"]["display_name"]
                for a in work.get("authorships", [])
                if a.get("author", {}).get("display_name")
            )
            title = work.get("title") or work.get("display_name") or "(untitled)"
            publication_date = work.get("publication_date")
            doi = work.get("doi")
            link = (work.get("primary_location") or {}).get("landing_page_url") or doi
            event = repo.events.append(
                "literature_candidate.found",
                work_id=work_id,
                watch_id=wq.watch_id,
                title=title,
                authors=list(authors),
                publication_date=publication_date,
                doi=doi,
                link=link,
                task=task,
            )
            new_candidates.append(
                LiteratureCandidate(
                    work_id=work_id,
                    watch_id=wq.watch_id,
                    title=title,
                    authors=authors,
                    publication_date=publication_date,
                    doi=doi,
                    link=link,
                    found_ts=event["ts"],
                )
            )
            already_seen.add(work_id)
    return new_candidates


def _dismissed_work_ids(repo: DHRARepo) -> set[str]:
    dismissed: set[str] = set()
    for event in repo.events.read_all():
        if event["type"] == "literature_candidate.dismissed":
            dismissed.add(event["work_id"])
        elif event["type"] == "literature_candidate.restored":
            dismissed.discard(event["work_id"])
    return dismissed


def list_candidates(repo: DHRARepo, *, include_dismissed: bool = False) -> list[LiteratureCandidate]:
    candidates: dict[str, LiteratureCandidate] = {}
    for event in repo.events.read_all():
        if event["type"] == "literature_candidate.found":
            candidates[event["work_id"]] = LiteratureCandidate(
                work_id=event["work_id"],
                watch_id=event["watch_id"],
                title=event["title"],
                authors=tuple(event.get("authors") or ()),
                publication_date=event.get("publication_date"),
                doi=event.get("doi"),
                link=event.get("link"),
                found_ts=event["ts"],
            )
    results = list(candidates.values())
    if not include_dismissed:
        dismissed = _dismissed_work_ids(repo)
        results = [c for c in results if c.work_id not in dismissed]
    return sorted(results, key=lambda c: c.found_ts, reverse=True)


def list_dismissed_candidates(repo: DHRARepo) -> list[LiteratureCandidate]:
    dismissed = _dismissed_work_ids(repo)
    return [c for c in list_candidates(repo, include_dismissed=True) if c.work_id in dismissed]


def dismiss_candidate(repo: DHRARepo, work_id: str, *, actor: str, task: str | None = None) -> None:
    repo.events.append("literature_candidate.dismissed", work_id=work_id, actor=actor, task=task)


def restore_candidate(repo: DHRARepo, work_id: str, *, actor: str, task: str | None = None) -> None:
    repo.events.append("literature_candidate.restored", work_id=work_id, actor=actor, task=task)
