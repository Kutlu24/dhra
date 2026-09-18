"""Terminal interface -- everything the web UI can do, scriptable.

`dhra <command> ...` against a store directory (`--store`, or the
`DHRA_STORE_DIR` environment variable, default `./store`). Same
underlying modules as `dhra.web`/`dhra.mcp_server` -- three surfaces,
one set of invariants, per the researcher's own preference for how they
want to work (terminal, browser, or an MCP-connected agent).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dhra.aggregate import aggregate_by_source
from dhra.evidence import search as evidence_search
from dhra.literature_watch import (
    LiteratureWatchError,
    add_watch_query,
    check_for_updates,
    dismiss_candidate,
    list_candidates,
    list_watch_queries,
    remove_watch_query,
)
from dhra.models import Locator
from dhra.repo import DHRARepo
from dhra.status import Status
from dhra.trace import trace_decisions, trace_summary

STATUS_MEANINGS = {
    Status.ATTESTED: "explicitly stated in a source in the corpus",
    Status.CORROBORATED: "attested in >=2 sources that passed an independence check",
    Status.INFERRED: "follows from E1/E2 by a stated chain",
    Status.CONTESTED: "sources in the corpus disagree",
    Status.SINGLE_WITNESS: "one source, reliability unestablished",
    Status.UNSUPPORTED: "not found; not evidence of non-occurrence",
    Status.NEGATIVE: "a source positively asserts non-occurrence",
    Status.OUT_OF_SCOPE: "this corpus cannot in principle address this claim",
}


def _repo(args: argparse.Namespace) -> DHRARepo:
    store = args.store or os.environ.get("DHRA_STORE_DIR") or "./store"
    return DHRARepo(store)


def _parse_locator(raw: str) -> Locator:
    parts = raw.split(",")
    if len(parts) != 4:
        raise SystemExit(f"malformed locator {raw!r} -- expected item_id,rep_id,start,end")
    item_id, rep_id, start, end = parts
    return Locator(item_id=item_id, rep_id=rep_id, start=int(start), end=int(end))


# --- search ------------------------------------------------------------------


def cmd_search(args: argparse.Namespace) -> None:
    repo = _repo(args)
    response = evidence_search(repo, args.query, variants=args.variant or None)
    if response.variant_expansion:
        print(f"(also searched variants: {', '.join(response.variant_expansion)})")
    if not response.evidence:
        print(response.absence_note)
        return
    for p in response.evidence:
        print(f'"{p.text}"')
        print(f"  {p.locator.item_id}/{p.locator.rep_id}[{p.locator.start}:{p.locator.end}]  ({p.rationale})")
        print()


# --- ingest --------------------------------------------------------------


def cmd_ingest(args: argparse.Namespace) -> None:
    repo = _repo(args)
    kwargs = dict(
        source_id=args.source_id,
        access_basis=args.access_basis,
        licence_id=args.licence_id,
        original_reference=args.original_reference,
    )
    if args.text is not None:
        item_id, rep_id = repo.ingest_text(args.text, **kwargs)
    else:
        path = Path(args.file)
        data = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            item_id, rep_id = repo.ingest_pdf(data, **kwargs)
        elif suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
            item_id, rep_id = repo.ingest_image(data, **kwargs)
        elif suffix in (".xml", ".tei"):
            item_id, rep_id = repo.ingest_tei(data, **kwargs)
        else:
            item_id, rep_id = repo.ingest_text(data.decode("utf-8", errors="replace"), **kwargs)
    print(f"item {item_id}")
    print(f"representation {rep_id}")


# --- claims --------------------------------------------------------------


def cmd_claims_list(args: argparse.Namespace) -> None:
    repo = _repo(args)
    projection = repo.projection()
    for c in sorted(projection.claims.values(), key=lambda c: c.claim_id):
        print(f"{c.status.value}  {c.claim_id}  {c.claim_text}")


def cmd_claims_show(args: argparse.Namespace) -> None:
    repo = _repo(args)
    assessment = repo.get_claim_assessment(args.claim_id)
    if assessment is None:
        raise SystemExit(f"no such claim: {args.claim_id}")
    print(f"{assessment.status.value} -- {STATUS_MEANINGS[assessment.status]}")
    print(assessment.claim_text)
    print()
    print(assessment.note)
    for label, locs in (("supporting", assessment.supporting), ("contradicting", assessment.contradicting), ("negating", assessment.negating)):
        if locs:
            print(f"\n{label}:")
            for loc in locs:
                print(f"  {loc.item_id}/{loc.rep_id}[{loc.start}:{loc.end}]")


def cmd_claims_assess(args: argparse.Namespace) -> None:
    repo = _repo(args)
    supporting = [_parse_locator(s) for s in (args.supporting or [])]
    contradicting = [_parse_locator(s) for s in (args.contradicting or [])]
    negating = [_parse_locator(s) for s in (args.negating or [])]

    if args.independence and supporting:
        assessment, clusters, _verdicts = repo.assess_claim_with_independence(
            claim_id=args.claim_id, claim_text=args.text, supporting=supporting, actor=args.actor
        )
        if clusters:
            print(f"{len(clusters)} descent cluster(s) found and collapsed:")
            for c in clusters:
                print(f"  representative {c.representative}, {len(c.members)} members")
    else:
        assessment = repo.assess_claim(
            claim_id=args.claim_id,
            claim_text=args.text,
            supporting=supporting,
            contradicting=contradicting,
            negating=negating,
        )
    print(f"{assessment.status.value} -- {STATUS_MEANINGS[assessment.status]}")
    print(assessment.note)


# --- aggregate / exclusions / trace ---------------------------------------


def cmd_aggregate(args: argparse.Namespace) -> None:
    repo = _repo(args)
    expected = set(args.expected_language) if args.expected_language else None
    result = aggregate_by_source(repo, expected_languages=expected)
    print(f"Bias report -- {result.bias_report.total_items} items in the active corpus.")
    if result.bias_report.warnings:
        for w in result.bias_report.warnings:
            print(f"  ! {w}")
    else:
        print("  (no warnings)")
    print()
    print("By source:")
    for b in result.buckets:
        print(f"  {b.label}: {len(b.item_ids)} item(s)")


def cmd_exclusions_list(args: argparse.Namespace) -> None:
    repo = _repo(args)
    projection = repo.projection()
    if not projection.active_exclusions:
        print("(no active exclusions)")
        return
    by_reason: dict[str, list[str]] = {}
    for item_id, excl in projection.active_exclusions.items():
        by_reason.setdefault(excl.reason.value, []).append(item_id)
    for reason, item_ids in by_reason.items():
        print(f"{reason} ({len(item_ids)}):")
        for iid in item_ids:
            print(f"  {iid}")


def cmd_exclusions_restore(args: argparse.Namespace) -> None:
    repo = _repo(args)
    repo.restore_item(item_id=args.item_id, actor=args.actor)
    print(f"restored {args.item_id}")


def cmd_trace(args: argparse.Namespace) -> None:
    repo = _repo(args)
    summary = trace_summary(repo.events, args.task)
    print(f"{summary.event_count} event(s)" + (f" for task {args.task}" if args.task else ""))
    for t, c in summary.counts_by_type:
        print(f"  {t}: {c}")
    if args.task:
        print("\nDecisions:")
        for d in trace_decisions(repo.events, args.task):
            print(f"  seq={d['seq']} {d['type']}")


def cmd_watch_add(args: argparse.Namespace) -> None:
    repo = _repo(args)
    watch_id = add_watch_query(repo, query_text=args.query, actor=args.actor)
    print(f"added watch {watch_id}: {args.query!r}")


def cmd_watch_list(args: argparse.Namespace) -> None:
    repo = _repo(args)
    for q in list_watch_queries(repo):
        print(f"{q.watch_id}  {q.query_text!r}  (added by {q.actor})")


def cmd_watch_check(args: argparse.Namespace) -> None:
    repo = _repo(args)
    try:
        new_candidates = check_for_updates(repo)
    except LiteratureWatchError as exc:
        raise SystemExit(f"literature watch check failed: {exc}")
    if not new_candidates:
        print("no new matches")
        return
    for c in new_candidates:
        authors = ", ".join(c.authors) if c.authors else "(no listed authors)"
        print(f"{c.work_id}  {c.title}")
        print(f"  {authors}" + (f" -- {c.publication_date}" if c.publication_date else ""))
        if c.link:
            print(f"  {c.link}")


def cmd_watch_candidates(args: argparse.Namespace) -> None:
    repo = _repo(args)
    candidates = list_candidates(repo)
    if not candidates:
        print("(no new candidates -- run 'dhra watch check' first)")
        return
    for c in candidates:
        authors = ", ".join(c.authors) if c.authors else "(no listed authors)"
        print(f"{c.work_id}  {c.title}")
        print(f"  {authors}" + (f" -- {c.publication_date}" if c.publication_date else ""))


def cmd_watch_remove(args: argparse.Namespace) -> None:
    repo = _repo(args)
    remove_watch_query(repo, args.watch_id, actor=args.actor)
    print(f"removed watch {args.watch_id}")


def cmd_watch_dismiss(args: argparse.Namespace) -> None:
    repo = _repo(args)
    dismiss_candidate(repo, args.work_id, actor=args.actor)
    print(f"dismissed {args.work_id}")


def cmd_web(args: argparse.Namespace) -> None:
    import uvicorn

    from dhra.web.app import build_app

    repo = _repo(args)
    expected = set(args.expected_language) if args.expected_language else None
    demo_banner = os.environ.get("DHRA_DEMO_BANNER") or None
    app = build_app(repo, expected_languages=expected, demo_banner=demo_banner)
    print(f"DHRA web UI: http://{args.host}:{args.port}  (store: {repo.root})")
    uvicorn.run(app, host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dhra", description="Digital Humanities Research Agent -- terminal interface.")
    parser.add_argument("--store", help="store directory (default: $DHRA_STORE_DIR or ./store)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search", help="locator-bound, absence-qualified evidence search")
    p.add_argument("query")
    p.add_argument("--variant", action="append", help="repeatable: an orthographic variant to also search")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("ingest", help="add an item (manual upload)")
    p.add_argument("--source-id", required=True)
    p.add_argument("--access-basis", default="public_domain")
    p.add_argument("--licence-id")
    p.add_argument("--original-reference")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="paste text directly")
    group.add_argument("--file", help="path to a .pdf/.png/.jpg/.tif/.xml/.txt file")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("claims", help="epistemic status")
    claims_sub = p.add_subparsers(dest="claims_command", required=True)

    cp = claims_sub.add_parser("list")
    cp.set_defaults(func=cmd_claims_list)

    cp = claims_sub.add_parser("show")
    cp.add_argument("claim_id")
    cp.set_defaults(func=cmd_claims_show)

    cp = claims_sub.add_parser("assess")
    cp.add_argument("claim_id")
    cp.add_argument("--text", required=True, dest="text")
    cp.add_argument("--actor", default="researcher")
    cp.add_argument("--supporting", action="append", metavar="item_id,rep_id,start,end")
    cp.add_argument("--contradicting", action="append", metavar="item_id,rep_id,start,end")
    cp.add_argument("--negating", action="append", metavar="item_id,rep_id,start,end")
    cp.add_argument("--independence", action="store_true", help="run the independence engine over --supporting first (required for E2)")
    cp.set_defaults(func=cmd_claims_assess)

    p = sub.add_parser("aggregate", help="source aggregate + bias report")
    p.add_argument("--expected-language", action="append", help="repeatable: a language the bias report should expect")
    p.set_defaults(func=cmd_aggregate)

    p = sub.add_parser("exclusions", help="reversible exclusions")
    ex_sub = p.add_subparsers(dest="exclusions_command", required=True)
    ep = ex_sub.add_parser("list")
    ep.set_defaults(func=cmd_exclusions_list)
    ep = ex_sub.add_parser("restore")
    ep.add_argument("item_id")
    ep.add_argument("--actor", default="researcher")
    ep.set_defaults(func=cmd_exclusions_restore)

    p = sub.add_parser("trace", help="decision trace")
    p.add_argument("--task")
    p.set_defaults(func=cmd_trace)

    p = sub.add_parser("watch", help="external literature watch (OpenAlex)")
    watch_sub = p.add_subparsers(dest="watch_command", required=True)

    wp = watch_sub.add_parser("add", help="add a saved query")
    wp.add_argument("query")
    wp.add_argument("--actor", default="researcher")
    wp.set_defaults(func=cmd_watch_add)

    wp = watch_sub.add_parser("list", help="list saved queries")
    wp.set_defaults(func=cmd_watch_list)

    wp = watch_sub.add_parser("remove", help="remove a saved query")
    wp.add_argument("watch_id")
    wp.add_argument("--actor", default="researcher")
    wp.set_defaults(func=cmd_watch_remove)

    wp = watch_sub.add_parser("check", help="run all saved queries against OpenAlex now")
    wp.set_defaults(func=cmd_watch_check)

    wp = watch_sub.add_parser("candidates", help="list new matches found by the last check(s)")
    wp.set_defaults(func=cmd_watch_candidates)

    wp = watch_sub.add_parser("dismiss", help="dismiss a candidate")
    wp.add_argument("work_id")
    wp.add_argument("--actor", default="researcher")
    wp.set_defaults(func=cmd_watch_dismiss)

    p = sub.add_parser("web", help="launch the web UI")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8420)
    p.add_argument("--expected-language", action="append")
    p.set_defaults(func=cmd_web)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
