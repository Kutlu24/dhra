"""Request-level security: one pure-ASGI middleware plus small helpers.

Pure ASGI (not BaseHTTPMiddleware) on purpose: it must also see WebSocket
connections (the mounted /interpreter app) and it enforces body limits while
the body streams in, not after it is already in memory.

Defaults are safe for the public Render demo (nothing here locks it out);
the stricter, internal-deployment behaviour is opt-in via environment:

  DHRA_REQUIRE_AUTH=1       every page except /login needs a valid session
  DHRA_SIGNUP=closed        no self-service sign-up (use `dhra user-add`)
  DHRA_MAX_UPLOAD_MB=25     request-body cap (interpreter: 10 MB)
  DHRA_ALLOWED_ORIGINS=...  extra origins allowed to POST (comma-separated)
  DHRA_TRUST_PROXY=1        believe X-Forwarded-For/-Host/-Proto (only behind
                            a reverse proxy you control)
  DHRA_COOKIE_SECURE=1|0    force the session cookie's Secure flag (default:
                            on whenever the request arrived over https)
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from http.cookies import SimpleCookie
from typing import Any, Callable
from urllib.parse import urlsplit

from fastapi.exceptions import HTTPException

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_PUBLIC_PATHS = frozenset({"/login", "/logout", "/signup", "/robots.txt", "/privacy", "/terms"})
_PUBLIC_PREFIXES = ("/static/", "/lang/")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SecurityConfig:
    max_upload_bytes: int = 25 * 1024 * 1024
    interpreter_max_bytes: int = 10 * 1024 * 1024
    require_auth: bool = False
    signup_closed: bool = False
    allowed_origins: frozenset[str] = frozenset()
    trust_proxy: bool = False
    cookie_secure: bool | None = None  # None = decide per request

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        try:
            max_mb = float(os.environ.get("DHRA_MAX_UPLOAD_MB", "25"))
        except ValueError:
            max_mb = 25.0
        secure_raw = os.environ.get("DHRA_COOKIE_SECURE")
        origins = {o.strip().rstrip("/").lower() for o in os.environ.get("DHRA_ALLOWED_ORIGINS", "").split(",") if o.strip()}
        return cls(
            max_upload_bytes=max(1, int(max_mb * 1024 * 1024)),
            require_auth=_env_bool("DHRA_REQUIRE_AUTH"),
            signup_closed=os.environ.get("DHRA_SIGNUP", "open").strip().lower() == "closed",
            allowed_origins=frozenset(origins),
            trust_proxy=_env_bool("DHRA_TRUST_PROXY"),
            cookie_secure=None if secure_raw is None else _env_bool("DHRA_COOKIE_SECURE"),
        )


def client_ip(headers: dict[str, str], client: Any, trust_proxy: bool) -> str:
    """Peer address. X-Forwarded-For is only believed when the operator says
    a trusted proxy sets it; otherwise any client could pick its own
    rate-limit bucket."""
    if trust_proxy:
        forwarded = headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return client[0] if client else "unknown"


def is_https(headers: dict[str, str], scheme: str, trust_proxy: bool) -> bool:
    if scheme in ("https", "wss"):
        return True
    return trust_proxy and headers.get("x-forwarded-proto", "").split(",")[0].strip().lower() == "https"


class AttemptLimiter:
    """Sliding-window attempt counter, in-process (like the rest of this
    app's state: single process; with several workers each has its own)."""

    def __init__(self, max_attempts: int, window_seconds: float, clock: Callable[[], float] = time.monotonic):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        cutoff = self._clock() - self.window
        while hits and hits[0] < cutoff:
            hits.popleft()
        if not hits:
            self._hits.pop(key, None)
            return deque()
        return hits

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._prune(key)) >= self.max_attempts

    def record(self, key: str) -> None:
        with self._lock:
            self._prune(key)
            self._hits.setdefault(key, deque()).append(self._clock())
            if len(self._hits) > 10_000:  # bound memory under key-spraying
                for k in list(self._hits)[:5_000]:
                    self._hits.pop(k, None)

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def retry_after(self, key: str) -> int:
        with self._lock:
            hits = self._prune(key)
            if len(hits) < self.max_attempts:
                return 0
            return max(1, int(hits[0] + self.window - self._clock()) + 1)


def _human(n: int) -> str:
    return f"{n // (1024 * 1024)} MB" if n >= 1024 * 1024 else f"{max(1, n // 1024)} KB"


class _TooLarge(HTTPException):
    """An HTTPException on purpose: FastAPI turns any other exception raised
    while it reads the body into a generic 400, but re-raises HTTPException,
    so the client gets the accurate 413."""

    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Request body too large.")


def _has_too_large(exc: BaseException) -> bool:
    if isinstance(exc, _TooLarge):
        return True
    return any(_has_too_large(e) for e in getattr(exc, "exceptions", ()))


class SecurityMiddleware:
    def __init__(self, app: Any, config: SecurityConfig, is_authenticated: Callable[[dict[str, str]], bool] | None = None):
        self.app = app
        self.config = config
        self.is_authenticated = is_authenticated

    # -- helpers ---------------------------------------------------------

    def _origin_ok(self, headers: dict[str, str]) -> bool:
        """Browsers always send Origin on cross-origin POSTs and WebSocket
        handshakes. If one is present it must be this site (or explicitly
        allowed); requests without Origin/Referer are non-browser clients
        (curl, scripts) and are not a CSRF vector."""
        origin = headers.get("origin")
        if origin is None:
            referer = headers.get("referer")
            if not referer:
                return True
            parts = urlsplit(referer)
            origin = f"{parts.scheme}://{parts.netloc}"
        origin = origin.rstrip("/").lower()
        if origin == "null":
            return False
        if origin in self.config.allowed_origins:
            return True
        netloc = urlsplit(origin).netloc
        hosts = {headers.get("host", "").lower()}
        if self.config.trust_proxy and headers.get("x-forwarded-host"):
            hosts.add(headers["x-forwarded-host"].split(",")[0].strip().lower())
        return bool(netloc) and netloc in hosts

    @staticmethod
    def _public(path: str) -> bool:
        return path in _PUBLIC_PATHS or path.startswith(_PUBLIC_PREFIXES)

    async def _deny(self, scope: dict, send: Any, status: int, message: str, *, location: str | None = None) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 4401 if status == 401 else 1008})
            return
        headers = [(b"content-type", b"text/plain; charset=utf-8"), (b"content-length", str(len(message)).encode())]
        if location:
            headers.append((b"location", location.encode()))
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": message.encode()})

    # -- ASGI ------------------------------------------------------------

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        path = scope.get("path", "")
        is_ws = scope["type"] == "websocket"
        method = scope.get("method", "GET")

        if (is_ws or method not in _SAFE_METHODS) and not self._origin_ok(headers):
            await self._deny(scope, send, 403, "Cross-origin request refused.")
            return

        if self.config.require_auth and not self._public(path):
            if self.is_authenticated is None or not self.is_authenticated(headers):
                if not is_ws and method in ("GET", "HEAD"):
                    await self._deny(scope, send, 303, "Login required.", location="/login")
                else:
                    await self._deny(scope, send, 401, "Login required.")
                return

        if is_ws or method in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return

        limit = self.config.interpreter_max_bytes if path.startswith("/interpreter") else self.config.max_upload_bytes
        declared = headers.get("content-length", "")
        if declared.isdigit() and int(declared) > limit:
            await self._deny(scope, send, 413, f"Request body too large (limit {_human(limit)}).")
            return

        received = 0
        started = False
        exceeded = False
        sent_413 = False
        too_large = f"Request body too large (limit {_human(limit)})."

        async def counting_receive() -> dict:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    raise _TooLarge
            return message

        async def tracking_send(message: dict) -> None:
            nonlocal started, sent_413
            if exceeded:
                # Whatever the app made of the aborted read (FastAPI wraps it
                # in a generic 400), the client gets the accurate 413.
                if not sent_413:
                    sent_413 = True
                    await self._deny(scope, send, 413, too_large)
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except BaseException as exc:  # noqa: BLE001 - re-raised unless it is our own size abort
            if not _has_too_large(exc):
                raise
            if not started and not sent_413:
                await self._deny(scope, send, 413, too_large)


def user_cookie_value(headers: dict[str, str], cookie_name: str) -> str | None:
    raw = headers.get("cookie")
    if not raw:
        return None
    jar: SimpleCookie = SimpleCookie()
    try:
        jar.load(raw)
    except Exception:  # noqa: BLE001 - malformed Cookie header is just "no cookie"
        return None
    morsel = jar.get(cookie_name)
    return morsel.value if morsel else None
