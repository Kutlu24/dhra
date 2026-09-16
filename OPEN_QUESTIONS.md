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

6. **Image OCR backend not wired.** Section 6's Phase 1 ingestion list is
   "PDF/image/text/TEI". Text (`ManualTranscriber`), TEI
   (`TeiTranscriber`), and PDF text-layer extraction (`PdfToTextTranscriber`,
   shelling out to the real, already-installed system `pdftotext`) are
   real and tested. Image ingestion is **not** wired to a real OCR
   backend: this environment has no `tesseract` binary (verified with
   `which tesseract` — not found; `pdftotext` was found and is used for
   real). The `Transcriber` protocol (`dhra.transcribe`) is designed so a
   `TesseractTranscriber` slots in the same way `PdfToTextTranscriber`
   does, once a researcher has Tesseract (or Kraken, per section 16)
   installed. Per section 0 rule 4 ("prefer refusing to guessing"), this
   was left unbuilt rather than faked with mocked OCR output. **Ask the
   researcher whether/when to install Tesseract** before manuscript image
   ingestion (the actual eventual target, per section 16) is needed.

7. **What a "claim" is, structurally.** The spec's epistemic status
   (section 7) is explicitly "assigned per claim, not per document," but
   never defines a `Claim` entity/table — only the `Status` vocabulary
   and assignment rules. **Decision (implementation default, not yet
   confirmed with the researcher): a claim is (claim_id, claim_text) +
   explicit evidence-locator sets the caller already decided on**
   (`DHRARepo.assess_claim(claim_id, claim_text, supporting=[...],
   contradicting=[...], negating=[...])`), persisted as `claim.assessed`
   events. This keeps status assignment pure/deterministic code over
   evidence, matching section 10's rule that the model may never assign
   status or resolve a contradiction itself — but it means nothing here
   currently *finds* candidate supporting/contradicting locators for a
   claim automatically (that would need query expansion + a relevance
   classifier, arguably Phase 1's `/evidence/compare` endpoint, not yet
   built). **Ask before Phase 2** (which needs claims as an input to
   independence testing / disconfirmation search).

8. **E3 (INFERRED) and dependents/`needs_review` cascade not built.**
   Section 7.2 rule 5 ("E3 shows its premises... chains longer than
   three steps are decomposed") and section 5.2 ("any stored claim whose
   supporting items were affected is flagged `needs_review`") describe
   real features. `dhra.status.weakest()` exists as the aggregation
   primitive they'd need, but no `assess_inference()` or dependents graph
   is built yet — deliberately, per rule 5 ("do not add features"): nothing
   in the Phase 1 exit test requires them, and building a half-working
   version now risked being wrong in a way that's expensive to unpick
   later. Needed before Phase 2's "flags dependent interpretations" on
   status demotion (section 7.2 rule 3) is real.
