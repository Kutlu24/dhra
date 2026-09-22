"""Accounts and private workspaces -- see OPEN_QUESTIONS.md #19/#21 (the
problem this closes) and `dhra.accounts`/`dhra.web.session` (how).

Every test here uses TWO SEPARATE `TestClient(app)` instances per
distinct actor (guest / alice / bob) -- `TestClient`, like a real
browser, persists `Set-Cookie` responses on its own cookie jar, so
reusing one client across a signup call and a "guest" check would
silently turn the "guest" into the signed-up user. That is a test-harness
pitfall, not an app behaviour, and the isolation this test suite checks
would look violated) if a test accidentally shared a client this way.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dhra.repo import DHRARepo
from dhra.web.app import build_app


@pytest.fixture
def shared_repo(tmp_path):
    repo = DHRARepo(tmp_path / "shared_store")
    repo.ingest_text("shared demo content visible to everyone", source_id="demo")
    return repo


@pytest.fixture
def app(tmp_path, shared_repo):
    return build_app(shared_repo, accounts_dir=tmp_path / "accounts", session_secret="test-secret")


@pytest.fixture
def app_with_demo_banner(tmp_path, shared_repo):
    return build_app(
        shared_repo, accounts_dir=tmp_path / "accounts", session_secret="test-secret", demo_banner="Demo -- ephemeral storage."
    )


def _signup(app, username: str, password: str) -> TestClient:
    """Signs up a fresh actor on their own TestClient and leaves them
    logged in (the session cookie signup sets is already on this
    client's own jar -- no separate login call needed)."""
    client = TestClient(app)
    resp = client.post("/signup", data={"username": username, "password": password, "password_confirm": password}, follow_redirects=False)
    assert resp.status_code == 303, resp.text
    return client


def test_guest_without_accounts_configured_is_unaffected(tmp_path, shared_repo):
    """accounts_dir=None (the default) -- the existing single-tenant test
    suite's whole premise -- must keep behaving exactly as before
    accounts existed. This is the compatibility guarantee the plan is
    built on, checked directly."""
    app = build_app(shared_repo)  # no accounts_dir
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "accounts_enabled" not in resp.text  # no auth UI leaks into single-tenant mode
    resp = client.get("/signup")
    assert resp.status_code == 404  # accounts routes don't exist when accounts aren't configured


def test_guest_sees_shared_demo_corpus(app):
    client = TestClient(app)
    resp = client.get("/evidence?q=shared")
    assert "Evidence (1)" in resp.text
    resp = client.get("/")
    assert "Guest -- shared demo" in resp.text


def test_signup_creates_isolated_private_workspace(app):
    alice = _signup(app, "alice", "correcthorsebattery")
    alice.post(
        "/ingest",
        data={"source_id": "alice_source", "access_basis": "public_domain", "licence_id": "", "original_reference": "", "text": "zzzalicesecretzzz research text"},
    )
    resp = alice.get("/evidence?q=zzzalicesecretzzz")
    assert "Evidence (1)" in resp.text

    guest = TestClient(app)
    resp = guest.get("/evidence?q=zzzalicesecretzzz")
    assert "Evidence (1)" not in resp.text  # a guest (shared demo corpus) never sees a private account's data


def test_two_accounts_do_not_see_each_others_data(app):
    alice = _signup(app, "alice", "correcthorsebattery")
    alice.post(
        "/ingest",
        data={"source_id": "alice_source", "access_basis": "public_domain", "licence_id": "", "original_reference": "", "text": "zzzalicesecretzzz"},
    )

    bob = _signup(app, "bob", "anotherpassword123")
    bob.post(
        "/ingest",
        data={"source_id": "bob_source", "access_basis": "public_domain", "licence_id": "", "original_reference": "", "text": "zzzbobsecretzzz"},
    )

    assert "Evidence (1)" in bob.get("/evidence?q=zzzbobsecretzzz").text
    assert "Evidence (1)" not in bob.get("/evidence?q=zzzalicesecretzzz").text
    assert "Evidence (1)" in alice.get("/evidence?q=zzzalicesecretzzz").text
    assert "Evidence (1)" not in alice.get("/evidence?q=zzzbobsecretzzz").text


def test_duplicate_username_rejected(app):
    _signup(app, "alice", "correcthorsebattery")
    dup = TestClient(app)
    resp = dup.post("/signup", data={"username": "alice", "password": "differentpassword", "password_confirm": "differentpassword"})
    assert "already taken" in resp.text


def test_short_password_rejected(app):
    client = TestClient(app)
    resp = client.post("/signup", data={"username": "newbie", "password": "short", "password_confirm": "short"})
    assert "at least 8 characters" in resp.text


def test_mismatched_confirmation_rejected(app):
    client = TestClient(app)
    resp = client.post("/signup", data={"username": "newbie", "password": "longenoughpass", "password_confirm": "different"})
    assert "match" in resp.text


def test_wrong_password_rejected(app):
    _signup(app, "alice", "correcthorsebattery")
    login_client = TestClient(app)
    resp = login_client.post("/login", data={"username": "alice", "password": "wrongpassword"})
    assert "Incorrect username or password" in resp.text
    assert "dhra_session" not in resp.cookies


def test_correct_login_sets_session_and_reaches_private_workspace(app):
    alice = _signup(app, "alice", "correcthorsebattery")
    alice.post(
        "/ingest",
        data={"source_id": "alice_source", "access_basis": "public_domain", "licence_id": "", "original_reference": "", "text": "zzzalicesecretzzz"},
    )

    login_client = TestClient(app)
    resp = login_client.post("/login", data={"username": "alice", "password": "correcthorsebattery"}, follow_redirects=False)
    assert resp.status_code == 303
    login_client.cookies.set("dhra_session", resp.cookies["dhra_session"])
    assert "Evidence (1)" in login_client.get("/evidence?q=zzzalicesecretzzz").text


def test_logout_clears_session_cookie(app):
    alice = _signup(app, "alice", "correcthorsebattery")
    resp = alice.post("/logout", follow_redirects=False)
    assert resp.status_code == 303
    # the Set-Cookie header on the response must clear/expire the cookie
    set_cookie = resp.headers.get("set-cookie", "")
    assert "dhra_session=" in set_cookie
    assert ("Max-Age=0" in set_cookie) or ("expires=" in set_cookie.lower())


def test_sidebar_reflects_signed_in_state(app):
    alice = _signup(app, "alice", "correcthorsebattery")
    resp = alice.get("/")
    assert "Signed in as alice" in resp.text
    assert "Log out" in resp.text


def test_tampered_session_cookie_is_rejected(app):
    """A signed cookie, not just an opaque user id -- setting an
    arbitrary/forged value must not authenticate as anyone."""
    forged = TestClient(app)
    forged.cookies.set("dhra_session", "not-a-real-signed-token")
    resp = forged.get("/")
    assert "Guest -- shared demo" in resp.text  # falls back to guest, not an error, not someone else's account


def test_signup_page_warns_about_ephemeral_storage_when_demo_banner_set(app_with_demo_banner):
    client = TestClient(app_with_demo_banner)
    resp = client.get("/signup")
    assert "storage resets on restart" in resp.text


def test_signup_page_has_no_ephemeral_warning_without_demo_banner(app):
    client = TestClient(app)
    resp = client.get("/signup")
    assert "storage resets on restart" not in resp.text
