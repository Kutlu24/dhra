# Open questions (Phase 0)

Per `docs/DHRA_BUILD_SPEC.md` section 0.5/0.6: things noted here rather than
silently decided or silently built beyond spec.

## Resolved

1. **"Active representation" selection rule** (asked 2026-09-16, user chose
   "hepsi active, seçim retrieval'a bırakılsın"). The spec's corpus
   manifest (section 5.2) includes representation ids per item but never
   defines how one is chosen when an item has several (e.g. a
   transcription plus a later translation, or two competing
   transcriptions from different tools). **Decision: no single "active"
   representation at the corpus-versioning layer.** Every representation
   of every included item is part of the corpus version
   (`CorpusVersion.rep_ids`, `Projection.representation_ids_for`); which
   one a given retrieval prefers for a given purpose is entirely a
   Phase 1 retrieval/ranking decision, out of scope for `dhra.corpus`.
   Implemented in `corpus_version_from_projection` — no per-item
   collapsing happens before Phase 1 exists to make that call correctly.

## Open

2. **`Locator.resolve()`.** The spec sketches it as a bound method
   (`section 4.6`). Implemented instead as `DHRARepo.resolve(locator)`,
   since a frozen dataclass has no honest way to reach the store. Same
   behaviour, different call shape — flagging in case the API surface
   (section 11) is expected to expose `Locator.resolve` directly.

3. **ULID generation.** `dhra.ulid.new_ulid()` is a minimal stdlib-only
   approximation (48-bit ms timestamp + 80 bits random, Crockford
   base32), not the `python-ulid` package. Fine for Phase 0 (ids only
   need to be unique strings); revisit if anything later depends on
   strict ULID monotonic sort order within the same millisecond.

4. **Concurrent writers.** `EventLog.append` is single-process thread-safe
   only (a lock, not a file lock). Multiple agent processes writing to
   the same `events.jsonl` is explicitly a Phase 3 concern (MCP server
   concurrency) per the spec's own scope, not addressed here.

5. **"Currently active" exclusion note in the export.** `exclusions.jsonl`
   includes a `currently_active` flag per historical exclusion (spec only
   requires the manifest's *active* exclusion set, section 4.7/5.2). Kept
   because it lets a researcher audit the full reversal history from the
   export alone without needing `events.jsonl` — a superset of what was
   asked for, not a substitute. Flagging per rule 5 ("do not add
   features") in case it should be trimmed.
