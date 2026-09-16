"""Phase 1 exit test battery -- DHRA_BUILD_SPEC.md section 6 (Phase 1) and
the relevant parts of section 13.1/13.2/13.3 that do not require the
Phase 2 independence engine.

Exit test (spec wording): "Traceability rate and quotation fidelity both
100% across the fixture battery; absence-discipline test passes."
"""

from __future__ import annotations

import pytest

from dhra.evidence import search
from dhra.models import ExclusionReason, Locator, Quality
from dhra.repo import DHRARepo
from dhra.response import NarrativeWithoutEvidenceError, build_response
from dhra.status import Status, lint_e6_text

# Adversarial text battery (section 13.1): smart quotes, ligatures, soft
# hyphens, combining diacritics, RTL text -- each must survive ingestion,
# indexing, retrieval and verbatim-checking byte-exact.
ADVERSARIAL_TEXTS = {
    "smart_quotes": 'She said “the treaty was signed” in 1849.',
    "ligatures": "The ﬁeld oﬃce reported a ﬂood in March.",
    "soft_hyphen": "This word is hy­phen­ated across a line break.",
    "combining_diacritics": "Vóilà, a note with combining acute and grave accents.",
    "rtl_arabic_script": "بسم الله الرحمن الرحيم وقع الحادثة في سنة 1265",
}


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


def _battery_query(text: str) -> str:
    """A whole-word, token-aligned substring of `text`. FTS5 does
    token-level phrase matching, not character-level substring matching,
    so an arbitrary char slice (which can cut a word or a ligature/
    diacritic sequence in half) is the wrong thing to search for --
    picking whole words is what actually exercises I1/I2 (does the
    locator resolve, does the quotation match byte-exact), independent
    of the index's own tokenizer quirks around any one adversarial
    character."""
    words = text.split()
    return " ".join(words[1:3]) if len(words) >= 3 else text


# --- Phase 1 exit test: traceability + quotation fidelity -----------------


@pytest.mark.parametrize("name,text", ADVERSARIAL_TEXTS.items())
def test_traceability_and_quotation_fidelity(repo, name, text):
    item_id, rep_id = repo.ingest_text(text, source_id="adversarial_battery")
    query = _battery_query(text)
    response = search(repo, query)

    assert response.evidence, f"{name}: expected at least one traceable hit"
    for passage in response.evidence:
        # I1: locator resolves in one call.
        resolved = repo.resolve(passage.locator)
        assert resolved is not None
        # I2: displayed quotation matches stored representation byte for byte.
        assert passage.text == resolved.text
        stored_rep_text = repo.projection().representations[passage.locator.rep_id].text
        assert stored_rep_text[passage.locator.start : passage.locator.end] == passage.text


def test_quotation_fidelity_adversarial_battery_full_pass_rate(repo):
    """Traceability rate and quotation fidelity must both be 100% across
    the whole battery, not just per-fixture -- this is the actual exit
    test the spec names."""
    ingested = [repo.ingest_text(text, source_id="battery") for text in ADVERSARIAL_TEXTS.values()]
    total_checked = 0
    for text in ADVERSARIAL_TEXTS.values():
        query = _battery_query(text)
        response = search(repo, query)
        assert response.evidence, "traceability rate must be 100%: every fixture must be findable"
        for passage in response.evidence:
            resolved = repo.resolve(passage.locator)  # raises if it does not resolve
            assert passage.text == resolved.text  # byte-exact, not approximate
            total_checked += 1
    assert total_checked >= len(ADVERSARIAL_TEXTS)


# --- Ingestion formats (section 6, Phase 1: "PDF/image/text/TEI") ----------

# Minimal hand-written single-page PDF (poppler repairs the missing xref
# table) -- real bytes, extracted with the real system `pdftotext`, not a
# mock.
_MINIMAL_PDF = b"""%PDF-1.1
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 300 144] /Contents 5 0 R >> endobj
4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
5 0 obj << /Length 44 >>
stream
BT /F1 18 Tf 10 100 Td (Hello DHRA PDF) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
trailer << /Root 1 0 R /Size 6 >>
%%EOF
"""

_MINIMAL_TEI = b"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader><fileDesc><titleStmt><title>Fixture</title></titleStmt>
  <publicationStmt><p>test</p></publicationStmt>
  <sourceDesc><p>test</p></sourceDesc></fileDesc></teiHeader>
  <text><body><p>Hello DHRA TEI</p></body></text>
</TEI>
"""


def test_ingest_pdf_extracts_real_text_via_pdftotext(repo):
    item_id, rep_id = repo.ingest_pdf(_MINIMAL_PDF, source_id="pdf_fixture")
    rep = repo.projection().representations[rep_id]
    assert "Hello DHRA PDF" in rep.text
    assert rep.producer == "pdftotext"
    assert rep.producer_version  # mandatory, and must reflect the real installed tool


def test_ingest_tei_extracts_text_element(repo):
    item_id, rep_id = repo.ingest_tei(_MINIMAL_TEI, source_id="tei_fixture")
    rep = repo.projection().representations[rep_id]
    assert rep.text == "Hello DHRA TEI"
    assert rep.producer == "tei_extract"


# --- Absence discipline (section 13.2) -------------------------------------


def test_absence_discipline_qualifies_by_legibility_not_unqualified(repo):
    repo.ingest_text("the harvest records for Sivas, 1849", source_id="s")
    good = Quality(mean_char_confidence=0.96)
    bad = Quality(mean_char_confidence=0.41)

    # Build two more items with explicit quality scores so the absence
    # note has real numbers to qualify itself with (section 8.3).
    item_a = repo.acquire_item(b"ocr page a", source_id="s", method="manual_upload", access_basis="public_domain", media_type="image/tiff")
    repo.create_representation(item_id=item_a, kind="transcription", producer="tesseract", producer_version="5.3.0", text="faded ledger entry", quality=good)
    item_b = repo.acquire_item(b"ocr page b", source_id="s", method="manual_upload", access_basis="public_domain", media_type="image/tiff")
    repo.create_representation(item_id=item_b, kind="transcription", producer="tesseract", producer_version="5.3.0", text="another faded entry", quality=bad)

    response = search(repo, "zzz_definitely_absent_token_zzz")
    assert response.evidence == ()
    assert response.narrative is None
    assert response.absence_note is not None

    # Forbidden: unqualified "no mentions found" (section 8.3).
    assert response.absence_note.lower() != "no mentions found"
    assert "corpus version" in response.absence_note.lower() or "searched" in response.absence_note.lower()

    # Must not be phrased as denial (I7, rule 4) -- reuse the actual linter.
    lint_e6_text(response.absence_note)  # raises on failure


def test_e6_never_rendered_as_denial():
    from dhra.status import render_e6

    text = render_e6(corpus_version="abc123", scope="12 items in corpus")
    lint_e6_text(text)  # must not raise
    with pytest.raises(ValueError):
        lint_e6_text("There was no treaty signed in 1849.")
    with pytest.raises(ValueError):
        lint_e6_text("This event never happened.")


# --- Two-channel response contract (I10) -----------------------------------


def test_narrative_rejected_without_evidence(repo):
    from dhra.trace import trace_summary

    with pytest.raises(NarrativeWithoutEvidenceError):
        build_response(
            repo=repo,
            evidence=[],
            trace=trace_summary(repo.events),
            corpus_version=repo.corpus_version().manifest_hash,
            narrative="This claim is confirmed.",
        )


def test_verbatim_check_raises_on_mismatch(repo):
    from dhra.models import Passage
    from dhra.response import VerbatimCheckError
    from dhra.trace import trace_summary

    item_id, rep_id = repo.ingest_text("the quick brown fox", source_id="s")
    real_locator = Locator(item_id=item_id, rep_id=rep_id, start=4, end=9)
    forged_passage = Passage(locator=real_locator, text="SLOW", score=1.0, rationale="forged")

    with pytest.raises(VerbatimCheckError):
        build_response(
            repo=repo,
            evidence=[forged_passage],
            trace=trace_summary(repo.events),
            corpus_version=repo.corpus_version().manifest_hash,
        )


# --- Epistemic status: monotonicity + demotion (section 13.2) --------------


def test_status_monotonicity_reasking_does_not_upgrade(repo):
    item_id, rep_id = repo.ingest_text("the treaty was signed at Sivas", source_id="s")
    loc = Locator(item_id=item_id, rep_id=rep_id, start=0, end=6)

    first = repo.assess_claim(claim_id="c1", claim_text="a treaty was signed", supporting=[loc])
    assert first.status == Status.SINGLE_WITNESS

    # Re-asking with the SAME evidence must not upgrade the status.
    second = repo.assess_claim(claim_id="c1", claim_text="a treaty was signed", supporting=[loc])
    assert second.status == Status.SINGLE_WITNESS

    # Attempting a rise with evidence that isn't actually new must be rejected.
    item_id2, rep_id2 = repo.ingest_text("independent record: treaty at Sivas", source_id="s2")
    loc2 = Locator(item_id=item_id2, rep_id=rep_id2, start=0, end=11)
    third = repo.assess_claim(claim_id="c1", claim_text="a treaty was signed", supporting=[loc, loc2])
    assert third.status == Status.ATTESTED  # genuinely new evidence -> rise is allowed
    assert repo.claim_history("c1")[-1].status == Status.ATTESTED
    assert len(repo.claim_history("c1")) == 3


def test_status_demotion_on_contradiction(repo):
    item_id, rep_id = repo.ingest_text("the treaty was signed in 1849", source_id="s")
    loc = Locator(item_id=item_id, rep_id=rep_id, start=0, end=6)
    first = repo.assess_claim(claim_id="c2", claim_text="a treaty was signed", supporting=[loc])
    assert first.status == Status.SINGLE_WITNESS

    item_id2, rep_id2 = repo.ingest_text("no treaty was ever signed at that location", source_id="s2")
    contra = Locator(item_id=item_id2, rep_id=rep_id2, start=0, end=9)
    demoted = repo.assess_claim(claim_id="c2", claim_text="a treaty was signed", supporting=[loc], contradicting=[contra])
    assert demoted.status == Status.CONTESTED  # a fall is always allowed (rule 3), immediately


def test_status_never_e2_in_phase1(repo):
    """I6: corroboration is never assigned without a passed independence
    check -- Phase 1 has no independence engine, so E2 must be
    unreachable no matter how much supporting evidence is thrown at it."""
    locs = []
    for i in range(5):
        item_id, rep_id = repo.ingest_text(f"independent account number {i} of the same event", source_id=f"s{i}")
        locs.append(Locator(item_id=item_id, rep_id=rep_id, start=0, end=11))
    result = repo.assess_claim(claim_id="c3", claim_text="the event occurred", supporting=locs)
    assert result.status != Status.CORROBORATED
    assert result.status == Status.ATTESTED
