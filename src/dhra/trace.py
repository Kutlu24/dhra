"""Three-level activity trace -- DHRA_BUILD_SPEC.md section 11.3.

Level 1 (summary) reassures without informing. Level 3 (raw) informs
without being read. Level 2 (decisions) is what a researcher can actually
audit in the time available -- every discretionary judgement, with its
grounds, in one place.

All three are pure views over the event log filtered by `task`; nothing
here is stored separately from events.jsonl.
"""

from __future__ import annotations

from dataclasses import dataclass

from dhra.store.events import EventLog

DISCRETIONARY_TYPES = frozenset(
    {
        "item.excluded",
        "item.restored",
        "assertion.preference_set",
        "claim.assessed",
        "approval.granted",
        "approval.denied",
        "draft.approved",
        "draft.rejected",
        "annotation.resolved",
    }
)


@dataclass(frozen=True)
class TraceSummary:
    task: str | None
    event_count: int
    counts_by_type: tuple[tuple[str, int], ...]


def _events_for_task(event_log: EventLog, task: str | None) -> list[dict]:
    events = list(event_log.read_all())
    if task is None:
        return events
    return [e for e in events if e.get("task") == task]


def trace_summary(event_log: EventLog, task: str | None = None) -> TraceSummary:
    events = _events_for_task(event_log, task)
    counts: dict[str, int] = {}
    for e in events:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
    return TraceSummary(
        task=task,
        event_count=len(events),
        counts_by_type=tuple(sorted(counts.items())),
    )


def trace_decisions(event_log: EventLog, task: str | None = None) -> list[dict]:
    """Every discretionary judgement for `task`, in order, with its grounds."""
    events = _events_for_task(event_log, task)
    return [e for e in events if e["type"] in DISCRETIONARY_TYPES]


def trace_raw(event_log: EventLog, task: str | None = None) -> list[dict]:
    """Full unfiltered event dump for `task` -- tool calls, params, model versions."""
    return _events_for_task(event_log, task)


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    ts: str
    type: str
    text: str  # human-readable one-liner, e.g. "Claim status changed -- E1 -> E4"


def audit_narrative(event_log: EventLog, task: str | None = None) -> list[AuditEntry]:
    """The "Research Audit Trail" view: every discretionary event
    (`DISCRETIONARY_TYPES`, already fully logged -- see `dhra.repo`'s
    `log_model_invocation`/`log_tool_invocation`, wired into every real
    caller) turned into one human-readable line, in order. Pure
    formatting over data that's already captured; no new events."""
    events = [
        e
        for e in _events_for_task(event_log, task)
        if e["type"] in DISCRETIONARY_TYPES
        or (e["type"] == "tool.invoked" and e.get("tool") == "search_evidence")
        or e["type"] == "model.invoked"
    ]
    last_status: dict[str, str] = {}
    entries: list[AuditEntry] = []
    for e in events:
        etype = e["type"]
        if etype == "tool.invoked":
            query = (e.get("parameters") or {}).get("query", "")
            text = f"Evidence searched -- {query!r}" if query else "Evidence searched"
        elif etype == "model.invoked":
            text = f"AI assistance used -- {e.get('purpose', '')}"
        elif etype == "claim.assessed":
            claim_id = e["claim_id"]
            new_status = e["status"]
            prev = last_status.get(claim_id)
            if prev is None:
                text = f"Claim created -- {e.get('claim_text', claim_id)} ({new_status})"
            elif prev != new_status:
                text = f"Claim status changed -- {e.get('claim_text', claim_id)}: {prev} -> {new_status}"
            else:
                text = f"Claim reassessed -- {e.get('claim_text', claim_id)} (status unchanged: {new_status})"
            last_status[claim_id] = new_status
        elif etype == "item.excluded":
            text = f"Source excluded -- {e.get('item_id')} ({e.get('reason')})"
        elif etype == "item.restored":
            text = f"Source restored -- {e.get('item_id')}"
        elif etype == "approval.granted":
            text = f"Approved -- {e.get('summary', e.get('tool'))}"
        elif etype == "approval.denied":
            text = f"Denied -- {e.get('summary', e.get('tool'))}"
        elif etype == "draft.approved":
            text = f"Draft approved -- {e.get('kind', '')}"
        elif etype == "draft.rejected":
            text = f"Draft rejected -- {e.get('kind', '')}"
        elif etype == "annotation.resolved":
            text = f"Annotation resolved -- {e.get('target_id', '')}"
        else:
            text = etype
        entries.append(AuditEntry(seq=e["seq"], ts=e["ts"], type=etype, text=text))
    return entries
