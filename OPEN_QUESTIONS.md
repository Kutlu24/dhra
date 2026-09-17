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
   as part of that work, not before. **Still not built** — Phase 2
   shipped independence testing, descent clustering, bias reporting and
   disconfirmation search without needing it (see #9 below); it remains
   open for whenever status demotion on a *dependent* claim is actually
   exercised.

# Open questions (Phase 2)

All four resolved 2026-09-17 (AskUserQuestion, before starting Phase 3) —
every one confirmed as-built, no code changes.

## Resolved

9. **Shingle similarity instead of MinHash** (user confirmed: keep
   Jaccard). Section 16 names `datasketch` MinHash for candidate
   generation. `dhra.independence` implements exact Jaccard similarity
   over word 3-shingles instead — no new dependency, exactly
   reproducible, and MinHash's approximation solves a "sketch a huge set
   cheaply" problem this project doesn't have yet at interactive,
   single-researcher corpus sizes. Revisit if candidate-generation cost
   over a large corpus ever actually matters.

10. **Reference lexicon is a placeholder** (user confirmed: keep it for
    now). The shared-error signal (section 7.3, "rare or absent from a
    reference lexicon") uses `independence.COMMON_WORDS`, a ~150-word
    hand-written list, not a real dictionary/frequency list. It correctly
    separates the reprint_family fixture's shared garbled token from
    ordinary shared vocabulary (verified: `tests/acceptance/test_phase2.py`),
    but a real corpus will have rare-but-legitimate words this list
    doesn't know about, risking false shared-error signals. **Revisit
    when real archival material is ingested** (e.g. a MAKHZAN-like
    corpus, or osmanlicagazeteler.org pages) — the right reference
    (which language(s), which period) depends on what that corpus turns
    out to be, so building it now would be guessing.

11. **Disconfirmation queries are caller-supplied, not model-generated**
    (user confirmed: keep as-is, no placeholder negation generator).
    `disconfirm_search()` runs `negated_queries` the caller already
    wrote, the same caller-supplies-the-judgement-call pattern as
    `assess_claim`. Section 10 explicitly allows the model to "propose
    ... disconfirmation strategies" — but there is no LLM-calling layer
    in this repo yet (see #7's same gap for candidate-locator-finding).
    **Needed once Phase 3's tool layer exists** and something is
    actually calling a model; a rule-based negation stopgap now would
    give false confidence without being real disconfirmation.

12. **"Corpus maps" scoped to one aggregate** (user confirmed: keep it
    at one for now). Section 6 lists "corpus maps with drill-down to
    passage" (plural, and section 8.4 names frequency bars, topic
    clusters, network nodes, timeline bands). `dhra.aggregate`
    implements exactly one: `aggregate_by_source`, grouping active items
    by acquisition source, each bucket carrying its `item_ids` for
    drill-down. This satisfies the structural invariant that matters for
    the exit test (a bias report is always attached, every bucket is
    attributable to real items) without building a visualisation layer
    that has no UI to sit in yet. More map types (starting with a
    date/period aggregate — the `skewed_corpus` fixture already has the
    `date` assertions to test it against) are straightforward to add the
    same way once there's a reason (a UI, or a specific research
    question) to render one.

# Open questions (Phase 3)

Not yet put to the researcher — flagged here per section 0 rule 6.

13. **Approvals are event-sourced pre-approval, not MCP's native
    elicitation protocol.** The `mcp` SDK (2.x) has a real mid-call
    interactive-input mechanism (`InputRequiredResult` /
    `ElicitRequest`) that could drive `PermissionClass.ASK` directly
    through the live protocol. `dhra.permissions` instead checks the
    event log for a matching, unconsumed `approval.granted` event before
    an ASK-class tool body runs — simpler to test (no session/transport
    needed, `MCPServer.call_tool` can be exercised directly, as the
    Phase 3 tests do), but means an agent has to be told to call
    `grant_approval` as a separate step rather than the client's own UI
    popping an approval prompt mid-call. Revisit once this actually runs
    behind a live MCP client (Claude Code/Desktop) where elicitation's
    UX would matter.

14. **"MCP clients for external archives" built as one HTTP client
    behind an MCP server, not an MCP-to-MCP client.** Section 6 lists
    "MCP clients for external archives" as separate from "MCP server
    exposing the tool layer." Zenodo has no MCP server of its own to be
    a *client* of, so `dhra.zenodo` is a real HTTP client (`requests`,
    real rate-limited, permission-gated calls to `zenodo.org/api`)
    wrapped as one tool (`request_zenodo_acquisition`) on DHRA's *own*
    MCP server. If a future target archive does expose an MCP server,
    "MCP client" would mean something more literal — the interpretation
    here is specific to Zenodo not having one.

15. **Redistribution restriction is recorded, not yet enforced.**
    `Item.acquisition.redistributable` is set correctly from the source
    registry (verified live against Zenodo — see
    `test_live_zenodo_acquisition_end_to_end`), but nothing reads it yet
    to actually block anything, because export (`dhra.export`) and
    "shared corpora" (section 9.3, Phase 4) don't check it. Needs wiring
    once either of those paths is built, so a non-redistributable item
    can't leak into an export bundle meant for someone else.

16. **Rumi and regnal calendars unsupported.** `dhra.calendar` converts
    Gregorian, Julian and (tabular/civil) Hijri via the `convertdate`
    library — real, tested math, not hand-rolled. Rumi (the Ottoman
    fiscal calendar) and regnal dating need period-specific epoch/
    correction tables this project doesn't have; `convert_date_claim`
    returns those `DateClaim`s unconverted rather than approximating.
    Needed if/when Ottoman fiscal-year-dated material is actually
    ingested.

17. **Zotero interchange is local JSON-shape mapping only.**
    `dhra.interchange.zotero` maps DHRA `Assertion`s to/from Zotero's
    item JSON shape entirely offline — no OAuth, no live sync against
    a researcher's actual Zotero library. That would need credential
    handling this project has no vault/secrets story for yet (see the
    Claude API skill's note on this exact gap for other integrations).
    Fine for now (export a DHRA item as Zotero-shaped JSON, hand it to
    Zotero's own importer); revisit if live two-way sync is wanted.

# Open questions (Phase 4)

18. **"Teaching support" not built at all.** Section 6 lists it as a
    Phase 4 deliverable, but nothing else in the 621-line spec elaborates
    what it concretely means — no data model, no test, no API surface
    entry, no UI requirement mentions it. Building something here would
    be guessing against section 0 rule 4 ("prefer refusing to guessing"),
    not implementing the spec. **Needs a real answer from the
    researcher**: anonymised/synthetic example corpora for classroom use?
    Assignment templates that walk students through the epistemic
    engine? A restricted "training mode" that blocks real acquisition
    (`PermissionClass.ACT`-style hard block on `dhra.zenodo`) so a class
    can't accidentally hit a real archive's rate limit? Left entirely
    unbuilt rather than guessed.

19. **"Shared corpora" has no account/permissions system.**
    `dhra.annotation` makes the event log itself the shared medium (two
    researchers pointing DHRA at the same `store/` directory already see
    each other's annotations) rather than building real multi-user
    accounts/sharing permissions — consistent with Phase 0's #4
    (concurrent writers deferred to "whenever this actually runs behind
    an MCP server" — which now exists, `dhra.mcp_server`, but still
    single-writer-safe only). This is honest for "one researcher's
    laptop, maybe synced" but not for genuine multi-writer concurrent
    use. Needs a real answer (who is "the researcher" when two people's
    clients write to the same store at once?) before this is actually
    shared in the sense the spec probably means.

20. **Monitoring has no scheduler.** `check_monitor`/`check_monitors` are
    plain functions the researcher (or an orchestrator) calls whenever
    they want — deliberately, since a background daemon has nowhere
    honest to live in a local-first, no-institutional-infrastructure
    prototype (section 16). If "monitoring" is meant to mean something
    that runs unattended (a cron job, a scheduled agent run), that is a
    deployment/orchestration decision outside this repo, not something
    `dhra.monitoring` should silently promise it's doing.
