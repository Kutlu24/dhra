"""Append-only event log -- DHRA_BUILD_SPEC.md section 5.1.

events.jsonl is the source of truth. Every state change is an event; no
state change happens any other way. derived.db and index/ are
projections and must be fully rebuildable by replaying this file
(see dhra.store.projection.replay).
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVENT_TYPES = frozenset(
    {
        "item.acquired",
        "representation.created",
        "assertion.added",
        "assertion.preference_set",
        "item.excluded",
        "item.restored",
        "claim.assessed",
        "access.failed",
        "approval.granted",
        "approval.denied",
        "approval.consumed",
        "draft.created",
        "draft.approved",
        "draft.rejected",
        "annotation.added",
        "annotation.resolved",
        "monitor.saved",
        "monitor.checked",
        "literature_watch_query.added",
        "literature_watch_query.removed",
        "literature_candidate.found",
        "literature_candidate.dismissed",
        "literature_candidate.restored",
        "model.invoked",
        "tool.invoked",
    }
)


class EventLog:
    """Append-only writer/reader over a single events.jsonl file.

    Thread-safe for append (single-process lock); not multi-process safe --
    that is a Phase 3 concern (concurrent agent runs), out of scope here.
    """

    def __init__(self, path: str | Path, *, allowed_types: frozenset[str] | None = None):
        """`allowed_types` defaults to the corpus vocabulary (`EVENT_TYPES`
        above) -- every existing caller (the corpus `events.jsonl`) keeps
        that validation unchanged. A caller managing a *different*
        append-only log (e.g. `dhra.accounts`'s `accounts.jsonl`, a
        separate concern with its own small vocabulary) passes its own
        set instead of overloading the corpus one with unrelated types."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = threading.Lock()
        self._allowed_types = allowed_types if allowed_types is not None else EVENT_TYPES

    def _next_seq(self) -> int:
        last = 0
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                last = json.loads(line)["seq"]
        return last + 1

    def append(self, event_type: str, **fields: Any) -> dict:
        if event_type not in self._allowed_types:
            raise ValueError(f"Unknown event type {event_type!r}; add it to the log's allowed-types set deliberately.")
        with self._lock:
            seq = self._next_seq()
            event = {
                "seq": seq,
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                **fields,
            }
            line = json.dumps(event, ensure_ascii=False, sort_keys=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            return event

    def read_all(self) -> Iterator[dict]:
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def read_up_to(self, seq: int) -> Iterator[dict]:
        for event in self.read_all():
            if event["seq"] > seq:
                return
            yield event

    def max_seq(self) -> int:
        last = 0
        for event in self.read_all():
            last = event["seq"]
        return last
