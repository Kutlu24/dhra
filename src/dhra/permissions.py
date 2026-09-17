"""Tool layer permissions -- DHRA_BUILD_SPEC.md section 9.1.

Approvals are event-sourced rather than tied to a live interactive
prompt: an `ASK`/`ACT` tool call checks the event log for a matching,
unconsumed `approval.granted` event before proceeding, and consumes it
(one approval = one use) so the same specifics can never be silently
reused for a different action. This is deliberately simpler than MCP's
native mid-call elicitation protocol (`mcp.server.mcpserver`'s
`InputRequiredResult`) -- see OPEN_QUESTIONS.md -- but satisfies what
the spec actually requires: approvals scoped to the action (never the
session), logged, and the approval rate trackable per class.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class PermissionClass(StrEnum):
    READ = "read"  # search, retrieve, analyse, compare -- no checkpoint, fully logged
    PREPARE = "prepare"  # draft, stage, propose -- nothing leaves/mutates without approval
    ASK = "ask"  # per-action approval, specifics shown
    ACT = "act"  # only under explicit, scoped, revocable, time-bounded standing authorisation


@dataclass(frozen=True)
class ActionSpec:
    """What the researcher is actually being asked to approve -- section
    9.1: not "access external archive?" but exact numbers."""

    tool: str
    summary: str  # e.g. "Request 340 items from Archive A, ~2.1 GB, under licence L which forbids redistribution."
    details: dict


class ApprovalRequired(Exception):
    def __init__(self, spec: ActionSpec):
        self.spec = spec
        super().__init__(spec.summary)


def check_permission(repo, permission: PermissionClass, spec: ActionSpec, *, actor: str) -> None:
    """Call before executing an ASK/ACT-class tool body. Raises
    ApprovalRequired if there is no unconsumed matching approval;
    consumes (via `approval.consumed`) the approval it used, so it
    cannot be replayed for a different call."""
    if permission in (PermissionClass.READ, PermissionClass.PREPARE):
        return  # no checkpoint (READ), or nothing leaves/mutates yet (PREPARE)

    projection = repo.projection()
    for event in projection.pending_approvals:
        if event["tool"] == spec.tool and event["summary"] == spec.summary:
            repo.events.append("approval.consumed", tool=spec.tool, summary=spec.summary, actor=actor)
            return
    raise ApprovalRequired(spec)


def approval_rate(repo, permission: PermissionClass | None = None) -> dict:
    """Track approval rate per class (section 9.1): "if a class is
    approved without exception over time, that is evidence it is
    misclassified and should become a bounded standing authorisation"."""
    projection = repo.projection()
    granted = len(projection.approval_log_granted)
    denied = len(projection.approval_log_denied)
    total = granted + denied
    return {
        "granted": granted,
        "denied": denied,
        "total": total,
        "approval_rate": (granted / total) if total else None,
    }
