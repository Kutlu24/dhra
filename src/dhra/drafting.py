"""Drafting under approval -- DHRA_BUILD_SPEC.md section 6 (Phase 4) and
section 10 ("The model may... draft correspondence and prose for
approval"). `PermissionClass.PREPARE`: "draft, stage, propose -- nothing
leaves or mutates without approval" (section 9.1).

There is no send/submit/publish path here at all, on purpose: section 15
forbids "automatic sending, submitting or publishing of anything" as an
anti-requirement, full stop -- not "without approval", not ever. A
draft's terminal states are APPROVED (the researcher may now send it
themselves, elsewhere) or REJECTED. Drafts are narrative, not evidence
(section 10.1): ephemeral, no reproducibility guarantee (section 10.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dhra.repo import DHRARepo
from dhra.ulid import new_ulid


class DraftStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Draft:
    draft_id: str
    kind: str  # "correspondence" | "prose" | ...
    text: str
    status: DraftStatus
    created_by: str
    ts: str


def create_draft(repo: DHRARepo, *, kind: str, text: str, actor: str, task: str | None = None) -> str:
    draft_id = new_ulid()
    repo.events.append("draft.created", draft_id=draft_id, kind=kind, text=text, actor=actor, task=task)
    return draft_id


def approve_draft(repo: DHRARepo, *, draft_id: str, actor: str, task: str | None = None) -> None:
    repo.events.append("draft.approved", draft_id=draft_id, actor=actor, task=task)


def reject_draft(repo: DHRARepo, *, draft_id: str, reason: str, actor: str, task: str | None = None) -> None:
    repo.events.append("draft.rejected", draft_id=draft_id, reason=reason, actor=actor, task=task)


def get_draft(repo: DHRARepo, draft_id: str) -> Draft | None:
    latest_create = None
    status = DraftStatus.PENDING
    for event in repo.events.read_all():
        if event["type"] == "draft.created" and event["draft_id"] == draft_id:
            latest_create = event
        elif event["type"] == "draft.approved" and event["draft_id"] == draft_id:
            status = DraftStatus.APPROVED
        elif event["type"] == "draft.rejected" and event["draft_id"] == draft_id:
            status = DraftStatus.REJECTED
    if latest_create is None:
        return None
    return Draft(
        draft_id=draft_id,
        kind=latest_create["kind"],
        text=latest_create["text"],
        status=status,
        created_by=latest_create["actor"],
        ts=latest_create["ts"],
    )
