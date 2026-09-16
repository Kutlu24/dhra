"""Minimal ULID generator (stdlib only) -- spec uses ULIDs for item_id etc.

26-char Crockford-base32 string: 48-bit millisecond timestamp + 80 bits
of randomness. Monotonic ordering is not guaranteed within the same
millisecond; that is not required anywhere in Phase 0.
"""

from __future__ import annotations

import secrets
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    ms = time.time_ns() // 1_000_000
    ts_bytes = ms.to_bytes(6, "big")
    rand_bytes = secrets.token_bytes(10)
    raw = ts_bytes + rand_bytes  # 16 bytes = 128 bits

    value = int.from_bytes(raw, "big")
    chars = []
    for _ in range(26):
        value, rem = divmod(value, 32)
        chars.append(_CROCKFORD[rem])
    return "".join(reversed(chars))
