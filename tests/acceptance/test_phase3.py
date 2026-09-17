"""Phase 3 exit test battery -- DHRA_BUILD_SPEC.md section 6 (Phase 3).

Exit test (spec wording): "A real acquisition run against a real
archive completes within published rate limits, with permission
checkpoints honoured and every licence constraint recorded per item."

The live-network part of that (`test_live_zenodo_acquisition_end_to_end`)
is skipped by default -- see its own docstring -- and was run manually
once against the real Zenodo API to prove the path genuinely works, not
just against a fake session.
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from dhra.calendar import convert_date_claim
from dhra.evidence import search
from dhra.interchange.tei import to_tei
from dhra.interchange.zotero import from_zotero_item, to_zotero_item
from dhra.models import DateClaim
from dhra.permissions import ActionSpec, ApprovalRequired, PermissionClass, check_permission
from dhra.rate_limit import RateLimitExceeded, RateLimiter
from dhra.repo import DHRARepo
from dhra.source_registry import RateLimitSpec, SourceEntry, load_registry
from dhra.zenodo import acquire_from_zenodo


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


TEST_SOURCE = SourceEntry(
    id="test_archive",
    name="Test Archive",
    access="api",
    rate_limit=RateLimitSpec(requests=3, per_seconds=1.0),
    identify_as="DHRA-test/0.1",
    bulk_download="prohibited",
    redistribution="prohibited",
    tdm_basis="licensed",
    robots_respected=True,
)


# --- Permissions (section 9.1) ----------------------------------------------


def test_ask_tool_blocked_without_approval(repo):
    spec = ActionSpec(tool="acquire_source", summary="Request 340 items from Archive A, ~2.1 GB.", details={})
    with pytest.raises(ApprovalRequired) as exc_info:
        check_permission(repo, PermissionClass.ASK, spec, actor="researcher")
    assert exc_info.value.spec.summary == spec.summary  # specifics, not a generic prompt


def test_ask_tool_proceeds_after_exact_matching_approval(repo):
    spec = ActionSpec(tool="acquire_source", summary="Request 340 items from Archive A, ~2.1 GB.", details={})
    repo.grant_approval(tool=spec.tool, summary=spec.summary, actor="researcher")
    check_permission(repo, PermissionClass.ASK, spec, actor="researcher")  # does not raise

    # Approval is consumed, scoped to this one action (section 9.1) -- reusing it fails.
    with pytest.raises(ApprovalRequired):
        check_permission(repo, PermissionClass.ASK, spec, actor="researcher")


def test_approval_for_different_specifics_does_not_transfer(repo):
    granted = ActionSpec(tool="acquire_source", summary="Request 10 items from Archive A.", details={})
    repo.grant_approval(tool=granted.tool, summary=granted.summary, actor="researcher")

    different = ActionSpec(tool="acquire_source", summary="Request 10000 items from Archive A.", details={})
    with pytest.raises(ApprovalRequired):
        check_permission(repo, PermissionClass.ASK, different, actor="researcher")


def test_read_class_tools_never_need_approval(repo):
    spec = ActionSpec(tool="search_evidence", summary="search the corpus", details={})
    check_permission(repo, PermissionClass.READ, spec, actor="researcher")  # no raise, no approval needed


# --- Rate limiting (section 9.2, 13.3 test_rate_limit_hard) -----------------


def test_rate_limit_hard_blocks_under_concurrency():
    limiter = RateLimiter()
    now = time.monotonic()
    for _ in range(TEST_SOURCE.rate_limit.requests):
        limiter.check(TEST_SOURCE, now=now)  # fills the window, does not warn-and-allow
    with pytest.raises(RateLimitExceeded):
        limiter.check(TEST_SOURCE, now=now)  # blocks, does not silently proceed

    # After the window elapses, requests are allowed again.
    later = now + TEST_SOURCE.rate_limit.per_seconds + 0.01
    limiter.check(TEST_SOURCE, now=later)


# --- Source registry (section 9.2) ------------------------------------------


def test_source_registry_loads_real_zenodo_config():
    registry = load_registry("config/sources.yaml")
    assert "zenodo" in registry
    zenodo = registry["zenodo"]
    assert zenodo.rate_limit.requests == 60
    assert zenodo.bulk_download == "prohibited"
    assert "DHRA" in zenodo.identify_as


# --- Calendar handling (section 4.5, 6) -------------------------------------


def test_hijri_day_precision_matches_spec_own_example():
    # DHRA_BUILD_SPEC.md section 4.5's own DateClaim example.
    claim = DateClaim(original_expression="12 Rebiulevvel 1265", calendar="hijri", precision="day", asserted_by="researcher")
    converted = convert_date_claim(claim, year=1265, month=3, day=12)
    assert converted.converted_iso == "1849-02-05"
    assert converted.conversion_method == "convertdate:hijri->gregorian"
    assert converted.original_expression == claim.original_expression  # never altered (I9)


def test_julian_day_precision():
    claim = DateClaim(original_expression="5 Feb 1849 (O.S.)", calendar="julian", precision="day", asserted_by="researcher")
    converted = convert_date_claim(claim, year=1849, month=2, day=5)
    assert converted.converted_iso == "1849-02-17"


def test_month_precision_produces_range_not_bare_iso():
    claim = DateClaim(original_expression="Rebiulevvel 1265", calendar="hijri", precision="month", asserted_by="researcher")
    converted = convert_date_claim(claim, year=1265, month=3)
    assert converted.converted_iso is None  # a month is not a single day -- no bare ISO date
    assert converted.range_start is not None
    assert converted.range_end is not None
    assert converted.range_start < converted.range_end


def test_unsupported_calendar_left_unconverted():
    claim = DateClaim(original_expression="3rd year of the reign", calendar="regnal", precision="year", asserted_by="researcher")
    converted = convert_date_claim(claim, year=3)
    assert converted is claim  # no defensible conversion offered, not guessed
    assert converted.converted_iso is None


# --- Zotero/TEI interchange (section 6) -------------------------------------


def test_tei_export_round_trip_readable_by_tei_transcriber(repo):
    from dhra.transcribe import TeiTranscriber

    item_id, rep_id = repo.ingest_text("the treaty was signed at Sivas", source_id="s", original_reference="https://example.org/doc/1")
    repo.add_assertion(subject_item_id=item_id, predicate="title", value="Treaty Notice", original_expression="Treaty Notice", asserted_by="researcher", confidence="stated")
    projection = repo.projection()
    item = projection.items[item_id]
    rep = projection.representations[rep_id]
    assertions = [projection.assertions[a] for a in projection.assertions_by_item[item_id]]

    tei_xml = to_tei(item, rep, assertions)
    assert "Treaty Notice" in tei_xml
    assert "the treaty was signed at Sivas" in tei_xml

    result = TeiTranscriber().transcribe(tei_xml.encode("utf-8"))
    assert result.text == "the treaty was signed at Sivas"


def test_zotero_export_import_round_trip(repo):
    item_id, rep_id = repo.ingest_text("a document about the flood", source_id="s", original_reference="https://example.org/doc/2")
    repo.add_assertion(subject_item_id=item_id, predicate="title", value="Flood Report", original_expression="Flood Report", asserted_by="researcher", confidence="stated")
    repo.add_assertion(subject_item_id=item_id, predicate="creator", value="A. Researcher", original_expression="A. Researcher", asserted_by="researcher", confidence="stated")
    projection = repo.projection()
    item = projection.items[item_id]
    assertions = [projection.assertions[a] for a in projection.assertions_by_item[item_id]]

    zotero_item = to_zotero_item(item, assertions)
    assert zotero_item["title"] == "Flood Report"
    assert zotero_item["creators"] == [{"creatorType": "author", "name": "A. Researcher"}]
    assert zotero_item["url"] == "https://example.org/doc/2"

    reimported = from_zotero_item(zotero_item, asserted_by="zotero_import")
    values = {d["predicate"]: d["value"] for d in reimported}
    assert values["title"] == "Flood Report"
    assert values["creator"] == "A. Researcher"


# --- Orthographic variant expansion (section 8.2) ---------------------------


def test_orthographic_variants_shown_not_silent(repo):
    repo.ingest_text("witnesses said the man shewed great courage", source_id="s1")
    repo.ingest_text("the report showed clear evidence of damage", source_id="s2")

    response = search(repo, "showed", variants=["shewed"])
    assert response.variant_expansion == ("shewed",)

    variant_hits = [p for p in response.evidence if "shewed" in p.rationale]
    literal_hits = [p for p in response.evidence if p.rationale.startswith("contains the literal")]
    assert variant_hits, "the shewed spelling must be found and clearly labelled as a variant match"
    assert literal_hits, "the literal showed spelling must still be found"

    # Display always shows the original orthography (I9) -- never a normalised form.
    for p in variant_hits:
        assert p.text.lower() == "shewed"


# --- MCP server (section 16) -------------------------------------------------


def test_mcp_server_search_tool_works(repo):
    from dhra.mcp_server import build_mcp_server

    repo.ingest_text("the bridge at Tokat was repaired", source_id="s")
    server = build_mcp_server(repo)

    async def run():
        return await server.call_tool("search_evidence", {"query": "Tokat"})

    result = asyncio.run(run())
    assert result.is_error is False
    assert result.structured_content["evidence"]


def test_mcp_server_zenodo_tool_requires_approval_first(repo):
    from dhra.mcp_server import build_mcp_server

    server = build_mcp_server(repo, zenodo_source=TEST_SOURCE)

    async def run():
        return await server.call_tool(
            "request_zenodo_acquisition",
            {"record_id": "123456", "filename": None, "actor": "researcher"},
        )

    result = asyncio.run(run())
    assert result.structured_content["status"] == "approval_required"
    assert "123456" in result.structured_content["summary"]


def test_mcp_server_grant_then_deny_are_both_logged(repo):
    from dhra.mcp_server import build_mcp_server

    server = build_mcp_server(repo)

    async def run():
        await server.call_tool("grant_approval", {"tool": "x", "summary": "y", "actor": "researcher"})
        return await server.call_tool("deny_approval", {"tool": "a", "summary": "b", "reason": "too broad", "actor": "researcher"})

    result = asyncio.run(run())
    assert result.structured_content["status"] == "denied"
    from dhra.permissions import approval_rate

    rate = approval_rate(repo)
    assert rate["granted"] == 1
    assert rate["denied"] == 1


# --- Real Zenodo acquisition (the actual exit test) -------------------------


def test_live_zenodo_acquisition_end_to_end(repo, tmp_path):
    """Skipped by default -- hits the real, live Zenodo API and is
    therefore slow/network-dependent/not something every `pytest` run
    should depend on. Run explicitly with:

        DHRA_LIVE_NETWORK_TESTS=1 pytest tests/acceptance/test_phase3.py -k live -q

    This is what actually proves the exit test ("a real acquisition run
    against a real archive completes within published rate limits, with
    permission checkpoints honoured and every licence constraint
    recorded per item") rather than a fake session standing in for it.
    """
    if not os.environ.get("DHRA_LIVE_NETWORK_TESTS"):
        pytest.skip("live network test -- set DHRA_LIVE_NETWORK_TESTS=1 to run against the real Zenodo API")

    registry = load_registry("config/sources.yaml")
    source = registry["zenodo"]
    limiter = RateLimiter()

    # A real, public, open-access Zenodo record (verified via a manual
    # `curl` against the live search API before pinning this id here).
    record_id = "6164620"

    spec_summary = f"Acquire Zenodo record {record_id} (metadata only) from {source.id}."
    repo.grant_approval(tool="acquire_from_zenodo", summary=spec_summary, actor="researcher")

    item_id = acquire_from_zenodo(repo, record_id=record_id, filename=None, source=source, limiter=limiter, actor="researcher")

    projection = repo.projection()
    item = projection.items[item_id]
    assert item.acquisition.source_id == "zenodo"
    assert item.acquisition.access_basis == source.tdm_basis
    assert item.acquisition.redistributable is False  # per config/sources.yaml's redistribution: prohibited
    assert item.acquisition.original_reference == f"https://zenodo.org/records/{record_id}"
