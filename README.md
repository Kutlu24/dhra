# DHRA — Digital Humanities Research Agent

Local-first research system: assemble a corpus from heterogeneous sources,
retrieve evidence with full provenance, assess how strongly that evidence
supports a claim, and export a citable record of how it was all done.

Full spec: [`docs/DHRA_BUILD_SPEC.md`](docs/DHRA_BUILD_SPEC.md) (binding
unless shown wrong). Open design questions not yet resolved:
[`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md).

**The one-sentence test for every decision:** the system exists to make the
path from source to claim shorter to travel and easier to audit — never
shorter to travel at the cost of being harder to audit.

## Status: Phase 4 (Practice) — all four spec phases now implemented

Phase 4 implemented per spec section 6 (below). Phases 0-3 are unchanged
and still pass their own exit tests. This is the spec's last phase
(section 17's build order ends here); what's left is the open questions
in [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md), not another phase.

- `src/dhra/methods_export.py` + `dhra.export`'s `methods_statement.json`
  — section 11.4's methods export, assembled entirely from real
  event-log state: corpus version/hash, acquisition sources with
  dates/access/licence, the transformation chain with tool versions,
  selection-criteria counts, exclusion summary by reason, the full query
  set actually run (`DHRARepo.log_tool_invocation`, now wired into
  `evidence.search`), model identities/versions/purposes (real, and
  truthfully empty — no LLM-calling layer exists yet), and limitations
  drawn from the bias report. Included in every `export_corpus()` bundle
  and read back by `reconstruct_from_export()`, same stdlib-only
  reconstruction path as everything else (I12).
- `src/dhra/drafting.py` — drafting under approval (`PermissionClass.PREPARE`):
  create/approve/reject, ephemeral and non-reproducible (section 10.2).
  No send/submit/publish function exists anywhere in the module — section
  15's anti-requirement ("automatic sending, submitting or publishing of
  anything") holds structurally, not just by convention, and is checked
  as such in the tests.
- `src/dhra/annotation.py` — comment threads on any target (item, claim,
  ...), addition/resolution as events. "Shared" means what local-first
  actually gives for free (the event log is the shared medium) — no
  account/permissions system; see
  [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#open-questions-phase-4) #19.
- `src/dhra/monitoring.py` — saved queries, re-run on demand
  (`check_monitor`/`check_monitors`), reporting only genuinely new
  matches since the last check. No scheduler/daemon (#20) — there is
  nowhere honest for one to live in a local-first prototype.
- **Not built: "teaching support"** (#18) — the spec names it as a Phase
  4 deliverable but never elaborates what it means anywhere else in the
  document; guessing at a data model/UI for it would violate section 0
  rule 4 ("prefer refusing to guessing"). Needs a real answer from the
  researcher.

**Exit test** (`tests/acceptance/test_phase4.py`): "a generated methods
statement contains everything Section 11.4 requires and round-trips
through the export test" — verified field-by-field against a realistic
seeded corpus (two sources, one excluded item, one access failure, two
real queries run), and verified to survive `export_corpus` →
`reconstruct_from_export` with matching `corpus_version` and a clean
checksum/manifest-hash pass.

```bash
pip install -e ".[dev]"
pytest tests/acceptance/test_phase4.py
```

## Web UI

Section 12's UI requirements, actually enforced (`tests/acceptance/test_web.py`
checks against a live `TestClient`, not just that routes exist):
evidence always renders above narrative and narrative never renders without
it; epistemic status is always a hover-tooltipped code (`E1`..`E8`), never a
bare number, anywhere; the bias report is part of the same response as
aggregate buckets, so it cannot be skipped; exclusions are grouped by reason
with one-click restore; there is no delete route anywhere in the app
(checked against the live route table, section 15). Server-rendered Jinja2 +
vanilla JS, no frontend framework (section 16).

```bash
pip install -e ".[dev]"
dhra web --store path/to/store --port 8420
# then open http://127.0.0.1:8420
```

Covers search, locator/provenance detail (with inline image display and
annotation threads), claim assessment (a plain-text `item_id,rep_id,start,end`
per line for evidence locators — a real, working v1, not yet a
click-to-select UI), exclusions, the source aggregate + bias report, and the
decision trace, plus an in-app `/tutorial` walkthrough pairing every feature
with its terminal equivalent. Not built: a UI for triggering `dhra.zenodo`
acquisitions (the MCP server already covers agent-driven acquisition; a
human "approve this request" button is future work), and there is no
account/session system — same caveat as `dhra.annotation`'s "the event log
is the shared medium" (OPEN_QUESTIONS.md #19).

## Terminal interface

Everything the web UI does, scriptable, against the same store
(`--store`, or `DHRA_STORE_DIR`):

```bash
dhra search "your query"
dhra ingest --source-id "my_archive" --text "..."
dhra claims assess my-claim --text "..." --supporting item_id,rep_id,start,end
dhra aggregate
dhra exclusions list
dhra trace
```

## Research-assistant features (LLM-backed)

`dhra.research_assistant`, `dhra.teaching`, `dhra.peer_review` — built
2026-09-18 after a real discussion among historians (Adrian, Tobias Hodel
and others) about what they'd want from an "agentic AI", mapped onto
DHRA's existing design. The model (GLM, OpenAI-compatible, meant to be
self-hosted on university infrastructure — `dhra.llm`) only ever
*proposes*; deterministic code still does the real work and every call
is logged (`model.invoked` events, feeding the methods export):

- **`suggest_research_questions`** — runs a real `evidence.search()`,
  shows the model only those real excerpts, stores its suggestions as a
  reviewable `Draft`. Refuses to run with no evidence to reason from.
- **`draft_exam_questions` / `assess_paper_against_rubric`** — exam
  question drafts and a first-pass, per-criterion rubric reading (never
  a grade) from course material, both `PermissionClass.PREPARE` drafts
  for the instructor to approve or edit.
- **`review_paper`** — extracts candidate claims from a paper (a
  proposal) and finds real candidate evidence for each via literal
  corpus search (deterministic) — never assigns an epistemic status
  itself; that stays a separate, manual `assess_claim` step, per section
  10's boundary.

No real GLM endpoint exists yet to call (Adrian's hosting is still
pending) — `dhra.llm.LLMClient` is tested against the real
OpenAI-compatible request/response shape via a fake session, not a live
endpoint; see [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#open-questions-llm-features--dhrallm-research_assistant-teaching-peer_review)
#24. None of these three modules are wired into the CLI/web UI/MCP
server yet (#27) — real credentials first.

## Phase 3 (Environment)

Phases 0-3's own sections below are unchanged from before Phase 4.

- `src/dhra/permissions.py` — `PermissionClass` (READ/PREPARE/ASK/ACT,
  section 9.1), `ApprovalRequired` carrying exact specifics (not "access
  external archive?" but the real summary), and event-sourced
  pre-approval (`approval.granted`/`approval.consumed`/`approval.denied`
  events) rather than MCP's native elicitation protocol — see
  [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#open-questions-phase-3) #13.
- `src/dhra/source_registry.py` + [`config/sources.yaml`](config/sources.yaml)
  — real registry entry for Zenodo, in the spec's own YAML shape,
  including its actually-published rate limit (60 req/min, verified
  against `developers.zenodo.org` on 2026-09-17).
- `src/dhra/rate_limit.py` — a hard, blocking sliding-window limiter
  (`test_rate_limit_hard`, section 13.3): it raises, it does not warn
  and proceed.
- `src/dhra/zenodo.py` — real HTTP client (`requests`) for the Zenodo
  API, rate-limited and identified (`User-Agent`) on every call,
  wrapped as one `PermissionClass.ASK` tool
  (`acquire_from_zenodo`/`request_zenodo_acquisition`) that records
  every licence constraint on the resulting `Item` (I11) — never
  assumed from the registry alone.
- `src/dhra/mcp_server.py` — the tool layer exposed over the real `mcp`
  SDK (`mcp.server.mcpserver.MCPServer`; note the v1→v2 `FastMCP`
  rename, see the module docstring): `search_evidence`,
  `get_corpus_version`, `request_zenodo_acquisition`, `grant_approval`,
  `deny_approval`.
- `src/dhra/calendar.py` — real Gregorian/Julian/Hijri conversion via
  the `convertdate` library (not hand-rolled arithmetic), day/month/year
  precision producing either `converted_iso` or a `range_start`/
  `range_end` pair, never a bare ISO date from partial precision.
  Rumi/regnal calendars are left unconverted (no lookup tables yet).
- `src/dhra/interchange/` — `tei.py` (export, completing the round trip
  with `dhra.transcribe.TeiTranscriber`'s import direction) and
  `zotero.py` (export/import against Zotero's item JSON shape, offline —
  no live API sync).
- `src/dhra/evidence.py` — `search(..., variants=[...])`: orthographic
  variant expansion, caller-supplied, shown via
  `Response.variant_expansion` (never silent), each matching passage's
  rationale naming which spelling actually matched (section 8.2's own
  example, almost verbatim: "matched via orthographic variant 'shewed'").

**Exit test** (`tests/acceptance/test_phase3.py`): "a real acquisition
run against a real archive completes within published rate limits, with
permission checkpoints honoured and every licence constraint recorded
per item" — `test_live_zenodo_acquisition_end_to_end` (skipped by
default; network/external-service dependent) was run for real against
the live Zenodo API on 2026-09-17 and passed: real record
`10.5281/zenodo.6164620`, real `cc-by-4.0` licence recorded, approval
checkpoint actually enforced first. Run it yourself with:

```bash
pip install -e ".[dev]"
DHRA_LIVE_NETWORK_TESTS=1 pytest tests/acceptance/test_phase3.py -k live -v
```

Everything else in `test_phase3.py` (permissions, rate limiting,
calendar math, interchange, MCP tool wiring) runs by default, no network
needed.

```bash
pytest tests/acceptance/test_phase3.py
```

## Phase 2 (Critique)

Phases 0-2's own sections below are unchanged from before Phase 3.

- `src/dhra/independence.py` — the independence engine (section 7.3):
  recall-oriented candidate grouping (exact Jaccard over word 3-shingles,
  not MinHash — see [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#open-questions-phase-2)
  #9), pairwise alignment (stdlib `difflib`), descent signal extraction
  (shared rare/error tokens — section 7.3's "single strongest available
  signal" — plus shared idiosyncratic phrasing), union-find cluster
  formation, and the three-way verdict
  (`INDEPENDENT`/`SHARED_DESCENT`/`UNDETERMINED`). `dedupe_by_descent()`
  is the "37 passages, 11 share a descent, count as one" collapse
  (section 18).
- `src/dhra/status.py` — extended: `assess_claim(independence_confirmed=...)`
  is the only path to `Status.CORROBORATED` (E2), and it's only ever set
  by `DHRARepo.assess_claim_with_independence()`, which actually ran the
  descent-clustering pipeline first. I6 now holds by *proof*, not by
  omission.
- `src/dhra/repo.py` — `assess_claim_with_independence()`: runs descent
  clustering over a claim's supporting locators, excludes
  non-representative cluster members reversibly
  (`ExclusionReason.DESCENT_CLUSTER_MEMBER`), collapses the supporting
  set, and only claims E2 when every remaining distinct-item pair was
  actually verdicted independent. `record_access_failure()`: a source
  that was tried and refused/failed is itself now an event (section
  9.2/11.4), feeding the bias report below.
- `src/dhra/bias.py` — `compute_bias_report()`: source concentration,
  period coverage gaps, expected-but-absent languages, and access
  failures, each a real, computed warning over the projection.
- `src/dhra/aggregate.py` — `aggregate_by_source()`: one real, drillable
  corpus map (items grouped by acquisition source, each bucket carrying
  its `item_ids`), with a `BiasReport` as a **mandatory** field of the
  response — there is no code path that returns aggregate data without
  one, which is how "shown *before* first aggregate results" (section
  12) is enforced without a UI/session layer to sequence it in yet.
- `src/dhra/disconfirm.py` — `disconfirm_search()`: runs
  caller-supplied refutation-oriented queries through the real search
  pipeline and reports whether anything refuting turned up. Query
  *generation* is explicitly the model's job (section 10) and isn't
  built here yet — same gap as claim-evidence-finding in
  [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#open-questions-phase-2) #11.

**Exit test** (`tests/acceptance/test_phase2.py`): the seeded
`reprint_family` fixture (17 items: 11 reprints of one wire dispatch
sharing one garbled proper noun, plus 6 genuinely independent accounts)
collapses to exactly 7 witnesses, with the shared-error signal — the
actual garbled token — cited as the cluster's basis; the `skewed_corpus`
fixture (dominant source, uneven period coverage, an entirely absent
expected language, 2 access failures) produces a bias report carrying
all four findings as a mandatory part of the same response as the
aggregate data, never as a separate, skippable step. Plus E2 shown
reachable end-to-end (two genuinely independent accounts corroborate a
claim) and confirmed unreachable for the reprint family alone (collapses
to E5, not E2 — the whole point of the fixture).

```bash
pip install -e ".[dev]"
pytest tests/acceptance/test_phase2.py
```

## Phase 1 (Evidence)

- `src/dhra/transcribe.py` — pluggable `Transcriber` protocol. Real,
  working backends: `ManualTranscriber` (text), `TeiTranscriber` (TEI
  XML, stdlib `xml.etree`), `PdfToTextTranscriber` (shells out to the
  real system `pdftotext`), `TesseractTranscriber` (shells out to the
  real system `tesseract`, including real per-word confidence scoring).
  Only `eng` language data is installed — Ottoman/Arabic-script
  manuscript OCR needs its own trained data (Kraken/Transkribus, per
  section 16), not yet installed; see
  [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#resolved-1) #6.
- `src/dhra/index.py` — literal, case-insensitive full-text search over
  representations via SQLite FTS5, rebuilt from the projection on every
  query (disposable, like `derived.db`). No orthographic variant
  expansion (section 8.2 is Phase 3 per the spec's own build order).
- `src/dhra/evidence.py` — `search()`: turns index hits into
  locator-bound `Passage`s with a stated rationale (section 8.1); a
  zero-hit result is qualified by the legibility of what was searched
  (mean character confidence, unreadable/below-quality exclusion counts)
  rather than an unqualified "no mentions found" (section 8.3).
- `src/dhra/response.py` — the two-channel `Response` contract (section
  10.1): `narrative` is rejected when `evidence` is empty (I10); every
  `Passage` is verbatim-checked against its stored representation before
  the response is built, raising (not warning) on mismatch (I2).
- `src/dhra/status.py` — the epistemic engine (section 7): `Status`
  E1–E8, `assess_claim()` (pure function, evidence sets → status — the
  model never assigns status itself, per section 10), the E6
  not-rendered-as-denial linter (I7), and a monotonicity guard rejecting
  a status rise unless the evidence set actually grew (rule 2). E2
  (CORROBORATED) is structurally unreachable in Phase 1 — there is no
  independence engine yet (that's Phase 2), so I6 holds by omission, not
  by a stub.
- `src/dhra/repo.py` — extended with `ingest_text`/`ingest_pdf`/
  `ingest_tei` (acquire + transcribe in one call) and
  `assess_claim`/`get_claim_assessment`/`claim_history`.

**Exit test** (`tests/acceptance/test_phase1.py`): traceability and
quotation fidelity both 100% across an adversarial text battery (smart
quotes, ligatures, soft hyphens, combining diacritics, RTL Arabic script);
absence-discipline passes (quality-qualified, non-denial E6). Plus the
section 13.2 claim-status tests that don't need Phase 2 (monotonicity,
demotion-on-contradiction, E2 unreachable) and real PDF/TEI ingestion
tests (`pdftotext` actually invoked, not mocked).

```bash
pip install -e ".[dev]"
pytest
```

## Phase 0 (Foundations)

Implemented per spec section 6:

- `src/dhra/models.py` — core entities (`Item`, `Acquisition`,
  `Representation`, `Quality`, `Assertion`, `DateClaim`, `Locator`,
  `ExclusionReason`) as frozen dataclasses. Nothing here is ever mutated
  in place.
- `src/dhra/store/blobs.py` — content-addressed, immutable blob store
  (I3, I4).
- `src/dhra/store/events.py` — append-only `events.jsonl`, the source of
  truth (section 5.1). No state change happens any other way.
- `src/dhra/store/projection.py` — `fold()`: pure replay of events into an
  in-memory `Projection`, plus `materialise_sqlite()` to build a disposable
  `derived.db` from it.
- `src/dhra/corpus.py` — `corpus_version_at(seq)`: immutable, hashed corpus
  manifests (I8). No single "active" representation per item — every
  representation of an included item is part of the corpus version;
  Phase 1 retrieval picks among them per query (resolved in
  [`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#resolved)).
- `src/dhra/trace.py` — the three-level activity trace (section 11.3).
- `src/dhra/export.py` — `export_corpus()` writes a self-describing,
  flat export; `reconstruct_from_export()` rebuilds state from it using
  **only stdlib**, no `dhra.models`/`dhra.store` imports, to actually
  demonstrate I12 ("reconstructable from the export alone").
- `src/dhra/repo.py` — `DHRARepo`, the ergonomic façade over the above
  (one method per event type) that tests and future phases call.

**Exit test** (`tests/acceptance/test_phase0.py`,
`test_phase0_exit_rebuild_from_events_and_export`): delete `derived.db`,
rebuild it by replaying `events.jsonl`; reconstruct an earlier corpus
version exactly (including an exclusion made at that point) despite later
events; export that version to a fresh directory and reconstruct it there
with a stdlib-only reconstructor. Plus the rest of the section 13.1/13.3
battery that is meaningfully testable before Phase 1 exists (exclusion
reversibility, version reconstruction, projection-rebuild determinism,
`DateClaim` rejecting a bare ISO date, mandatory `producer_version`,
walkable representation chains, `Locator` resolving-or-raising).

```bash
pip install -e ".[dev]"
pytest tests/acceptance/test_phase0.py
```

## What's left

All four spec phases (section 17's build order) are implemented. What
remains is the open-questions list in
[`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md) — 20 items across the four
phases, all but one (#18, "teaching support") a real, working default
that was either confirmed with the researcher or reasoned and recorded
rather than silently assumed. The ones most worth reading before relying
on this against real archival material:

- **#18** — "teaching support" (Phase 4) isn't built at all; the spec
  never says what it means.
- **#15** — redistribution restriction is recorded on every `Item` but
  nothing reads it yet, because nothing has needed to share/export to
  a third party for real yet.
- **#10** — the shared-error reference lexicon is a ~150-word
  placeholder; matters once this runs against a real corpus.
- **#19** — "shared corpora" has no account/permissions system, only
  "the event log is the shared medium."
- **#8** — status demotion doesn't yet flag dependent claims as
  `needs_review`.
