"""Signed session cookies for the accounts system.

Deliberately separate from `dhra.web.app`'s existing `LANGUAGE_COOKIE`
mechanism: that cookie carries a raw, unsigned 3-value language code,
safe only because `resolve_language()` allowlists against a tiny fixed
set. A session cookie carries a user id -- an unsigned value there would
let anyone set `dhra_session=<any-user-id>` and be logged in as them.
`itsdangerous` (the standard tool for exactly this in the
Flask/FastAPI/Starlette ecosystem -- Starlette's own SessionMiddleware
uses it) signs the cookie so tampering is detectable, not just discouraged.
"""

from __future__ import annotations

import secrets

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE = "dhra_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def make_serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt="dhra-session")


def session_cookie_value(serializer: URLSafeTimedSerializer, user_id: str) -> str:
    # `sid` is a server-issued nonce inside the signed payload: logout
    # revokes by (user_id, sid), never by the cookie's raw text, which can
    # be written several ways (non-canonical base64) that all verify.
    return serializer.dumps({"user_id": user_id, "sid": secrets.token_urlsafe(9)})


def user_id_from_cookie(serializer: URLSafeTimedSerializer, cookie_value: str | None) -> str | None:
    if not cookie_value:
        return None
    try:
        data = serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    user_id = data.get("user_id")
    return user_id if isinstance(user_id, str) else None


def session_from_cookie(serializer: URLSafeTimedSerializer, cookie_value: str | None) -> tuple[str, str] | None:
    """(user_id, session id) from a valid cookie. Cookies issued before
    `sid` existed fall back to their signed issue timestamp as the id."""
    if not cookie_value:
        return None
    try:
        data, issued = serializer.loads(cookie_value, max_age=SESSION_MAX_AGE, return_timestamp=True)
    except (BadSignature, SignatureExpired):
        return None
    user_id = data.get("user_id") if isinstance(data, dict) else None
    if not isinstance(user_id, str):
        return None
    sid = data.get("sid")
    return user_id, sid if isinstance(sid, str) else f"ts{int(issued.timestamp())}"
