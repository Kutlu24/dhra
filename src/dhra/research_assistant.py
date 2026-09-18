"""Research question suggestion -- section 10: "The model may... propose
research questions and disconfirmation strategies." This is that,
finally wired to a real model (dhra.llm) instead of being a caller
obligation.

Deterministic code still does the actual evidence work: the corpus
excerpts the model sees come from a real `evidence.search()` call, not
the model's own imagination, and every suggestion is stored as a
`Draft` (dhra.drafting) -- reviewable, dismissible, never presented as
a finding. Suggesting a question is not evidence of anything; it is a
prompt for the researcher to go find out.
"""

from __future__ import annotations

from dhra.drafting import create_draft
from dhra.evidence import search as evidence_search
from dhra.llm import LLMClient, log_and_complete
from dhra.repo import DHRARepo

_SYSTEM_PROMPT = (
    "You are assisting a historian in reasoning about their own primary-source corpus. "
    "You are given a set of excerpts already retrieved from that corpus. Propose research "
    "questions, gaps, or connections a historian might want to pursue. Do NOT assert any "
    "historical fact that is not explicitly in the excerpts -- you may ask about a gap, "
    "never fill it. Number each suggestion. Be concise: one sentence per suggestion."
)


def suggest_research_questions(
    repo: DHRARepo,
    client: LLMClient,
    *,
    context_query: str,
    actor: str,
    max_passages: int = 8,
    task: str | None = None,
) -> str:
    """Searches the corpus for `context_query`, shows the model only
    those real excerpts (with locators, so a suggestion can be traced
    back to what prompted it), and stores the model's suggestions as a
    PREPARE-class draft. Returns the draft_id."""
    response = evidence_search(repo, context_query, task=task)
    if not response.evidence:
        raise ValueError(f"no evidence found for {context_query!r} -- nothing to reason from (I10's spirit applies here too)")

    excerpts = "\n".join(
        f"- [{p.locator.item_id}/{p.locator.rep_id}:{p.locator.start}-{p.locator.end}] \"{p.text}\""
        for p in response.evidence[:max_passages]
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Corpus excerpts matching '{context_query}':\n{excerpts}\n\nSuggest research directions."},
    ]
    suggestions = log_and_complete(client, repo, purpose="research_question_suggestion", messages=messages, task=task)

    draft_text = f"Suggestions prompted by search for {context_query!r} (corpus version {repo.corpus_version().manifest_hash[:12]}):\n\n{suggestions}"
    return create_draft(repo, kind="research_questions", text=draft_text, actor=actor, task=task)
