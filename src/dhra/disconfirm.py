"""Disconfirmation search -- DHRA_BUILD_SPEC.md section 11.2
(`POST /evidence/disconfirm`) and section 6 (Phase 2).

Section 10: the model "may propose research questions and
disconfirmation strategies" -- the actual reformulation of a claim into
refutation-oriented search queries is exactly that kind of proposal.
`disconfirm_search` is the deterministic half: given queries a caller
already proposed, it runs them for real through the existing evidence
pipeline and reports what came back -- the same caller-supplies-the-
judgement-call pattern as `DHRARepo.assess_claim`.

OPEN_QUESTIONS.md #25 (2026-09-20): `propose_and_run_disconfirmation`
is the model-side half, now that `dhra.llm` exists -- the same
"LLM proposes, deterministic code executes and stores as a reviewable
draft" pattern as `dhra.research_assistant.suggest_research_questions`.
`disconfirm_search` itself is unchanged: it still takes queries as a
plain argument and has no LLM dependency, so every existing caller
(direct, or via the new wrapper) keeps working.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dhra.drafting import create_draft
from dhra.llm import LLMClient, log_and_complete
from dhra.repo import DHRARepo
from dhra.response import Response
from dhra.evidence import search


@dataclass(frozen=True)
class DisconfirmationOutcome:
    query: str
    response: Response


@dataclass(frozen=True)
class DisconfirmationResult:
    claim_text: str
    outcomes: tuple[DisconfirmationOutcome, ...]
    corpus_version: str

    def found_refuting_evidence(self) -> bool:
        return any(o.response.evidence for o in self.outcomes)


def disconfirm_search(repo: DHRARepo, claim_text: str, negated_queries: list[str], *, task: str | None = None) -> DisconfirmationResult:
    outcomes = tuple(DisconfirmationOutcome(query=q, response=search(repo, q, task=task)) for q in negated_queries)
    version = repo.corpus_version()
    return DisconfirmationResult(claim_text=claim_text, outcomes=outcomes, corpus_version=version.manifest_hash)


_DISCONFIRM_SYSTEM_PROMPT = (
    "A historian wants to try to disprove a claim about their own primary-source corpus, "
    "rather than only looking for support. Given the claim, propose 2-4 short, literal "
    "search phrases (a few words each, wording likely to appear verbatim in a primary "
    "source) that would surface material contradicting or complicating the claim -- not "
    "material repeating it. One phrase per line, nothing else: no numbering, no commentary."
)

_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")


def propose_disconfirmation_queries(client: LLMClient, repo: DHRARepo, *, claim_text: str, task: str | None = None) -> list[str]:
    """Returns the model's proposed refutation-oriented search phrases
    -- a proposal, not evidence (section 10). Lines are stripped of
    common list markers ("1.", "-", "*") a model might add despite the
    prompt; blank lines are dropped."""
    messages = [
        {"role": "system", "content": _DISCONFIRM_SYSTEM_PROMPT},
        {"role": "user", "content": f"Claim: {claim_text}"},
    ]
    raw = log_and_complete(client, repo, purpose="disconfirmation_query_proposal", messages=messages, task=task)
    queries = []
    for line in raw.splitlines():
        line = _LIST_MARKER_RE.sub("", line).strip()
        if line:
            queries.append(line)
    return queries


def propose_and_run_disconfirmation(repo: DHRARepo, client: LLMClient, *, claim_text: str, actor: str, task: str | None = None) -> str:
    """Proposes refutation-oriented queries (model), runs them for real
    (`disconfirm_search`, deterministic), and stores the outcome as a
    reviewable PREPARE-class draft (dhra.drafting). Returns the
    draft_id. Raises ValueError if the model proposed nothing usable --
    same "nothing to reason from" discipline as
    `suggest_research_questions`."""
    queries = propose_disconfirmation_queries(client, repo, claim_text=claim_text, task=task)
    if not queries:
        raise ValueError("no disconfirmation queries could be proposed for this claim")

    result = disconfirm_search(repo, claim_text, queries, task=task)

    lines = [
        f"Disconfirmation search for: {claim_text}",
        f"(corpus version {result.corpus_version[:12]})",
        f"Queries proposed by the model -- verify they're actually refutation-oriented, not just paraphrases:",
        "",
    ]
    for outcome in result.outcomes:
        lines.append(f"QUERY: {outcome.query}")
        if outcome.response.evidence:
            for p in outcome.response.evidence:
                lines.append(f"  - \"{p.text}\" [{p.locator.item_id}/{p.locator.rep_id}:{p.locator.start}-{p.locator.end}]")
        else:
            lines.append("  - no matching evidence found in this corpus")
        lines.append("")
    lines.append(
        "Refuting-looking evidence was found for at least one query -- check it closely."
        if result.found_refuting_evidence()
        else "No refuting-looking evidence turned up for any proposed query in this corpus."
    )

    return create_draft(repo, kind="disconfirmation", text="\n".join(lines), actor=actor, task=task)
