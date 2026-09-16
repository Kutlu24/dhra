# Open questions (Phase 0)

Per `docs/DHRA_BUILD_SPEC.md` section 0.5/0.6: things noted here rather than
silently decided or silently built beyond spec.

1. **"Active representation" selection rule.** The spec's corpus manifest
   (section 5.2) includes "their active representation ids" per item but
   never defines how the active one is chosen when an item has several
   (e.g. a transcription plus a later translation, or two competing
   transcriptions from different tools). Phase 0 implements the simplest
   possible rule — **most recently created representation for that item**
   (`Projection.active_representation_id`) — purely so the manifest has
   *something* deterministic to hash. This is almost certainly wrong for
   Phase 1 (a translation should not silently become "the" representation
   over its source transcription) and needs a real answer, probably a
   `kind`-scoped notion of "active per kind" plus an explicit
   researcher-settable preference (mirroring `assertion.preference_set`).
   **Ask before Phase 1 retrieval depends on this.**

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
