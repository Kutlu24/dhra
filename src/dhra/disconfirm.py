"""Disconfirmation search -- DHRA_BUILD_SPEC.md section 11.2
(`POST /evidence/disconfirm`) and section 6 (Phase 2).

Section 10: the model "may propose research questions and
disconfirmation strategies" -- the actual reformulation of a claim into
refutation-oriented search queries is exactly that kind of proposal, so
it belongs on the model side (not built here; there is no LLM-calling
layer in this repo yet). This module is the deterministic half: given
queries a caller (eventually: the model, via that not-yet-built layer)
already proposed, it runs them for real through the existing evidence
pipeline and reports what came back -- the same caller-supplies-the-
judgement-call pattern as `DHRARepo.assess_claim`.
"""

from __future__ import annotations

from dataclasses import dataclass

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
