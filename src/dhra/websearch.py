"""Real web search -- OPEN_QUESTIONS.md #28: `draft_reading_list`'s
"UNVERIFIED SUGGESTIONS" section previously came only from the model's
own training-data recall, with no way to check it against anything
actually retrieved. Adrian's Discord suggestion (a self-hosted SearXNG
instance) is the concrete shape wired here: a real HTTP client against
SearXNG's JSON search API (`GET /search?q=...&format=json`, verified
against docs.searxng.org), which the researcher points at their own
instance via `DHRA_SEARXNG_URL` -- the same "researcher supplies their
own infrastructure via an env var" pattern as `dhra.llm`'s GLM key
(#24). This repo does not host a search backend itself.

Most public SearXNG instances disable `format=json` (SearXNG's own
anti-scraping default -- `search.formats` in `settings.yml`), so this
is written for a researcher-controlled instance (self-hosted, or a
public one they've confirmed allows JSON), not any public instance by
default.

Like `dhra.llm`, absence is the honest default: with no
`DHRA_SEARXNG_URL` set, `WebSearchConfig.from_env()` raises
`WebSearchError` and every caller here falls back to the previous
recall-only behaviour (still clearly labelled unverified) rather than
crashing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests


class WebSearchError(Exception):
    pass


@dataclass(frozen=True)
class WebSearchConfig:
    base_url: str
    timeout: float = 15.0

    @classmethod
    def from_env(cls) -> "WebSearchConfig":
        base_url = os.environ.get("DHRA_SEARXNG_URL")
        if not base_url:
            raise WebSearchError(
                "DHRA_SEARXNG_URL is not set -- no web search backend configured "
                "(see OPEN_QUESTIONS.md #28)."
            )
        return cls(base_url=base_url.rstrip("/"))


@dataclass(frozen=True)
class WebResult:
    title: str
    url: str
    snippet: str


class WebSearchClient:
    """SearXNG's JSON search API. Never lets a real backend failure (bad
    URL, an instance with JSON disabled, a timeout) escape as a raw
    exception -- same discipline as `dhra.llm.LLMClient.complete`, for
    the same reason (a free/researcher-run instance fails in practice,
    not just hypothetically)."""

    def __init__(self, config: WebSearchConfig, *, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()

    def search(self, query: str, *, max_results: int = 5) -> list[WebResult]:
        try:
            resp = self.session.get(
                f"{self.config.base_url}/search",
                params={"q": query, "format": "json"},
                timeout=self.config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as exc:
            raise WebSearchError(f"web search backend request failed: {exc}") from exc
        except ValueError as exc:  # resp.json() on a non-JSON body (e.g. an HTML page, JSON disabled)
            raise WebSearchError(f"web search backend returned a non-JSON response: {exc}") from exc
        try:
            results = data["results"]
        except (KeyError, TypeError) as exc:
            raise WebSearchError(f"unexpected response shape from web search backend: {data!r}") from exc
        return [
            WebResult(title=r.get("title", ""), url=r.get("url", ""), snippet=r.get("content", ""))
            for r in results[:max_results]
        ]


def web_search(repo, client: WebSearchClient, query: str, *, task: str | None = None) -> list[WebResult]:
    """The wrapper every caller in this repo should use instead of
    `client.search` directly -- logs the query the same way
    `evidence.search` logs a corpus search (`DHRARepo.log_tool_invocation`),
    so the methods export's "full query set actually run" (section 11.4)
    stays honest about external search too, not just corpus search."""
    repo.log_tool_invocation(tool="web_search", purpose="reading_list_web_search", parameters={"query": query}, task=task)
    return client.search(query)
