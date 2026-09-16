# Open questions (Phase 0)

Per `docs/DHRA_BUILD_SPEC.md` section 0.5/0.6: things noted here rather than
silently decided or silently built beyond spec. All five Phase 0 questions
are now resolved (2026-09-16, AskUserQuestion) — kept here as the record of
*why* the code looks the way it does, not as a TODO list.

## Resolved

1. **"Active representation" selection rule** (user chose "hepsi active,
   seçim retrieval'a bırakılsın"). The spec's corpus manifest (section 5.2)
   includes representation ids per item but never defines how one is
   chosen when an item has several (e.g. a transcription plus a later
   translation, or two competing transcriptions from different tools).
   **Decision: no single "active" representation at the corpus-versioning
   layer.** Every representation of every included item is part of the
   corpus version (`CorpusVersion.rep_ids`,
   `Projection.representation_ids_for`); which one a given retrieval
   prefers for a given purpose is entirely a Phase 1 retrieval/ranking
   decision, out of scope for `dhra.corpus`. Implemented in
   `corpus_version_from_projection` — no per-item collapsing happens
   before Phase 1 exists to make that call correctly.

2. **`Locator.resolve()` call shape** (user confirmed the current
   implementation). The spec sketches it as a parameterless bound method
   (section 4.6), but `Locator` is a frozen dataclass with no honest way
   to reach the store. **Decision: keep `DHRARepo.resolve(locator)`** as
   a free function on the repo rather than adding a store reference or
   injected resolver to `Locator` itself — `Locator` stays pure data, and
   the `/evidence/locator/{...}` endpoint (section 11.2) will call this
   the same way regardless.

3. **ULID generation** (user confirmed the current implementation).
   **Decision: keep `dhra.ulid.new_ulid()`**, a minimal stdlib-only
   approximation (48-bit ms timestamp + 80 bits random, Crockford
   base32) rather than adding the `python-ulid` dependency — no
   zero-dependency, local-first cost, and nothing in Phase 0/1 needs
   strict same-millisecond monotonic ordering.

4. **Concurrent writers** (user confirmed the current implementation).
   **Decision: leave `EventLog.append` single-process thread-safe only**
   (a lock, not a file lock) and defer real concurrency protection to
   Phase 3 (MCP server), matching the spec's own stated scope. Revisit
   if Phase 1/2 work ever runs two processes against the same store
   before Phase 3 exists.

5. **"Currently active" field in the exclusions export** (user confirmed
   the current implementation). **Decision: keep** the `currently_active`
   flag on each historical exclusion record in `exclusions.jsonl`, even
   though the spec's manifest only requires the *active* exclusion set
   (section 4.7/5.2) — it lets a researcher audit the full reversal
   history from the export alone, without needing `events.jsonl`. Treated
   as a harmless superset of what was asked for, not a violation of
   "do not add features" (section 0.5).
