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

## Status: Phase 0 (Foundations)

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
pytest
```

## Not yet built

Everything from Phase 1 onward (evidence/retrieval, the epistemic engine,
critique/independence testing, the tool layer + MCP, drafting/export) —
see spec section 6 and the build order in section 17. Do not start Phase 1
until the Phase 0 exit test above is the thing being trusted, not just
passing once.
