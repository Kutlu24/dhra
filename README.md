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

## Status: Phase 1 (Evidence)

Phase 1 implemented per spec section 6 (below). Phase 0 (Foundations) — the
event-sourced store everything else sits on — is unchanged and still
passes its own exit test; see `tests/acceptance/test_phase0.py`.

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

## Not yet built

Phase 2 onward (independence testing/descent clustering, bias report,
disconfirmation search, corpus maps; then the tool layer + MCP; then
drafting/export) — see spec section 6 and the build order in section 17.
All three of Phase 1's own open questions
([`OPEN_QUESTIONS.md`](OPEN_QUESTIONS.md#resolved-1) #6–8) are resolved;
#8 (E3/dependents `needs_review` cascade) is explicitly deferred to be
built *as part of* Phase 2, not before it.
