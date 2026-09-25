"""Accessibility acceptance tests -- axe-core scan of key DHRA pages.

Runs pages through a real headless browser (not TestClient's stub DOM)
against a live uvicorn instance, so axe-core sees the actual computed
styles/ARIA a screen reader or a11y tool would encounter. DHRA is a
research tool used by scholars, some of whom rely on assistive tech --
this is a correctness check for that audience, not cosmetic polish.
"""

from __future__ import annotations

import multiprocessing
import socket
import time
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

AXE_SCRIPT = (Path(__file__).parent.parent / "fixtures" / "axe.min.js").read_text()

# Unauthenticated pages covering the app's main surfaces (dashboard,
# search, ingest, docs, teaching, accounts). Login-gated pages
# (claims, dashboard-with-data, etc.) aren't included here -- a
# separate seeded-session fixture would be needed for those.
PAGES = [
    "/",
    "/evidence",
    "/ingest",
    "/tutorial",
    "/start",
    "/teaching",
    "/sources",
    "/assistant",
    "/login",
    "/signup",
]

# axe rule IDs known-bad and intentionally deferred, keyed by reason.
# Empty until a real finding needs to be triaged rather than fixed --
# don't add to this to silence a violation without a linked follow-up.
ALLOWED_VIOLATION_IDS: set[str] = set()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _run_server(store_dir: str, accounts_dir: str, port: int) -> None:
    import uvicorn

    from dhra.repo import DHRARepo
    from dhra.web.app import build_app

    repo = DHRARepo(Path(store_dir))
    # accounts_dir set so /login and /signup render their real templates
    # instead of _require_accounts()'s bare 404 (single-tenant mode).
    app = build_app(repo, accounts_dir=Path(accounts_dir), session_secret="test-secret")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


@pytest.fixture(scope="module")
def live_server(tmp_path_factory):
    # Run uvicorn in its own OS process, not a thread: a thread shares
    # the test process's asyncio loop bookkeeping, and uvicorn.run()
    # tripped "asyncio.run() cannot be called from a running event
    # loop" in later, unrelated async tests (test_phase3.py's MCP
    # tests) once both ran in the same session.
    store_dir = tmp_path_factory.mktemp("store")
    accounts_dir = tmp_path_factory.mktemp("accounts") / "accounts"
    port = _free_port()
    # spawn, not fork: by fixture time Playwright's browser fixture has
    # already started its own threads, and forking a multi-threaded
    # process is unsafe (can deadlock in the child).
    ctx = multiprocessing.get_context("spawn")
    proc = ctx.Process(target=_run_server, args=(str(store_dir), str(accounts_dir), port), daemon=True)
    proc.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=0.2)
            break
        except Exception:
            time.sleep(0.1)
    else:
        proc.terminate()
        raise RuntimeError("live_server did not start in time")
    yield url
    proc.terminate()
    proc.join(timeout=5)


@pytest.mark.parametrize("path", PAGES)
def test_page_has_no_serious_axe_violations(live_server, page, path):
    page.goto(f"{live_server}{path}")
    page.add_script_tag(content=AXE_SCRIPT)
    results = page.evaluate("async () => await axe.run()")
    serious = [
        v
        for v in results["violations"]
        if v["impact"] in ("serious", "critical") and v["id"] not in ALLOWED_VIOLATION_IDS
    ]
    assert not serious, "\n".join(
        f"[{v['impact']}] {v['id']}: {v['help']} ({v['helpUrl']}) -- "
        f"{len(v['nodes'])} node(s), e.g. {v['nodes'][0]['html'][:200]}"
        for v in serious
    )
