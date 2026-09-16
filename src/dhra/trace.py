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
