"""Rate limiting -- DHRA_BUILD_SPEC.md section 9.2: "Rate limits are hard
constraints, not preferences." The limiter blocks (raises), it does not
warn and proceed anyway (section 13.3, `test_rate_limit_hard`); no
retry-on-schedule, only explicit backoff after a real failure (section
9.2: "back off on error rather than retrying").
"""

from __future__ import annotations

import threading
import time
from collections import deque

from dhra.source_registry import SourceEntry


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    """One sliding-window limiter per source id. Thread-safe for the
    single-process case (see dhra.store.events's own scope note on
    concurrency)."""

    def __init__(self) -> None:
        self._windows: dict[str, deque] = {}
        self._lock = threading.Lock()

    def check(self, source: SourceEntry, *, now: float | None = None) -> None:
        """Raises RateLimitExceeded (blocks) if calling now would exceed
        `source.rate_limit`. Does not itself sleep/retry -- the caller
        decides whether to wait or refuse."""
        now = now if now is not None else time.monotonic()
        with self._lock:
            window = self._windows.setdefault(source.id, deque())
            cutoff = now - source.rate_limit.per_seconds
            while window and window[0] < cutoff:
                window.popleft()
            if len(window) >= source.rate_limit.requests:
                raise RateLimitExceeded(
                    f"{source.id}: {source.rate_limit.requests} requests per "
                    f"{source.rate_limit.per_seconds}s exceeded"
                )
            window.append(now)

    def wait_time(self, source: SourceEntry, *, now: float | None = None) -> float:
        """Seconds until the next request would be allowed (0 if allowed now)."""
        now = now if now is not None else time.monotonic()
        with self._lock:
            window = self._windows.get(source.id)
            if not window or len(window) < source.rate_limit.requests:
                return 0.0
            oldest = window[0]
            return max(0.0, (oldest + source.rate_limit.per_seconds) - now)
