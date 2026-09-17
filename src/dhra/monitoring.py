"""Literature monitoring -- DHRA_BUILD_SPEC.md section 6 (Phase 4).

A monitor is a saved query, re-run on demand against the current corpus
version, reporting which matches are new since the last check. No
scheduler/daemon here (local-first, section 16: "assume the absence" of
institutional infrastructure) -- `check_monitor`/`check_monitors` are
called whenever the researcher (or an orchestrator) decides to, which is
also more honest than pretending a background process is watching
continuously when none is running.
"""

from __future__ import annotations

from dataclasses import dataclass

from dhra.evidence import search
from dhra.repo import DHRARepo
from dhra.ulid import new_ulid


@dataclass(frozen=True)
class Monitor:
    monitor_id: str
    name: str
    query: str
    variants: tuple[str, ...]
    actor: str
    created_ts: str


@dataclass(frozen=True)
class MonitorCheckResult:
    monitor_id: str
    checked_at: str
    matched_item_ids: tuple[str, ...]
    new_item_ids: tuple[str, ...]


def save_monitor(repo: DHRARepo, *, name: str, query: str, variants: list[str] | None = None, actor: str, task: str | None = None) -> str:
    monitor_id = new_ulid()
    repo.events.append(
        "monitor.saved",
        monitor_id=monitor_id,
        name=name,
        query=query,
        variants=variants or [],
        actor=actor,
        task=task,
    )
    return monitor_id


def list_monitors(repo: DHRARepo) -> list[Monitor]:
    monitors: dict[str, Monitor] = {}
    for event in repo.events.read_all():
        if event["type"] == "monitor.saved":
            monitors[event["monitor_id"]] = Monitor(
                monitor_id=event["monitor_id"],
                name=event["name"],
                query=event["query"],
                variants=tuple(event.get("variants") or ()),
                actor=event["actor"],
                created_ts=event["ts"],
            )
    return sorted(monitors.values(), key=lambda m: m.created_ts)


def _previously_seen_item_ids(repo: DHRARepo, monitor_id: str) -> set[str]:
    seen: set[str] = set()
    for event in repo.events.read_all():
        if event["type"] == "monitor.checked" and event["monitor_id"] == monitor_id:
            seen.update(event["matched_item_ids"])
    return seen


def check_monitor(repo: DHRARepo, monitor_id: str, *, task: str | None = None) -> MonitorCheckResult:
    monitor = next((m for m in list_monitors(repo) if m.monitor_id == monitor_id), None)
    if monitor is None:
        raise ValueError(f"no such monitor: {monitor_id}")

    previously_seen = _previously_seen_item_ids(repo, monitor_id)
    response = search(repo, monitor.query, variants=list(monitor.variants), task=task)
    matched_item_ids = tuple(sorted({p.locator.item_id for p in response.evidence}))
    new_item_ids = tuple(sorted(set(matched_item_ids) - previously_seen))

    event = repo.events.append(
        "monitor.checked",
        monitor_id=monitor_id,
        matched_item_ids=list(matched_item_ids),
        new_item_ids=list(new_item_ids),
        task=task,
    )
    return MonitorCheckResult(
        monitor_id=monitor_id,
        checked_at=event["ts"],
        matched_item_ids=matched_item_ids,
        new_item_ids=new_item_ids,
    )


def check_monitors(repo: DHRARepo, *, task: str | None = None) -> list[MonitorCheckResult]:
    return [check_monitor(repo, m.monitor_id, task=task) for m in list_monitors(repo)]
