"""Peer review support -- scoped narrowly per the researcher's own
framing (2026-09-18): check a paper's claims against the reviewer's own
corpus, don't produce an editorial verdict. The model extracts candidate
claims and short literal search phrases for each (a proposal); deterministic
`evidence.search()` -- already real code, unchanged -- finds whatever
the corpus actually has for each one. No status (E1..E8) is assigned
here: that still requires a human to look at the candidate evidence and
decide via the normal `assess_claim` path, exactly as section 10
requires ("the model may... propose candidate relevance judgements for
verification" -- never assign the judgement itself).

Honest limitation, stated in the report itself, not hidden: corpus
search here is literal-substring (dhra.evidence), not semantic, so a
claim only turns up candidate evidence when the corpus actually shares
some of its wording -- silence does not mean the claim is unsupported
by the wider literature, only that this corpus doesn't textually
overlap with it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from dhra.drafting import create_draft
from dhra.evidence import search as evidence_search
from dhra.llm import LLMClient, log_and_complete
from dhra.models import Passage
from dhra.repo import DHRARepo

_EXTRACT_SYSTEM_PROMPT = (
    "You extract checkable factual claims from an academic paper, for a reviewer who wants "
    "to check them against their own source corpus. For each claim, also propose 1-3 short "
    "literal phrases (a few words each, wording likely to appear verbatim in a primary "
    "source) that could be searched to find corroborating or contradicting material. "
    "Respond in exactly this format, one block per claim, nothing else:\n\n"
    "CLAIM: <the claim, one sentence>\n"
    "QUERY: <short literal phrase>\n"
    "QUERY: <short literal phrase>\n"
    "---\n"
)

_CLAIM_BLOCK_RE = re.compile(r"CLAIM:\s*(.+?)\n((?:QUERY:.*\n?)*)---", re.MULTILINE)
_QUERY_RE = re.compile(r"QUERY:\s*(.+)")


@dataclass(frozen=True)
class ClaimCandidate:
    claim_text: str
    queries: tuple[str, ...]
    candidate_evidence: tuple[Passage, ...]


def extract_claims(client: LLMClient, repo: DHRARepo, *, paper_text: str, task: str | None = None) -> list[tuple[str, list[str]]]:
    """Returns [(claim_text, [query, ...]), ...] -- a proposal, not
    evidence. Parsing failures are silently dropped, not guessed at."""
    messages = [
        {"role": "system", "content": _EXTRACT_SYSTEM_PROMPT},
        {"role": "user", "content": paper_text},
    ]
    raw = log_and_complete(client, repo, purpose="peer_review_claim_extraction", messages=messages, task=task)
    out = []
    for block in _CLAIM_BLOCK_RE.finditer(raw + "\n---"):
        claim_text = block.group(1).strip()
        queries = [m.group(1).strip() for m in _QUERY_RE.finditer(block.group(2))]
        if claim_text and queries:
            out.append((claim_text, queries))
    return out


def review_paper(repo: DHRARepo, client: LLMClient, *, paper_text: str, actor: str, task: str | None = None) -> str:
    """Extracts claims, finds real candidate evidence for each via
    literal search, and stores the whole thing as one PREPARE-class
    draft (dhra.drafting) -- a starting point for the reviewer's own
    reading, never a submitted review. Returns the draft_id."""
    claims = extract_claims(client, repo, paper_text=paper_text, task=task)
    if not claims:
        raise ValueError("no claims could be extracted from this text")

    candidates: list[ClaimCandidate] = []
    for claim_text, queries in claims:
        evidence: list[Passage] = []
        seen_locators = set()
        for q in queries:
            response = evidence_search(repo, q, task=task)
            for p in response.evidence:
                key = (p.locator.item_id, p.locator.rep_id, p.locator.start, p.locator.end)
                if key not in seen_locators:
                    seen_locators.add(key)
                    evidence.append(p)
        candidates.append(ClaimCandidate(claim_text=claim_text, queries=tuple(queries), candidate_evidence=tuple(evidence)))

    lines = [
        f"Peer-review candidate report (corpus version {repo.corpus_version().manifest_hash[:12]}).",
        "Search is literal-substring: no hits means no textual overlap with this corpus, not that the claim is unsupported generally.",
        "",
    ]
    for c in candidates:
        lines.append(f"CLAIM: {c.claim_text}")
        lines.append(f"  (searched: {', '.join(c.queries)})")
        if c.candidate_evidence:
            for p in c.candidate_evidence:
                lines.append(f"  - \"{p.text}\" [{p.locator.item_id}/{p.locator.rep_id}:{p.locator.start}-{p.locator.end}]")
        else:
            lines.append("  - no candidate evidence found in this corpus")
        lines.append("")

    return create_draft(repo, kind="peer_review", text="\n".join(lines), actor=actor, task=task)
