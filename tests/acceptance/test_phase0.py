"""Phase 0 exit test battery -- DHRA_BUILD_SPEC.md section 6 (Phase 0) and
section 13.1/13.3. A phase is not done when the features exist; it is
done when its exit test passes.
"""

from __future__ import annotations

import json

import pytest

from dhra.export import export_corpus, reconstruct_from_export
from dhra.models import DateClaim, ExclusionReason, Locator
from dhra.repo import DHRARepo
from dhra.store.projection import fold, materialise_sqlite


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


def _seed_two_items(repo: DHRARepo) -> tuple[str, str, str]:
    item_a = repo.acquire_item(
        b"page one raw bytes",
        source_id="test_source",
        method="manual_upload",
        access_basis="public_domain",
        media_type="image/tiff",
    )
    rep_a = repo.create_representation(
        item_id=item_a,
        kind="transcription",
        producer="tesseract",
        producer_version="5.3.0",
        text="the quick brown fox",
    )
    item_b = repo.acquire_item(
        b"page two raw bytes",
        source_id="test_source",
        method="manual_upload",
        access_basis="public_domain",
        media_type="image/tiff",
    )
    return item_a, rep_a, item_b


# --- Phase 0 exit test: rebuild from events, then from export alone --------


def test_phase0_exit_rebuild_from_events_and_export(repo, tmp_path):
    item_a, rep_a, item_b = _seed_two_items(repo)
    repo.exclude_item(item_id=item_b, reason=ExclusionReason.BELOW_QUALITY, actor="researcher", threshold=0.55, observed=0.41)

    claim_seq = repo.events.max_seq()
    version_at_claim = repo.corpus_version(claim_seq)
    assert version_at_claim.item_ids == (item_a,)  # item_b excluded
    assert version_at_claim.exclusions == ((item_b, ExclusionReason.BELOW_QUALITY.value),)

    # More happens after the claim was made -- the claim's version must stay reconstructable.
    repo.acquire_item(
        b"page three, added later",
        source_id="test_source",
        method="manual_upload",
        access_basis="public_domain",
        media_type="image/tiff",
    )
    repo.restore_item(item_id=item_b, actor="researcher")

    # 1. Delete derived.db and rebuild by replaying events.jsonl.
    db_path = repo.root / "derived.db"
    projection_full = fold(repo.events.read_all())
    materialise_sqlite(projection_full, db_path)
    assert db_path.exists()

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT item_id, excluded FROM items ORDER BY item_id").fetchall()
    finally:
        conn.close()
    assert len(rows) == 3
    assert all(excluded == 0 for _item_id, excluded in rows)  # item_b was restored

    # Reconstruct the EARLIER claim's exact state (including its exclusion) despite later events.
    reconstructed_claim_version = repo.corpus_version(claim_seq)
    assert reconstructed_claim_version == version_at_claim
    assert reconstructed_claim_version.manifest_hash == version_at_claim.manifest_hash

    # 2. Export that earlier version and reconstruct from the export alone,
    #    in a fresh directory, using a generic (stdlib-only) reconstructor.
    export_dir = tmp_path / "export_at_claim"
    export_corpus(repo.root, export_dir, seq=claim_seq)

    rebuilt = reconstruct_from_export(export_dir)
    assert rebuilt["manifest_hash_ok"] is True
    assert rebuilt["checksum_errors"] == []
    assert set(rebuilt["items"].keys()) == {item_a, item_b}
    assert rebuilt["items"][item_b]["currently_excluded"] is True
    assert rebuilt["items"][item_b]["exclusion_reason"] == ExclusionReason.BELOW_QUALITY.value
    assert rebuilt["manifest"]["item_ids"] == [item_a]  # only the included set
    assert rep_a in rebuilt["representations"]
    assert rebuilt["representations"][rep_a]["text"] == "the quick brown fox"


# --- 13.1 mechanical --------------------------------------------------------


def test_projection_rebuild_is_deterministic(repo, tmp_path):
    _seed_two_items(repo)
    db1 = tmp_path / "derived1.db"
    db2 = tmp_path / "derived2.db"
    materialise_sqlite(fold(repo.events.read_all()), db1)
    materialise_sqlite(fold(repo.events.read_all()), db2)
    assert db1.read_bytes() != b""  # sanity: something was written
    # Same event prefix -> same rows (ignoring WAL/file-level bytes, compare content).
    import sqlite3

    def dump(path):
        conn = sqlite3.connect(path)
        try:
            return conn.execute("SELECT * FROM items ORDER BY item_id").fetchall()
        finally:
            conn.close()

    assert dump(db1) == dump(db2)


def test_exclusion_reversibility_one_action(repo):
    item_a, _rep_a, item_b = _seed_two_items(repo)
    repo.exclude_item(item_id=item_b, reason=ExclusionReason.WRONG_LANGUAGE, actor="researcher")
    assert item_b not in repo.corpus_version().item_ids

    repo.restore_item(item_id=item_b, actor="researcher")  # single action
    version = repo.corpus_version()
    assert item_b in version.item_ids  # immediate downstream recomputation
    assert version.exclusions == ()


def test_version_reconstruction_six_months_later(repo):
    item_a, _rep_a, item_b = _seed_two_items(repo)
    early_seq = repo.events.max_seq()
    early_version = repo.corpus_version(early_seq)

    # Simulate a lot happening later.
    for _ in range(3):
        repo.acquire_item(b"noise", source_id="s", method="manual_upload", access_basis="public_domain", media_type="text/plain")
    repo.exclude_item(item_id=item_a, reason=ExclusionReason.OUT_OF_DATE_RANGE, actor="researcher")

    assert repo.corpus_version(early_seq) == early_version


def test_export_round_trip_no_app_code(repo, tmp_path):
    _seed_two_items(repo)
    export_dir = tmp_path / "export"
    export_corpus(repo.root, export_dir)
    rebuilt = reconstruct_from_export(export_dir)  # imports nothing from dhra.models/dhra.store
    assert rebuilt["checksum_errors"] == []
    assert rebuilt["manifest_hash_ok"] is True
    assert len(rebuilt["items"]) == 2


# --- 13.3 behavioural (the parts that are Phase-0-testable now) ------------


def test_date_claim_rejects_bare_iso():
    with pytest.raises(ValueError):
        DateClaim(original_expression="", calendar="gregorian", precision="day", asserted_by="researcher")
    with pytest.raises(ValueError):
        DateClaim(original_expression="12 Rebiulevvel 1265", calendar="", precision="day", asserted_by="researcher")

    # Well-formed: original expression + calendar always travel together.
    claim = DateClaim(
        original_expression="12 Rebiulevvel 1265",
        calendar="hijri",
        precision="day",
        asserted_by="researcher",
        converted_iso="1849-02-05",
        conversion_method="hijri_to_gregorian_v1",
    )
    assert claim.original_expression and claim.calendar


def test_representation_requires_producer_version(repo):
    item_a, _rep_a, _item_b = _seed_two_items(repo)
    with pytest.raises(ValueError):
        repo.create_representation(
            item_id=item_a,
            kind="translation",
            producer="claude",
            producer_version="",
            text="whatever",
        )


def test_representation_chain_is_walkable_to_blob(repo):
    item_a, rep_a, _item_b = _seed_two_items(repo)
    rep_translation = repo.create_representation(
        item_id=item_a,
        kind="translation",
        producer="claude-sonnet-5",
        producer_version="2026-09",
        text="tilki",
        parent_rep_id=rep_a,
    )
    projection = repo.projection()
    chain = projection.representation_chain(rep_translation)
    assert [r.rep_id for r in chain] == [rep_translation, rep_a]
    assert chain[-1].parent_rep_id is None  # walks all the way back to the blob


def test_locator_resolves_or_raises(repo):
    item_a, rep_a, _item_b = _seed_two_items(repo)
    good = Locator(item_id=item_a, rep_id=rep_a, start=4, end=9)
    passage = repo.resolve(good)
    assert passage.text == "quick"

    bad = Locator(item_id=item_a, rep_id=rep_a, start=0, end=9999)
    with pytest.raises(ValueError):
        repo.resolve(bad)  # not found, not a degraded/truncated result
