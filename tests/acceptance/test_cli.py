"""CLI acceptance tests -- dhra.cli mirrors the web UI, scriptable.

Runs the real argparse entry point (dhra.cli.main) against a temp store,
not just the underlying functions -- this is what a researcher's shell
script actually invokes.
"""

from __future__ import annotations

import pytest

from dhra.cli import main


@pytest.fixture
def store(tmp_path):
    return str(tmp_path / "store")


def test_ingest_then_search_round_trip(store, capsys):
    main(["--store", store, "ingest", "--source-id", "s", "--text", "a record about Amasya"])
    out = capsys.readouterr().out
    assert "item " in out
    item_id = out.splitlines()[0].split()[1]

    main(["--store", store, "search", "Amasya"])
    out = capsys.readouterr().out
    assert '"Amasya"' in out
    assert item_id in out


def test_search_absence_note_when_nothing_found(store, capsys):
    main(["--store", store, "ingest", "--source-id", "s", "--text", "an unrelated sentence"])
    capsys.readouterr()
    main(["--store", store, "search", "zzz_absent_zzz"])
    out = capsys.readouterr().out
    assert "not evidence of non-occurrence" in out.lower()


def test_claims_assess_and_show(store, capsys):
    main(["--store", store, "ingest", "--source-id", "s", "--text", "a claim source sentence"])
    item_id = capsys.readouterr().out.splitlines()[0].split()[1]

    from dhra.repo import DHRARepo

    repo = DHRARepo(store)
    proj = repo.projection()
    rep_id = proj.reps_by_item[item_id][0]

    main([
        "--store", store, "claims", "assess", "c2",
        "--text", "the claim text",
        "--supporting", f"{item_id},{rep_id},0,5",
    ])
    out = capsys.readouterr().out
    assert out.startswith("E5")

    main(["--store", store, "claims", "show", "c2"])
    out = capsys.readouterr().out
    assert "E5" in out
    assert "the claim text" in out


def test_aggregate_shows_bias_report_and_buckets(store, capsys):
    main(["--store", store, "ingest", "--source-id", "only_source", "--text", "a lone item"])
    capsys.readouterr()
    main(["--store", store, "aggregate"])
    out = capsys.readouterr().out
    assert "Bias report" in out
    assert "By source:" in out
    assert out.index("Bias report") < out.index("By source:")


def test_exclusions_list_and_restore(store, capsys):
    main(["--store", store, "ingest", "--source-id", "s", "--text", "an excludable item"])
    item_id = capsys.readouterr().out.splitlines()[0].split()[1]

    from dhra.models import ExclusionReason
    from dhra.repo import DHRARepo

    repo = DHRARepo(store)
    repo.exclude_item(item_id=item_id, reason=ExclusionReason.BELOW_QUALITY, actor="researcher")

    main(["--store", store, "exclusions", "list"])
    out = capsys.readouterr().out
    assert "below_quality_threshold" in out
    assert item_id in out

    main(["--store", store, "exclusions", "restore", item_id])
    out = capsys.readouterr().out
    assert "restored" in out
    assert item_id in repo.corpus_version().item_ids


def test_watch_add_check_and_dismiss(store, capsys, monkeypatch):
    main(["--store", store, "watch", "add", "Ottoman manuscripts"])
    out = capsys.readouterr().out
    assert "added watch" in out

    main(["--store", store, "watch", "list"])
    out = capsys.readouterr().out
    assert "Ottoman manuscripts" in out

    import requests

    class _FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [
                    {
                        "id": "https://openalex.org/W111",
                        "title": "A new find in the Tokat archive",
                        "publication_date": "2026-09-15",
                        "primary_location": {"landing_page_url": "https://doi.org/10.1234/W111"},
                        "authorships": [{"author": {"display_name": "Jane Historian"}}],
                    }
                ]
            }

    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **kw: _FakeResp())

    main(["--store", store, "watch", "check"])
    out = capsys.readouterr().out
    assert "W111" in out
    assert "A new find in the Tokat archive" in out

    main(["--store", store, "watch", "candidates"])
    out = capsys.readouterr().out
    assert "A new find in the Tokat archive" in out

    main(["--store", store, "watch", "dismiss", "W111"])
    out = capsys.readouterr().out
    assert "dismissed W111" in out

    main(["--store", store, "watch", "candidates"])
    out = capsys.readouterr().out
    assert "no new candidates" in out.lower()
