"""Search index -- DHRA_BUILD_SPEC.md section 16 ("SQLite FTS5 for search
initially -- defer Elasticsearch until a fixture corpus of 100k items
proves it necessary") and the architecture diagram (`index/` is a
projection, rebuildable, never a second source of truth).

No orthographic variant expansion here (section 8.2) -- that is
scheduled for Phase 3 in the spec's own build order (section 17). This
index does literal, case-insensitive full-text matching only, and every
rationale says so, rather than silently implying more than it does.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from dhra.store.projection import Projection


@dataclass(frozen=True)
class IndexHit:
    rep_id: str
    item_id: str
    text: str
    bm25_rank: float


def build_index(projection: Projection, index_db_path: str | Path) -> None:
    """Rebuild the index from scratch, over every representation of every
    currently-included (non-excluded) item. Disposable: delete the file
    and call this again from a fresh fold() for the same result."""
    index_db_path = Path(index_db_path)
    index_db_path.parent.mkdir(parents=True, exist_ok=True)
    if index_db_path.exists():
        index_db_path.unlink()
    conn = sqlite3.connect(index_db_path)
    try:
        conn.executescript(
            "CREATE VIRTUAL TABLE rep_fts USING fts5(rep_id UNINDEXED, item_id UNINDEXED, text);"
        )
        included = set(projection.active_item_ids())
        for rep in projection.representations.values():
            if rep.item_id not in included:
                continue
            conn.execute(
                "INSERT INTO rep_fts (rep_id, item_id, text) VALUES (?,?,?)",
                (rep.rep_id, rep.item_id, rep.text),
            )
        conn.commit()
    finally:
        conn.close()


def _fts_query(query: str) -> str:
    # Literal phrase match: quote it so FTS5 doesn't interpret the
    # researcher's query as its own query-syntax operators.
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


def search_index(index_db_path: str | Path, query: str, limit: int = 20) -> list[IndexHit]:
    conn = sqlite3.connect(index_db_path)
    try:
        rows = conn.execute(
            "SELECT rep_id, item_id, text, bm25(rep_fts) FROM rep_fts "
            "WHERE rep_fts MATCH ? ORDER BY bm25(rep_fts) LIMIT ?",
            (_fts_query(query), limit),
        ).fetchall()
    finally:
        conn.close()
    return [IndexHit(rep_id=r[0], item_id=r[1], text=r[2], bm25_rank=r[3]) for r in rows]
