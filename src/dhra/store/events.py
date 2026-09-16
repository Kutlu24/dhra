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
        "model.invoked",
        "tool.invoked",
    }
)


class EventLog:
    """Append-only writer/reader over a single events.jsonl file.

    Thread-safe for append (single-process lock); not multi-process safe --
    that is a Phase 3 concern (concurrent agent runs), out of scope here.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        self._lock = threading.Lock()

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
        if event_type not in EVENT_TYPES:
            raise ValueError(f"Unknown event type {event_type!r}; add it to EVENT_TYPES deliberately.")
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
