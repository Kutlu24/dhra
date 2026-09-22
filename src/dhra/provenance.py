"""Claim -> Evidence -> Source provenance chain, assembled for display.

Everything here is a read-only walk over data that already exists in the
projection (`Locator` -> `Representation` [+ parent chain] -> `Item` ->
`Acquisition.source_id`) plus `DHRARepo.resolve()` for exact excerpt
text. No new events, no new store state -- this module exists because
that walk wasn't assembled into one place anywhere yet, not because the
underlying data was missing (see `repo.resolve`, `Projection.
representation_chain`).

Used by the claim-detail evidence blocks and the evidence/provenance
graph (`web/templates/macros/{cards,graph}.html`).
"""

from __future__ import annotations

from dataclasses import dataclass

from dhra.models import Item, Locator, Representation
from dhra.repo import DHRARepo
from dhra.status import ClaimAssessment


@dataclass(frozen=True)
class ProvenanceNode:
    locator: Locator
    resolved_text: str
    rep_chain: tuple[Representation, ...]  # root representation first
    item: Item
    source_id: str


def locator_provenance(repo: DHRARepo, locator: Locator) -> ProvenanceNode:
    passage = repo.resolve(locator)
    projection = repo.projection()
    item = projection.items[locator.item_id]
    chain = tuple(reversed(projection.representation_chain(locator.rep_id)))
    return ProvenanceNode(
        locator=locator,
        resolved_text=passage.text,
        rep_chain=chain,
        item=item,
        source_id=item.acquisition.source_id,
    )


@dataclass(frozen=True)
class ClaimProvenance:
    claim_id: str
    supporting: tuple[ProvenanceNode, ...]
    contradicting: tuple[ProvenanceNode, ...]
    negating: tuple[ProvenanceNode, ...]


def claim_provenance(repo: DHRARepo, assessment: ClaimAssessment) -> ClaimProvenance:
    return ClaimProvenance(
        claim_id=assessment.claim_id,
        supporting=tuple(locator_provenance(repo, loc) for loc in assessment.supporting),
        contradicting=tuple(locator_provenance(repo, loc) for loc in assessment.contradicting),
        negating=tuple(locator_provenance(repo, loc) for loc in assessment.negating),
    )
