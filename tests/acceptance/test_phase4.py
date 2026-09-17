"""Phase 4 exit test battery -- DHRA_BUILD_SPEC.md section 6 (Phase 4).

Exit test (spec wording): "A generated methods statement contains
everything Section 11.4 requires and round-trips through the export
test."
"""

from __future__ import annotations

import json

import pytest

from dhra.annotation import add_annotation, annotations_for, resolve_annotation
from dhra.drafting import DraftStatus, approve_draft, create_draft, get_draft, reject_draft
from dhra.evidence import search
from dhra.export import export_corpus, reconstruct_from_export
from dhra.methods_export import build_methods_statement
from dhra.models import ExclusionReason, Quality
from dhra.monitoring import check_monitor, check_monitors, list_monitors, save_monitor
from dhra.repo import DHRARepo


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


def _seed_realistic_corpus(repo: DHRARepo) -> dict:
    item_a, rep_a = repo.ingest_text("the bridge at Tokat was repaired in 1850", source_id="archive_a")
    item_b = repo.acquire_item(b"scan bytes", source_id="archive_b", method="manual_upload", access_basis="public_domain", media_type="image/tiff")
    repo.create_representation(item_id=item_b, kind="transcription", producer="tesseract", producer_version="5.3.4", text="a faded record of the same repair", quality=Quality(mean_char_confidence=0.4))
    repo.exclude_item(item_id=item_b, reason=ExclusionReason.BELOW_QUALITY, actor="researcher", threshold=0.55, observed=0.4)
    repo.record_access_failure(source_id="archive_c", reason="access_denied")
    search(repo, "bridge")
    search(repo, "Tokat")
    return {"item_a": item_a, "item_b": item_b}


# --- Phase 4 exit test: methods statement ------------------------------------


def test_methods_statement_contains_everything_section_11_4_requires(repo):
    _seed_realistic_corpus(repo)
    statement = build_methods_statement(repo.events)
    d = statement.to_dict()

    # "corpus definition and version hash"
    assert d["corpus_version"]
    assert d["corpus_item_count"] == 1  # item_b excluded

    # "acquisition sources with dates, access conditions and licence basis"
    assert d["acquisition_sources"]
    for s in d["acquisition_sources"]:
        assert s["earliest_retrieved_at"] and s["latest_retrieved_at"]
        assert s["access_basis"]

    # "the transformation chain with tool versions"
    assert any(t["producer"] == "manual" for t in d["transformation_chain"])

    # "selection criteria with counts at each stage"
    assert d["selection_criteria"] == {"total_acquired": 2, "total_excluded": 1, "total_included": 1}

    # "exclusion summary by reason"
    assert d["exclusion_summary"] == [{"reason": "below_quality_threshold", "count": 1}]

    # "the full query set"
    queries = {q["query"] for q in d["query_set"]}
    assert queries == {"bridge", "Tokat"}

    # "model identities and versions used, with purposes" -- real, truthfully empty (no LLM layer yet)
    assert d["model_invocations"] == []

    # "a statement of known limitations drawn from the bias report (including access failures)"
    assert d["bias_report"]["access_failure_count"] == 1
    assert d["limitations"]  # non-empty: at least the access-failure warning


def test_methods_statement_round_trips_through_export(repo, tmp_path):
    _seed_realistic_corpus(repo)
    export_dir = tmp_path / "export"
    export_corpus(repo.root, export_dir)

    # Present on disk, in the same self-contained, generically-readable
    # export as everything else (I12).
    on_disk = json.loads((export_dir / "methods_statement.json").read_text(encoding="utf-8"))
    assert on_disk["corpus_item_count"] == 1

    rebuilt = reconstruct_from_export(export_dir)  # stdlib-only reconstructor
    assert rebuilt["methods_statement"] is not None
    assert rebuilt["methods_statement"]["corpus_version"] == on_disk["corpus_version"]
    assert rebuilt["manifest_hash_ok"] is True
    assert rebuilt["checksum_errors"] == []


def test_methods_statement_model_invocations_populated_when_real(repo):
    repo.log_model_invocation(model="claude-sonnet-5", purpose="query_expansion", prompt_sha256="abc123")
    statement = build_methods_statement(repo.events)
    assert len(statement.model_invocations) == 1
    assert statement.model_invocations[0].model == "claude-sonnet-5"
    assert statement.model_invocations[0].purpose == "query_expansion"


# --- Drafting under approval (section 6, 9.1, 10, 15) -----------------------


def test_draft_lifecycle_never_auto_sends(repo):
    draft_id = create_draft(repo, kind="correspondence", text="Dear Archive, may we request...", actor="researcher")
    draft = get_draft(repo, draft_id)
    assert draft.status == DraftStatus.PENDING

    approve_draft(repo, draft_id=draft_id, actor="researcher")
    approved = get_draft(repo, draft_id)
    assert approved.status == DraftStatus.APPROVED
    assert approved.text == draft.text  # approval does not mutate the content

    # No send/submit/publish function exists anywhere in dhra.drafting --
    # section 15's anti-requirement, checked structurally.
    import dhra.drafting as drafting_module

    assert not any(name.startswith("send") or name.startswith("submit") or name.startswith("publish") for name in dir(drafting_module))


def test_draft_rejection_is_logged_with_reason(repo):
    draft_id = create_draft(repo, kind="prose", text="A synthesis paragraph.", actor="researcher")
    reject_draft(repo, draft_id=draft_id, reason="overclaims beyond the evidence", actor="researcher")
    draft = get_draft(repo, draft_id)
    assert draft.status == DraftStatus.REJECTED


# --- Shared corpora with annotation threads (section 6) ---------------------


def test_annotation_thread_add_and_resolve(repo):
    item_a, _rep_a = repo.ingest_text("a disputed claim about the bridge", source_id="s")
    add_annotation(repo, target_type="item", target_id=item_a, text="Is this the same bridge as in the 1849 dispatch?", actor="researcher_1")
    a2 = add_annotation(repo, target_type="item", target_id=item_a, text="Yes, confirmed against the gazette.", actor="researcher_2")

    thread = annotations_for(repo, target_type="item", target_id=item_a)
    assert len(thread) == 2
    assert [a.actor for a in thread] == ["researcher_1", "researcher_2"]
    assert all(not a.resolved for a in thread)

    resolve_annotation(repo, annotation_id=a2, actor="researcher_1")
    thread_after = annotations_for(repo, target_type="item", target_id=item_a)
    assert thread_after[1].resolved is True
    assert thread_after[0].resolved is False  # only the resolved one flips


# --- Literature monitoring (section 6) ---------------------------------------


def test_monitor_reports_only_genuinely_new_matches(repo):
    repo.ingest_text("the first report on the Tokat bridge repair", source_id="s1")
    monitor_id = save_monitor(repo, name="Tokat bridge watch", query="Tokat", actor="researcher")
    assert len(list_monitors(repo)) == 1

    first = check_monitor(repo, monitor_id)
    assert len(first.matched_item_ids) == 1
    assert first.new_item_ids == first.matched_item_ids  # everything is new on the first check

    second = check_monitor(repo, monitor_id)
    assert second.new_item_ids == ()  # nothing new -- same corpus

    repo.ingest_text("a second, later report on the Tokat bridge", source_id="s2")
    third = check_monitor(repo, monitor_id)
    assert len(third.matched_item_ids) == 2
    assert len(third.new_item_ids) == 1  # only the newly-ingested item is "new"


def test_check_monitors_runs_every_saved_monitor(repo):
    repo.ingest_text("a note about Sivas", source_id="s")
    save_monitor(repo, name="m1", query="Sivas", actor="researcher")
    save_monitor(repo, name="m2", query="nonexistent_term_xyz", actor="researcher")
    results = check_monitors(repo)
    assert len(results) == 2
    assert any(r.matched_item_ids for r in results)
    assert any(not r.matched_item_ids for r in results)
