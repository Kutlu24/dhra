"""Passage retrieval -- DHRA_BUILD_SPEC.md section 8.1/8.2/8.3, wired to
the two-channel response contract (section 10.1).

`search()` is the reference implementation of `POST /evidence/search`
(section 11.2): every hit turned into a locator-bound `Passage` with a
stated rationale, and a zero-hit result qualified by the legibility of
what was searched (section 8.3) rather than rendered as an unqualified
"no mentions found".

Orthographic variant expansion (section 8.2) is caller-supplied, not
generated here (period/region-aware expansion needs a real variant
lexicon this project doesn't have yet -- see OPEN_QUESTIONS.md): pass
`variants=[...]` and each is searched in addition to `query`, shown
(never silent) via `Response.variant_expansion`, with each matching
passage's rationale naming which spelling actually matched (index-only:
display always shows the stored orthography, never a normalised form --
I9).
"""

from __future__ import annotations

import re

from dhra.index import build_index, search_index
from dhra.models import ExclusionReason, Locator, Passage
from dhra.repo import DHRARepo
from dhra.response import Response, build_response
from dhra.status import lint_e6_text, render_e6
from dhra.trace import trace_summary


def _find_span(text: str, query: str) -> tuple[int, int] | None:
    match = re.search(re.escape(query), text, re.IGNORECASE)
    if match is None:
        return None
    return match.start(), match.end()


def search(repo: DHRARepo, query: str, *, task: str | None = None, limit: int = 20, variants: list[str] | None = None) -> Response:
    projection = repo.projection()
    version = repo.corpus_version()
    variants = variants or []

    index_path = repo.root / "index" / "fts.db"
    build_index(projection, index_path)

    passages: list[Passage] = []
    seen_locators: set[tuple[str, str, int, int]] = set()
    for term, is_variant in [(query, False)] + [(v, True) for v in variants]:
        for hit in search_index(index_path, term, limit=limit):
            span = _find_span(hit.text, term)
            if span is None:
                # FTS5 matched via its own tokenisation but no literal substring
                # exists (e.g. punctuation-adjacent token) -- do not fabricate
                # a locator for a passage we cannot point at exactly (I1/I2).
                continue
            start, end = span
            key = (hit.item_id, hit.rep_id, start, end)
            if key in seen_locators:
                continue
            seen_locators.add(key)
            locator = Locator(item_id=hit.item_id, rep_id=hit.rep_id, start=start, end=end)
            rationale = f"matched via orthographic variant {term!r}" if is_variant else f"contains the literal query term {term!r}"
            passages.append(Passage(locator=locator, text=hit.text[start:end], score=hit.bm25_rank, rationale=rationale))

    trace = trace_summary(repo.events, task)

    if not passages:
        absence_note = _quality_qualified_absence(projection, version)
        return build_response(
            repo=repo,
            evidence=[],
            trace=trace,
            corpus_version=version.manifest_hash,
            absence_note=absence_note,
            variant_expansion=tuple(variants),
        )

    return build_response(
        repo=repo,
        evidence=passages,
        trace=trace,
        corpus_version=version.manifest_hash,
        variant_expansion=tuple(variants),
    )


def _quality_qualified_absence(projection, version) -> str:
    total_items = len(version.item_ids)
    confidences = [
        rep.quality.mean_char_confidence
        for item_id in version.item_ids
        for rep_id in projection.representation_ids_for(item_id)
        if (rep := projection.representations[rep_id]).quality is not None
        and rep.quality.mean_char_confidence is not None
    ]
    mean_conf = sum(confidences) / len(confidences) if confidences else None
    below_quality_excluded = sum(
        1
        for excl in projection.active_exclusions.values()
        if excl.reason in (ExclusionReason.FORMAT_UNREADABLE, ExclusionReason.BELOW_QUALITY)
    )
    conf_part = f"{mean_conf:.2f}" if mean_conf is not None else "unavailable (no scored representations)"
    scope = (
        f"{total_items} items in corpus version {version.manifest_hash[:12]}. "
        f"Mean character confidence across the searched set: {conf_part}. "
        f"{below_quality_excluded} items were unreadable/below-quality and excluded."
    )
    note = render_e6(corpus_version=version.manifest_hash[:12], scope=scope)
    lint_e6_text(note)
    return note
