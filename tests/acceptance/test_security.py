"""Security fixes: upload limits, CSRF/Origin, auth gate, login throttling,
actor binding, redirect safety, cookie flags, hidden API docs, interpreter
limits."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dhra.repo import DHRARepo
from dhra.web.app import build_app
from dhra.web.security import AttemptLimiter, SecurityConfig

PW = "correct-horse-1"


def make(tmp_path, *, accounts=True, **cfg):
    kwargs = {"accounts_dir": tmp_path / "acc"} if accounts else {}
    return build_app(DHRARepo(tmp_path / "store"), session_secret="s" * 32, security=SecurityConfig(**cfg), **kwargs)


def signup(client, name="alice"):
    return client.post("/signup", data={"username": name, "password": PW, "password_confirm": PW}, follow_redirects=False)


# -- 1. upload size ---------------------------------------------------------

def test_oversized_upload_rejected_by_declared_length(tmp_path):
    c = TestClient(make(tmp_path, accounts=False, max_upload_bytes=1024))
    r = c.post("/ingest", data={"source_id": "s"}, files={"file": ("a.txt", b"x" * 5000)})
    assert r.status_code == 413


def test_oversized_chunked_upload_rejected_while_streaming(tmp_path):
    c = TestClient(make(tmp_path, accounts=False, max_upload_bytes=1024))

    def body():
        for _ in range(20):
            yield b"x" * 512

    r = c.post("/ingest", content=body(), headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 413


def test_small_upload_still_works(tmp_path):
    c = TestClient(make(tmp_path, accounts=False, max_upload_bytes=1024 * 1024))
    r = c.post("/ingest", data={"source_id": "s", "text": "hello"}, follow_redirects=False)
    assert r.status_code == 303


# -- 3. CSRF / Origin -------------------------------------------------------

def test_cross_origin_post_refused_same_origin_and_no_origin_allowed(tmp_path):
    c = TestClient(make(tmp_path, accounts=False))
    data = {"source_id": "s", "text": "t"}
    assert c.post("/ingest", data=data, headers={"Origin": "https://evil.example"}, follow_redirects=False).status_code == 403
    assert c.post("/ingest", data=data, headers={"Origin": "null"}, follow_redirects=False).status_code == 403
    assert c.post("/ingest", data=data, headers={"Referer": "https://evil.example/x"}, follow_redirects=False).status_code == 403
    assert c.post("/ingest", data=data, headers={"Origin": "http://testserver"}, follow_redirects=False).status_code == 303
    assert c.post("/ingest", data=data, follow_redirects=False).status_code == 303


def test_allowed_origin_override(tmp_path):
    c = TestClient(make(tmp_path, accounts=False, allowed_origins=frozenset({"https://dhra.example"})))
    r = c.post("/ingest", data={"source_id": "s", "text": "t"}, headers={"Origin": "https://dhra.example"}, follow_redirects=False)
    assert r.status_code == 303


# -- 2. auth gate -----------------------------------------------------------

def test_require_auth_gates_pages_posts_and_interpreter(tmp_path):
    c = TestClient(make(tmp_path, require_auth=True))
    r = c.get("/claims", follow_redirects=False)
    assert (r.status_code, r.headers["location"]) == (303, "/login")
    assert c.post("/ingest", data={"source_id": "s", "text": "t"}).status_code == 401
    assert c.post("/interpreter/rooms").status_code == 401
    assert c.get("/login").status_code == 200
    assert c.get("/static/css/dhra.css").status_code == 200
    with pytest.raises(Exception):  # refused before accept
        with c.websocket_connect("/interpreter/ws/abcdef12"):
            pass
    assert signup(c).status_code == 303
    assert c.get("/claims", follow_redirects=False).status_code == 200
    assert c.post("/interpreter/rooms").status_code == 200


def test_require_auth_without_accounts_or_secret_is_a_config_error(tmp_path):
    with pytest.raises(ValueError):
        build_app(DHRARepo(tmp_path / "s1"), security=SecurityConfig(require_auth=True))
    with pytest.raises(ValueError):
        build_app(DHRARepo(tmp_path / "s2"), accounts_dir=tmp_path / "a", security=SecurityConfig(require_auth=True))


def test_closed_signup(tmp_path):
    c = TestClient(make(tmp_path, signup_closed=True))
    assert c.get("/signup").status_code == 403
    assert signup(c).status_code == 403


# -- 5. login throttle ------------------------------------------------------

def test_login_lockout_after_repeated_failures(tmp_path):
    c = TestClient(make(tmp_path))
    signup(c)
    c.post("/logout")
    c.cookies.clear()
    codes = [c.post("/login", data={"username": "alice", "password": f"bad{i}"}).status_code for i in range(7)]
    assert codes[:5] == [200] * 5 and codes[5:] == [429, 429]
    # even the right password is refused while locked
    r = c.post("/login", data={"username": "alice", "password": PW})
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_signup_attempts_are_throttled(tmp_path):
    c = TestClient(make(tmp_path))
    codes = [c.post("/signup", data={"username": f"u{i}", "password": PW, "password_confirm": "x"}).status_code for i in range(7)]
    assert 429 in codes


def test_attempt_limiter_window():
    now = [0.0]
    lim = AttemptLimiter(2, 10, clock=lambda: now[0])
    lim.record("k"); lim.record("k")
    assert lim.blocked("k") and lim.retry_after("k") >= 1
    now[0] = 11
    assert not lim.blocked("k")


# -- 7. actor binding -------------------------------------------------------

def test_actor_comes_from_session_not_form(tmp_path):
    repo = DHRARepo(tmp_path / "store")
    app = build_app(repo, accounts_dir=tmp_path / "acc", session_secret="s" * 32, security=SecurityConfig())
    c = TestClient(app)
    signup(c, "alice")
    r = c.post("/ingest", data={"source_id": "s", "text": "hello"}, follow_redirects=False)
    item_id = r.headers["location"].rsplit("/", 1)[1]
    c.post("/annotate", data={"target_type": "item", "target_id": item_id, "text": "note", "actor": "mallory"})
    store = tmp_path / "acc" / "users"
    log = "".join(p.read_text() for p in store.rglob("events.jsonl"))
    assert "alice" in log and "mallory" not in log


# -- 8. open redirect -------------------------------------------------------

def test_lang_redirect_stays_on_site(tmp_path):
    c = TestClient(make(tmp_path, accounts=False))
    r = c.get("/lang/de", headers={"Referer": "https://evil.example/x"}, follow_redirects=False)
    assert r.headers["location"] == "/"
    r = c.get("/lang/de", headers={"Referer": "http://testserver/claims?x=1"}, follow_redirects=False)
    assert r.headers["location"] == "/claims?x=1"


# -- 9. cookies / logout ----------------------------------------------------

def test_cookie_secure_flag_and_logout_revokes(tmp_path):
    c = TestClient(make(tmp_path, trust_proxy=True))
    r = signup(c)
    assert "secure" not in r.headers["set-cookie"].lower()
    c.cookies.clear()
    r = c.post("/signup", data={"username": "bob", "password": PW, "password_confirm": PW},
               headers={"X-Forwarded-Proto": "https"}, follow_redirects=False)
    assert "secure" in r.headers["set-cookie"].lower()
    stolen = c.cookies.get("dhra_session")
    jar = {"Cookie": f"dhra_session={stolen}"}  # Secure cookie is not resent over plain http by the test client
    assert "signed in as bob" in c.get("/", headers=jar).text.lower().replace("\n", " ").replace("  ", " ") or "bob" in c.get("/", headers=jar).text
    c.post("/logout", headers=jar)
    c.cookies.clear()
    assert "bob" not in c.get("/", headers=jar).text


def test_forced_secure_cookie(tmp_path):
    c = TestClient(make(tmp_path, cookie_secure=True))
    assert "secure" in signup(c).headers["set-cookie"].lower()


# -- 10. docs hidden --------------------------------------------------------

@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/interpreter/docs", "/interpreter/openapi.json"])
def test_api_docs_not_exposed(tmp_path, path):
    assert TestClient(make(tmp_path, accounts=False)).get(path).status_code == 404


# -- 4. interpreter limits --------------------------------------------------

def test_interpreter_room_ids_and_caps(tmp_path):
    from dhra.interpreter import rooms

    c = TestClient(make(tmp_path, accounts=False))
    room_id = c.post("/interpreter/rooms").json()["room_id"]
    assert len(room_id) == 10 and rooms.valid_room_id(room_id)
    assert c.get(f"/interpreter/rooms/{room_id}").status_code == 200
    assert c.get("/interpreter/rooms/NOT-A-ROOM").status_code == 404
    assert c.post("/interpreter/tts", data={"text": "x" * 2001, "language": "en"}).status_code == 413
    old = rooms.MAX_ROOMS
    try:
        rooms.MAX_ROOMS = len(rooms.registry._rooms)
        assert c.post("/interpreter/rooms").status_code == 503
    finally:
        rooms.MAX_ROOMS = old


def test_interpreter_rate_limit(tmp_path):
    from dhra.interpreter.api import app as iapp

    c = TestClient(make(tmp_path, accounts=False))
    iapp._room_limiter._hits.clear()
    codes = [c.post("/interpreter/rooms").status_code for _ in range(25)]
    assert codes.count(429) >= 1
    iapp._room_limiter._hits.clear()


def test_interpreter_websocket_cross_origin_refused(tmp_path):
    c = TestClient(make(tmp_path, accounts=False))
    with pytest.raises(Exception):
        with c.websocket_connect("/interpreter/ws/abcdef12", headers={"Origin": "https://evil.example"}):
            pass
