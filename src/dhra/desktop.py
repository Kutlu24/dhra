"""Desktop launcher -- the entry point PyInstaller bundles into a
standalone executable (see desktop.spec at the repo root). This is
deliberately *not* the same thing as `dhra web` (the CLI command, which
requires a terminal and a --store choice): the whole point of this
module is a double-click experience for someone who has never opened a
terminal -- pick a sensible default store under their home directory,
start the server, open their browser for them.

What this does NOT solve (see the PyInstaller build workflow and
OPEN_QUESTIONS.md for the honest state of each): the executable bundles
DHRA's own Python code and dependencies, but not the external system
binaries `pdftotext` (poppler) or Tesseract OCR that PDF/image
ingestion shell out to -- those still need to be installed separately,
same as the pip-installed CLI. The window that opens is the user's own
default browser, not a native app window. And unsigned Windows/macOS
builds will show an OS security warning on first run until someone
pays for a code-signing certificate.
"""

from __future__ import annotations

import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from dhra.repo import DHRARepo
from dhra.web.app import build_app

DEFAULT_STORE = Path.home() / "DHRA" / "store"
DEFAULT_PORT = 8420


def main() -> None:
    DEFAULT_STORE.mkdir(parents=True, exist_ok=True)
    repo = DHRARepo(DEFAULT_STORE)
    app = build_app(repo)

    def _open_browser() -> None:
        time.sleep(1.5)
        webbrowser.open(f"http://127.0.0.1:{DEFAULT_PORT}")

    threading.Thread(target=_open_browser, daemon=True).start()

    print("DHRA is starting...")
    print(f"Your data is stored in: {DEFAULT_STORE}")
    print(f"If your browser doesn't open automatically, go to http://127.0.0.1:{DEFAULT_PORT}")
    print("Close this window to stop DHRA.")
    uvicorn.run(app, host="127.0.0.1", port=DEFAULT_PORT)


if __name__ == "__main__":
    main()
