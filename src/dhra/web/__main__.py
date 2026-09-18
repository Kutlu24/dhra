"""Run the local DHRA web UI: python -m dhra.web <store_dir> [--port 8420]."""

from __future__ import annotations

import argparse

import uvicorn

from dhra.repo import DHRARepo
from dhra.web.app import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local DHRA web UI against a store directory.")
    parser.add_argument("store_dir", help="DHRARepo root (contains events.jsonl, blobs/)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--expected-language", action="append", default=[], help="repeatable: a language the bias report should expect")
    args = parser.parse_args()

    repo = DHRARepo(args.store_dir)
    app = build_app(repo, expected_languages=set(args.expected_language) or None)
    print(f"DHRA web UI: http://{args.host}:{args.port}  (store: {args.store_dir})")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
