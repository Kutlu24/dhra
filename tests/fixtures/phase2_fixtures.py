"""Phase 2 fixtures -- DHRA_BUILD_SPEC.md section 14, fixtures 1 and 2.

Generated synthetically (not committed as static corpus files: DHRA has
no "raw corpus directory" input format -- every item enters through
`DHRARepo.acquire_item`/`ingest_*`, so "the fixture" is this generator
plus the ids it hands back, not files on disk). Ground truth for each is
also written as a static, human-readable `GROUND_TRUTH.json` alongside
this file (ids are fresh ULIDs every run, so those files describe
structure/counts, not literal ids).
"""

from __future__ import annotations

from dhra.repo import DHRARepo

# --- Fixture 1: reprint_family -----------------------------------------

_LEADS = [
    "By telegraph, 14th instant: ",
    "Special dispatch -- ",
    "We are informed that ",
    "According to the latest wire, ",
    "Our correspondent reports: ",
    "Late intelligence states that ",
    "From our correspondent: ",
    "The following dispatch has reached us: ",
    "Telegraphic advices report that ",
    "It is reported by wire that ",
    "News has reached this office that ",
]

_BODY_FULL = (
    "Governor Ahmed Reshud of Sivas province has ordered the immediate repair "
    "of the flood-damaged bridge at Tokat, following the storm of the twelfth. "
    "Relief supplies were dispatched from the provincial depot the same evening."
)
_BODY_CUT = (
    "Governor Ahmed Reshud of Sivas province has ordered the urgent repair "
    "of the flood-damaged bridge at Tokat, following the storm of the twelfth."
)

_INDEPENDENT_ACCOUNTS = [
    "I witnessed the flood myself; the old bridge at Tokat gave way during the "
    "night storm, and the governor, Ahmed Reshid, was on site directing rescue "
    "efforts by dawn.",
    "My uncle wrote from Sivas that the river rose without warning that week "
    "and the stone crossing did not survive it; officials from the capital "
    "arrived within two days to assess the damage.",
    "A grain merchant travelling through Tokat recorded the bridge collapse "
    "in his diary, noting Ahmed Reshid's swift response and the resulting "
    "losses to the local market.",
    "The provincial council's own minutes record storm damage to the Tokat "
    "river crossing and describe the repair contract awarded the following "
    "month under the governor's supervision.",
    "A missionary stationed near Tokat described the flood in a letter home, "
    "remarking on the destroyed crossing and a relief effort organised by "
    "local notables rather than the provincial office.",
    "An army engineer's field notes mention inspecting the collapsed span at "
    "Tokat afterward and recommending a stone replacement instead of the "
    "original timber construction.",
]


def build_reprint_family(repo: DHRARepo) -> dict:
    """Ingests 11 reprint-family items (1 implicit original + 10 further
    reprints, all sharing the garbled 'Reshud') and 6 independent
    accounts (correct spelling, genuinely different wording). Returns
    the item ids grouped by ground-truth category."""
    reprint_ids = []
    for i, lead in enumerate(_LEADS):
        body = _BODY_CUT if i % 4 == 3 else _BODY_FULL  # some reprints cut the last sentence
        item_id, _rep_id = repo.ingest_text(lead + body, source_id=f"newspaper_{i}")
        reprint_ids.append(item_id)

    independent_ids = []
    for i, text in enumerate(_INDEPENDENT_ACCOUNTS):
        item_id, _rep_id = repo.ingest_text(text, source_id=f"eyewitness_{i}")
        independent_ids.append(item_id)

    return {
        "reprint_ids": reprint_ids,
        "independent_ids": independent_ids,
        "all_ids": reprint_ids + independent_ids,
        "expected_witnesses": 1 + len(independent_ids),
    }


# --- Fixture 2: skewed_corpus -------------------------------------------


def build_skewed_corpus(repo: DHRARepo) -> dict:
    """10 items: 7 from one dominant source, dense 1849-51 / thin
    1846-48 dates, no Armenian or Greek despite both being 'expected',
    plus 2 recorded access failures."""
    item_ids = []

    dominant_texts = [
        ("Provincial gazette notice on tax assessment for the district.", 1849),
        ("Provincial gazette notice on road maintenance contracts.", 1850),
        ("Provincial gazette notice on grain price regulation.", 1850),
        ("Provincial gazette notice on the annual census return.", 1851),
        ("Provincial gazette notice on customs house appointments.", 1851),
        ("Provincial gazette notice on the new market regulations.", 1849),
        ("Provincial gazette notice on the harbour repair fund.", 1850),
    ]
    for text, year in dominant_texts:
        item_id, rep_id = repo.ingest_text(text, source_id="dominant_archive")
        repo.add_assertion(
            subject_item_id=item_id,
            predicate="date",
            value=str(year),
            original_expression=f"{year}",
            asserted_by="researcher",
            confidence="stated",
        )
        repo.add_assertion(
            subject_item_id=item_id,
            predicate="language",
            value="ottoman-turkish",
            original_expression="Ottoman Turkish",
            asserted_by="researcher",
            confidence="stated",
        )
        item_ids.append(item_id)

    minor_texts = [
        ("Consular report on shipping traffic through the port.", 1846, "french"),
        ("Traveller's account of the inland road conditions.", 1847, "french"),
        ("Missionary society bulletin on school enrolment.", 1848, "ottoman-turkish"),
    ]
    for text, year, lang in minor_texts:
        item_id, rep_id = repo.ingest_text(text, source_id="minor_archive")
        repo.add_assertion(
            subject_item_id=item_id,
            predicate="date",
            value=str(year),
            original_expression=f"{year}",
            asserted_by="researcher",
            confidence="stated",
        )
        repo.add_assertion(
            subject_item_id=item_id,
            predicate="language",
            value=lang,
            original_expression=lang,
            asserted_by="researcher",
            confidence="stated",
        )
        item_ids.append(item_id)

    repo.record_access_failure(source_id="restricted_archive", reason="access_denied: subscription required")
    repo.record_access_failure(source_id="restricted_archive", reason="rate_limited: daily quota exhausted")

    return {
        "all_ids": item_ids,
        "dominant_source": "dominant_archive",
        "expected_languages": {"ottoman-turkish", "armenian", "greek"},
    }
