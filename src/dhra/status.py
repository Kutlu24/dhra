"""The epistemic engine -- DHRA_BUILD_SPEC.md section 7.

Section 10 is explicit: the model may not "assign epistemic status" or
"resolve a contradiction between sources". Every function here is
deterministic code over explicit, already-decided evidence sets
(locators a researcher, or a verified deterministic comparison, marked
as supporting/contradicting/negating a claim) -- never a freeform model
judgement. Phase 1 has no independence engine yet (that is Phase 2), so
nothing here can ever produce E2 -- I6 is satisfied by omission, not by
a stub that fakes an independence check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from dhra.models import Locator


class Status(StrEnum):
    ATTESTED = "E1"  # explicitly stated in a source in the corpus
    CORROBORATED = "E2"  # attested in >= 2 sources that PASSED independence -- Phase 2 only
    INFERRED = "E3"  # follows from E1/E2 by a stated chain
    CONTESTED = "E4"  # sources in the corpus disagree
    SINGLE_WITNESS = "E5"  # one source, reliability unestablished
    UNSUPPORTED = "E6"  # not found; scope of search stated
    NEGATIVE = "E7"  # a source positively asserts non-occurrence
    OUT_OF_SCOPE = "E8"  # corpus cannot in principle address this


# Used only to detect an attempted *rise* without new evidence (rule 2).
# E4/E7/E8 are not "weak"/"strong" so much as *disqualifying* for a clean
# rise -- any transition into or out of them always requires a fresh
# assess_claim() call with an explicit evidence-set change, never an
# implicit reinterpretation of the same evidence.
_RANK = {
    Status.UNSUPPORTED: 0,
    Status.OUT_OF_SCOPE: 0,
    Status.NEGATIVE: 0,
    Status.SINGLE_WITNESS: 1,
    Status.CONTESTED: 1,
    Status.ATTESTED: 2,
    Status.INFERRED: 3,
    Status.CORROBORATED: 4,
}


def rank(status: Status) -> int:
    return _RANK[status]


def weakest(statuses: list[Status]) -> Status:
    """Aggregates inherit the weakest constituent status (rule 6)."""
    if not statuses:
        raise ValueError("weakest() requires at least one status")
    return min(statuses, key=rank)


# --- E6 -- never rendered, phrased, or summarised as denial (I7, rule 4) ---

E6_TEMPLATE = "Not found in corpus version {version}. Searched: {scope}. This is not evidence of non-occurrence."

_DENIAL_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bthere (?:was|were|is|are) no\b",
        r"\bdid not occur\b",
        r"\bdidn't occur\b",
        r"\bnever happened\b",
        r"\bnever occurred\b",
        r"\bdoes not exist\b",
        r"\bdid not happen\b",
    )
]


def render_e6(*, corpus_version: str, scope: str) -> str:
    return E6_TEMPLATE.format(version=corpus_version, scope=scope)


def lint_e6_text(text: str) -> None:
    """Rejects E6 payloads phrased as denial (I7). Raises, does not warn."""
    for pattern in _DENIAL_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"E6 text contains a denial construction ({pattern.pattern!r}): {text!r}")


# --- Claim assessment --------------------------------------------------------


@dataclass(frozen=True)
class ClaimAssessment:
    claim_id: str
    claim_text: str
    status: Status
    supporting: tuple[Locator, ...]
    contradicting: tuple[Locator, ...]
    negating: tuple[Locator, ...]
    note: str
    corpus_version: str


def assess_claim(
    *,
    claim_id: str,
    claim_text: str,
    corpus_version: str,
    supporting: list[Locator] | None = None,
    contradicting: list[Locator] | None = None,
    negating: list[Locator] | None = None,
    out_of_scope: bool = False,
    search_scope: str = "",
    independence_confirmed: bool = False,
    independence_note: str = "",
) -> ClaimAssessment:
    """Pure function: evidence sets in, status out. No search, no I/O.

    Assignment rules (section 7.2), in the order applied:
      1. out_of_scope -> E8, unconditionally (rule: corpus cannot in
         principle address this).
      2. Any contradicting locator -> E4 (sources disagree). Checked
         before negating/supporting because disagreement is itself the
         finding, regardless of what else was found.
      3. No contradicting, but a negating locator -> E7 (a source
         positively asserts non-occurrence) -- never phrased as absence.
      4. No supporting/contradicting/negating locators at all -> E6,
         rendered through the fixed template and linted against denial
         constructions (I7).
      5. Supporting locators from exactly one item -> E5 (single
         witness; count is unambiguous without running independence).
      6. Supporting locators from >1 item, `independence_confirmed=True`
         -> E2 (corroborated). The caller (dhra.independence, Phase 2)
         must have actually run the descent-clustering pipeline over
         these exact supporting locators and found every pair
         INDEPENDENT before passing this flag -- assess_claim itself
         does no checking, it only records the argument (section 7.3:
         "the independence argument is attached to the claim and
         displayed with it").
      7. Supporting locators from >1 item, independence not confirmed
         -> E1 (attested). Never E2 by default (I6).
    """
    supporting = list(supporting or [])
    contradicting = list(contradicting or [])
    negating = list(negating or [])

    if out_of_scope:
        return ClaimAssessment(
            claim_id=claim_id,
            claim_text=claim_text,
            status=Status.OUT_OF_SCOPE,
            supporting=(),
            contradicting=(),
            negating=(),
            note="This corpus cannot in principle address this claim.",
            corpus_version=corpus_version,
        )

    if contradicting:
        return ClaimAssessment(
            claim_id=claim_id,
            claim_text=claim_text,
            status=Status.CONTESTED,
            supporting=tuple(supporting),
            contradicting=tuple(contradicting),
            negating=tuple(negating),
            note=f"{len(contradicting)} source(s) in the corpus disagree with this claim.",
            corpus_version=corpus_version,
        )

    if negating:
        return ClaimAssessment(
            claim_id=claim_id,
            claim_text=claim_text,
            status=Status.NEGATIVE,
            supporting=tuple(supporting),
            contradicting=(),
            negating=tuple(negating),
            note="A source in the corpus positively asserts this did not occur.",
            corpus_version=corpus_version,
        )

    if not supporting:
        note = render_e6(corpus_version=corpus_version, scope=search_scope)
        lint_e6_text(note)
        return ClaimAssessment(
            claim_id=claim_id,
            claim_text=claim_text,
            status=Status.UNSUPPORTED,
            supporting=(),
            contradicting=(),
            negating=(),
            note=note,
            corpus_version=corpus_version,
        )

    distinct_items = {loc.item_id for loc in supporting}
    if len(distinct_items) == 1:
        status = Status.SINGLE_WITNESS
        note = "One source in the corpus attests this claim; reliability unestablished."
    elif independence_confirmed:
        status = Status.CORROBORATED
        note = (
            f"Corroborated by {len(distinct_items)} source(s), checked pairwise "
            f"and found independent (no shared descent). {independence_note}".strip()
        )
    else:
        status = Status.ATTESTED
        note = (
            f"Attested by {len(distinct_items)} source(s) in the corpus. "
            "Not assigned as corroborated (E2): independence between these "
            "sources has not been checked."
        )

    return ClaimAssessment(
        claim_id=claim_id,
        claim_text=claim_text,
        status=status,
        supporting=tuple(supporting),
        contradicting=(),
        negating=(),
        note=note,
        corpus_version=corpus_version,
    )


def check_monotonicity(previous: ClaimAssessment | None, new: ClaimAssessment) -> None:
    """Status never rises without new evidence (rule 2). Raises if a rise
    is attempted without the supporting/contradicting/negating locator
    sets actually growing.

    A rise IS allowed only when the new evidence set is a strict superset
    of the old one (new locators were actually added) -- not merely
    because the same evidence was re-submitted or rephrased.
    """
    if previous is None:
        return
    if rank(new.status) <= rank(previous.status):
        return  # falling or staying is always allowed (rule 3)

    old_evidence = set(previous.supporting) | set(previous.contradicting) | set(previous.negating)
    new_evidence = set(new.supporting) | set(new.contradicting) | set(new.negating)
    if not new_evidence > old_evidence:
        raise ValueError(
            f"Monotonicity violation: claim {new.claim_id!r} status would rise "
            f"{previous.status.value} -> {new.status.value} without new evidence "
            "(re-asking or rephrasing cannot upgrade status)."
        )
