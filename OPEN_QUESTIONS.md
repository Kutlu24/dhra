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

# Open questions (Phase 1)

All three resolved 2026-09-17 (AskUserQuestion, before starting Phase 2).

## Resolved

6. **Image OCR backend** (user chose "şimdi tesseract kur ve bağla" —
   install and wire it now, rather than deferring). Tesseract 5.3.4 was
   installed by the user (`sudo apt-get install -y tesseract-ocr`, run in
   their own terminal — this session's/harness's non-interactive shell
   cannot supply a sudo password itself, confirmed by two failed
   attempts). `TesseractTranscriber` (`dhra.transcribe`) now shells out
   to the real binary, same pattern as `PdfToTextTranscriber`:
   `producer="tesseract"`, `producer_version` from `tesseract --version`,
   and `Quality.mean_char_confidence` computed from real per-word
   confidences in tesseract's TSV output (documented in `Quality.notes`
   as a word-level approximation, since the CLI doesn't expose true
   per-character confidence). Wired into `DHRARepo.ingest_image()`.
   Tested against a real generated image
   (`tests/fixtures/ocr_sample.png`, regenerable via
   `tests/fixtures/generate_ocr_sample.py`), not a mock. Only `eng`
   language data is installed in this environment — Ottoman/Arabic-script
   manuscript material needs its own trained data (Kraken/Transkribus,
   per section 16) installed separately; that remains unbuilt and is not
   blocking Phase 2.

7. **What a "claim" is, structurally** (user confirmed: keep the current
   implementation). **Decision: a claim is (claim_id, claim_text) +
   explicit evidence-locator sets the caller already decided on**
   (`DHRARepo.assess_claim(claim_id, claim_text, supporting=[...],
   contradicting=[...], negating=[...])`), persisted as `claim.assessed`
   events. Phase 2's independence-testing/descent-clustering pipeline
   will call this with the locators it finds — no structural change
   needed. Still true: nothing here *finds* candidate locators for a
   claim automatically; that stays out of scope (query expansion + a
   relevance classifier would be needed, and the model still may never
   assign status itself, per section 10).

8. **E3 (INFERRED) and dependents/`needs_review` cascade** (user
   confirmed: build during Phase 2, when the independence-testing/status-
   demotion scenario that actually needs it exists, rather than
   pre-building a version now that risks being wrong in a way that's
   expensive to unpick). `dhra.status.weakest()` exists as the
   aggregation primitive it will need. Blocks Phase 2's "flags dependent
   interpretations" on status demotion (section 7.2 rule 3) — build it
   as part of that work, not before.
