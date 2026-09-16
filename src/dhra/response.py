"""Two-channel response contract -- DHRA_BUILD_SPEC.md section 10.1.

`evidence` is structured, validated, every item locator-bound.
`narrative` is generated prose: ephemeral, excluded from reproducibility
guarantees (section 10.2), and the contract refuses to carry it without
evidence (I10). `Passage` (section 8.1, dhra.models) doubles as the
EvidenceItem shape here -- both are "text + locator + score + rationale",
and the spec never asks for a second, near-identical type.
"""

from __future__ import annotations

from dataclasses import dataclass

from dhra.models import Passage
from dhra.repo import DHRARepo
from dhra.trace import TraceSummary


class VerbatimCheckError(ValueError):
    pass


class NarrativeWithoutEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class Response:
    evidence: tuple[Passage, ...]
    narrative: str | None
    trace: TraceSummary
    corpus_version: str
    absence_note: str | None = None  # section 8.3 quality-qualified absence; deterministic, not model prose


def verify_verbatim(repo: DHRARepo, passage: Passage) -> None:
    """The quoted text must be found at exactly [start:end] of rep.text.
    Mismatch raises; it does not warn (section 10.1)."""
    resolved = repo.resolve(passage.locator)
    if resolved.text != passage.text:
        raise VerbatimCheckError(
            f"Verbatim check failed for locator {passage.locator}: "
            f"passage text {passage.text!r} != stored [{passage.locator.start}:{passage.locator.end}] "
            f"{resolved.text!r}"
        )


def build_response(
    *,
    repo: DHRARepo,
    evidence: list[Passage],
    trace: TraceSummary,
    corpus_version: str,
    narrative: str | None = None,
    absence_note: str | None = None,
) -> Response:
    if narrative is not None and not evidence:
        raise NarrativeWithoutEvidenceError("narrative is rejected when evidence is empty (I10)")
    if absence_note is not None and evidence:
        raise ValueError("absence_note is only meaningful when evidence is empty")
    for passage in evidence:
        verify_verbatim(repo, passage)
    return Response(
        evidence=tuple(evidence),
        narrative=narrative,
        trace=trace,
        corpus_version=corpus_version,
        absence_note=absence_note,
    )
