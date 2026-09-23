# Digital Humanities Research Assistant — Build Specification

**For: Claude Code**
**Companion to:** *The Digital Humanities Research Assistant — Concept Paper v2.0*
**Status:** implementation brief. Everything here is binding unless you can show it is wrong.

---

## 0. Working agreement

Read this section before writing code.

1. **Build in the stated phase order.** The order is deliberate and differs from the intuitive one. Provenance and versioning come *before* retrieval, because they cannot be retrofitted. Critique (independence testing, bias reporting) comes *before* external connectors, because a system that acquires widely before it can assess independence produces confident nonsense at scale.
2. **Write the invariant tests first.** Section 2 lists twelve invariants. Before implementing a phase, write its acceptance tests (Section 13) as failing tests. A phase is not done when the features exist; it is done when its exit test passes.
3. **The model proposes; deterministic code verifies.** Anywhere a language model produces something that will be presented as evidence, a non-model code path must validate it against stored data. If validation fails, the response fails — it does not degrade gracefully into prose.
4. **Prefer refusing to guessing.** When the system cannot determine something (independence, a date, a transcription), the correct output is an explicit "undetermined" with a reason, never a best approximation. This applies to your code and to the agent's behaviour.
5. **Do not add features.** This spec is already large. If something seems missing, note it in `OPEN_QUESTIONS.md` rather than building it.
6. **Ask before ambiguity becomes architecture.** If a design decision here is underspecified and the choice is load-bearing, stop and ask rather than picking one silently.

---

## 1. What you are building

A local-first research system that helps a humanities researcher assemble a corpus from heterogeneous sources, retrieve evidence from it with full provenance, assess how strongly that evidence supports a claim, and export a citable record of how the whole thing was done.

**The one-sentence test for every decision:**

> The system exists to make the path from source to claim shorter to travel and easier to audit — never shorter to travel at the cost of being harder to audit.

**Non-goals.** This is not a question-answering service, not a writing tool that produces historical prose, not a plagiarism detector, and not an authority. Answers are a by-product; evidence is the product.

---

## 2. Non-negotiable invariants

These are testable properties of the running system, not aspirations. Each maps to an acceptance test in Section 13.

| # | Invariant | Enforced by |
|---|---|---|
| I1 | No evidentiary statement is ever emitted without a locator that resolves in one call. | Type system + response validator |
| I2 | Every displayed quotation matches the stored representation byte for byte. | Pre-display verbatim check |
| I3 | The original bitstream of every acquired item is preserved unmodified and checksummed. | Content-addressed blob store |
| I4 | No item is ever deleted by the system. Exclusion is a reversible annotation. | No DELETE path on items |
| I5 | Every exclusion carries a reason from a closed vocabulary and is reversible in one action. | Exclusion table + enum |
| I6 | Corroboration (E2) is never assigned without a passed independence check. | Epistemic engine |
| I7 | "Not found" is never rendered, phrased or summarised as "did not happen". | Status enum + output linting |
| I8 | Every claim is indexed to a corpus version that can be reconstructed exactly. | Event log + immutable manifests |
| I9 | Normalisation (orthography, dates, entities) never alters displayed text. | Separate index vs. display paths |
| I10 | Generated prose cannot render without its supporting passages in the same payload. | Two-channel response contract |
| I11 | Licence and rate-limit constraints are enforced at the tool layer, not by convention. | Source registry + executor |
| I12 | The corpus and its record are fully reconstructable from the export alone, without this software. | Export round-trip test |

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────┐
│  UI  — evidence-first, two-channel, drillable aggregates  │
└────────────────────────┬─────────────────────────────────┘
                         │  HTTP/JSON
┌────────────────────────▼─────────────────────────────────┐
│  RESPONSE CONTRACT  — evidence channel (validated)        │
│                       narrative channel (ephemeral)       │
├──────────────────────────────────────────────────────────┤
│  AGENT ORCHESTRATOR  — plans, calls tools, logs decisions │
├──────────────────────────────────────────────────────────┤
│  TOOL LAYER  — permission classes, licence + rate limits  │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ CORPUS   │ EVIDENCE │ EPISTEMIC│ CRITIQUE │ WORKFLOW     │
│ acquire  │ search   │ status   │ bias     │ monitor      │
│ ingest   │ passage  │ indep.   │ disconf. │ draft        │
│ transform│ compare  │ inference│ maps     │ export       │
├──────────┴──────────┴──────────┴──────────┴──────────────┤
│  STORE                                                    │
│  blobs/ (content-addressed, immutable)                    │
│  events.jsonl (append-only, the source of truth)          │
│  derived.db (SQLite projection, rebuildable from events)  │
│  index/ (search index, rebuildable)                       │
└──────────────────────────────────────────────────────────┘
```

**Critical structural point:** `events.jsonl` is the source of truth. `derived.db` and `index/` are *projections* that can be deleted and rebuilt by replaying events. Build the replay path in Phase 0 and test it — if state can only live in SQLite, I8 and I12 are unachievable.

---

## 4. Data model

### 4.1 Blob store

Content-addressed. Path: `blobs/<sha256[0:2]>/<sha256>`. Written once, never modified, never deleted. Every acquisition writes the bytes exactly as received before anything else happens.

### 4.2 Core entities

```python
@dataclass(frozen=True)
class Item:
    item_id: str              # ULID
    blob_sha256: str
    media_type: str
    byte_length: int
    acquisition: Acquisition

@dataclass(frozen=True)
class Acquisition:
    source_id: str            # FK -> SourceRegistry
    retrieved_at: datetime
    method: str               # "api" | "download" | "manual_upload" | "mcp"
    request: dict | None      # exact parameters used
    access_basis: str         # "public_domain" | "licensed" | "tdm_exception" | "permission" | "unknown"
    licence_id: str | None
    redistributable: bool | None   # None = unknown, and unknown is not permission
    original_reference: str | None # shelfmark, URL, call number
```

### 4.3 Representations — the transformation chain

A `Representation` is any derived form of a blob. Everything the researcher reads is a representation, never the blob itself.

```python
@dataclass(frozen=True)
class Representation:
    rep_id: str
    item_id: str
    parent_rep_id: str | None      # None = derived directly from blob
    kind: str                      # "transcription" | "translation" | "normalisation" | "segmentation"
    producer: str                  # tool name
    producer_version: str          # REQUIRED — pinned
    parameters: dict
    created_at: datetime
    text: str                      # the actual content
    quality: Quality | None

@dataclass(frozen=True)
class Quality:
    mean_char_confidence: float | None   # 0..1
    per_span_confidence: list[tuple[int, int, float]]  # (start, end, conf)
    script: str | None                   # "latin" | "fraktur" | "arabic" | ...
    manually_corrected: bool
    notes: str | None
```

**Rules.** Transformations always produce a new representation; they never mutate an existing one. The chain from any representation back to the blob must be walkable. `producer_version` is mandatory — an unversioned transformation is not reproducible and must be rejected at write time.

### 4.4 Assertions — metadata as testimony, not fact

This is the part most likely to be simplified by mistake. **Do not create a `documents` table with `title`, `author`, `date` columns.** Catalogue metadata is a claim made by a cataloguer under a particular scheme at a particular time, and two catalogues may disagree about the same object.

```python
@dataclass(frozen=True)
class Assertion:
    assertion_id: str
    subject_item_id: str
    predicate: str            # "title" | "creator" | "date" | "place" | "genre" | "language"
    value: str                # normalised value, for indexing
    original_expression: str  # exactly as it appeared in the source
    asserted_by: str          # "catalogue:BL" | "researcher" | "tool:date_parser@1.2"
    asserted_at: datetime
    confidence: str           # "stated" | "inferred" | "uncertain"
    evidence_locator: Locator | None
```

Conflicting assertions coexist. The API returns all of them with their sources; the UI shows disagreement rather than resolving it. A "preferred" assertion may be selected by the researcher, and that selection is itself an event.

### 4.5 Dates

Dates get their own treatment because they carry an unusual density of silent error.

```python
@dataclass(frozen=True)
class DateClaim:
    original_expression: str       # "12 Rebiülevvel 1265"
    calendar: str                  # "gregorian"|"julian"|"hijri"|"rumi"|"regnal"|"french_republican"|"unknown"
    converted_iso: str | None      # only if conversion is defensible
    conversion_method: str | None
    precision: str                 # "day"|"month"|"year"|"decade"|"range"|"terminus_ante_quem"|...
    range_start: str | None
    range_end: str | None
    asserted_by: str
```

**Never store a bare ISO date.** A chronological analysis built on silently converted dates is an analysis of the conversion. When the calendar is unknown, `converted_iso` is `None` and the item is excluded from temporal aggregates with reason `date_unresolved` — which is reported, not hidden.

### 4.6 Locators

```python
@dataclass(frozen=True)
class Locator:
    item_id: str
    rep_id: str               # WHICH representation — a locator into a translation is not a locator into the source
    start: int                # character offset in rep.text
    end: int
    page: str | None
    iiif_region: str | None
    def resolve(self) -> ResolvedPassage: ...
```

A `Locator` that does not resolve is a bug, not a degraded result. Add a startup integrity check that samples locators and verifies resolution.

### 4.7 Exclusions

```python
class ExclusionReason(StrEnum):
    OUT_OF_DATE_RANGE     = "out_of_date_range"
    WRONG_LANGUAGE        = "wrong_language"
    DESCENT_CLUSTER_MEMBER= "descent_cluster_member"
    BELOW_RELEVANCE       = "below_relevance_threshold"
    ACCESS_DENIED         = "access_denied"
    FORMAT_UNREADABLE     = "format_unreadable"
    BELOW_QUALITY         = "below_quality_threshold"
    DATE_UNRESOLVED       = "date_unresolved"
    RESEARCHER_EXCLUDED   = "researcher_excluded"
```

Closed vocabulary, deliberately. Free-text reasons cannot be aggregated, and the aggregate is the diagnostic output: *"412 items excluded as format_unreadable"* is a finding about the corpus, not a log line. Every exclusion records actor, timestamp, threshold value where applicable, and is reversed by a single `restore_item` call that emits a compensating event.

---

## 5. The event log and corpus versioning

### 5.1 Events

Append-only JSONL. Every state change is an event. No state change happens any other way.

```json
{"seq": 1041, "ts": "2026-09-16T10:31:02Z", "type": "item.acquired",
 "actor": "agent", "item_id": "01J...", "source_id": "bl_newspapers",
 "blob_sha256": "9f2c...", "approval_event": 1039}
{"seq": 1042, "ts": "...", "type": "item.excluded",
 "actor": "agent", "item_id": "01J...", "reason": "below_quality_threshold",
 "threshold": 0.55, "observed": 0.41, "reversible": true}
{"seq": 1043, "ts": "...", "type": "model.invoked",
 "model": "claude-sonnet-4-6", "purpose": "query_expansion",
 "prompt_sha256": "...", "temperature": 0.0}
```

Every `model.invoked` event records model identity, version, purpose, prompt hash and parameters. This is what makes the disclosure in the methods statement honest.

### 5.2 Corpus versions

A corpus version is an immutable manifest: the set of included item ids, their active representation ids, the active exclusion set, and the assertion-preference set. Its id is the hash of the manifest.

```python
def corpus_version_at(seq: int) -> CorpusVersion:
    """Fold events up to seq into a manifest. Pure function. No I/O beyond the log."""
```

Every search result, aggregate, chart, claim and export records the corpus version it was computed against. When a new event changes the corpus, any stored claim whose supporting items were affected is flagged `needs_review` — not silently invalidated, not silently kept.

---

## 6. Phases

Each phase ends with a test, not a date. Do not start the next phase until the exit test passes.

### Phase 0 — Foundations
Blob store, event log, replay/projection, representations with transformation chains, assertions, dates, exclusions, corpus versioning, three-level activity trace, export.

**Exit test:** Delete `derived.db` and `index/`, rebuild from `events.jsonl`, and reconstruct the exact corpus state underlying a claim made earlier — including its exclusions. Then reconstruct it again from the *export* alone, in a fresh directory, with the application code absent from the reconstruction path (I12).

### Phase 1 — Evidence
Ingestion (PDF/image/text/TEI), transcription with quality scoring, search index, passage retrieval with locators, ranking with stated rationale, epistemic status E1–E8, two-channel response contract, verbatim check.

**Exit test:** Traceability rate and quotation fidelity both 100% across the fixture battery; absence-discipline test passes (Section 13.3).

### Phase 2 — Critique
Independence testing and descent clustering, variant clustering (never deletion), bias report, disconfirmation search, corpus maps with drill-down to passage.

**Exit test:** The seeded reprint-family fixture is correctly collapsed to a single witness, with the shared error cited as the basis; the skewed-corpus fixture produces an unprompted bias report before any aggregate is returned.

### Phase 3 — Environment
MCP server exposing the tool layer; MCP clients for external archives; source registry with licence and rate-limit enforcement; Zotero and TEI interchange; orthographic variant expansion; calendar handling.

**Exit test:** A real acquisition run against a real archive completes within published rate limits, with permission checkpoints honoured and every licence constraint recorded per item.

### Phase 4 — Practice
Literature monitoring, drafting under approval, shared corpora with annotation threads, methods-statement export, teaching support.

**Exit test:** A generated methods statement contains everything Section 11.4 requires and round-trips through the export test.

---

## 7. The epistemic engine

### 7.1 Status vocabulary

```python
class Status(StrEnum):
    ATTESTED       = "E1"   # explicitly stated in a source in the corpus
    CORROBORATED   = "E2"   # attested in >= 2 sources that PASSED independence
    INFERRED       = "E3"   # follows from E1/E2 by a stated chain
    CONTESTED      = "E4"   # sources in the corpus disagree
    SINGLE_WITNESS = "E5"   # one source, reliability unestablished
    UNSUPPORTED    = "E6"   # not found; scope of search stated
    NEGATIVE       = "E7"   # a source positively asserts non-occurrence
    OUT_OF_SCOPE   = "E8"   # corpus cannot in principle address this
```

### 7.2 Assignment rules — implement as explicit guards

1. Status is assigned **per claim**, not per document.
2. Status **never rises without new evidence.** Re-asking, rephrasing, or a longer session cannot upgrade E5 to E2. Implement as a monotonicity guard on the claim record.
3. Status **may fall at any time.** A new contradicting source moves E1 → E4 immediately and flags dependent interpretations.
4. **E6 is never rendered as denial.** Ship an output linter that rejects E6 payloads whose text contains denial constructions ("there was no", "did not occur", "never happened"). The E6 template is fixed: *"Not found in corpus version {v}. Searched: {scope}. This is not evidence of non-occurrence."*
5. **E3 shows its premises.** Each premise carries its own locator. Chains longer than three steps are decomposed rather than compressed.
6. **Aggregates inherit the weakest constituent status** and report the distribution.

### 7.3 Independence — the hardest and most important component

E2 is the level most easily awarded in error, and corroboration is what turns a suggestion into a finding. Eleven provincial newspapers printing the same wire dispatch are **one** witness.

**Pipeline:**

```
candidates → shingle/MinHash similarity over normalised text (recall-oriented)
           → pairwise alignment within candidate groups
           → descent signal extraction
           → cluster formation
           → verdict: INDEPENDENT | SHARED_DESCENT | UNDETERMINED
```

**Descent signals, in descending strength:**

1. **Shared error.** Tokens that are (a) rare or absent from a reference lexicon, (b) identical across members, (c) at positions where texts outside the group differ. Two texts agreeing in an unusual mistake almost certainly share a source. This is the single strongest available signal — implement it first and surface it explicitly in the output.
2. **Shared idiosyncratic phrasing** — rare n-grams shared beyond chance.
3. **Shared structural cuts** — the same passage omitted at the same point.
4. **Explicit antecedent citation** — both cite a common third source.
5. **Metadata descent** — one item's provenance names the other, or both derive from one catalogue record.

**Verdict rules:**

- `SHARED_DESCENT` → the cluster is reported as **one witness**, with members listed, the descent evidence shown, and the representative selected by the researcher. Members are excluded with `descent_cluster_member` — reversibly.
- `UNDETERMINED` → **E5 with a note**, never an optimistic E2. Default conservative.
- `INDEPENDENT` → E2 permitted, and the independence argument is attached to the claim and displayed with it.

Never assign E2 on textual similarity or co-occurrence alone. Similarity is a signal of *descent*, not of *corroboration* — getting this backwards inverts the entire feature.

---

## 8. Retrieval

### 8.1 Locator-bound results

Search returns `Passage` objects, each with a resolving locator, the ranking score, and a **stated rationale** — why this passage, in terms a researcher can dispute ("contains the query term in a date-adjacent context"; "matched via orthographic variant *shewed*"). An opaque score is not a rationale.

### 8.2 Orthographic variant expansion

Spelling was not standardised for most of the period most historians work in, so literal search is close to useless. Expansion must be:

- **period- and region-aware** where data allows;
- **shown, not silent** — the expansion set is returned with the results and is editable, because the variant set is itself a scholarly judgement someone may dispute;
- **index-only** — normalised forms are indexed for retrieval; display always shows the original orthography (I9).

### 8.3 Quality-qualified absence

Every negative result is qualified by the legibility of what was searched:

> *"No matches. Searched 1,412 items in corpus v7. Mean character confidence across the searched set: 0.71. 31 items were unreadable and excluded. A negative result at this quality level is weak."*

`"No mentions found"` unqualified is a forbidden output.

### 8.4 Drillable aggregates

Every element of every aggregate view — frequency bar, topic cluster, network node, timeline band — carries the locator set that produced it and opens to those passages in one action. **An analytical method whose output cannot be attributed back to specific passages must not be added to the system**, regardless of its statistical virtues.

---

## 9. Tool layer, permissions, licences

### 9.1 Permission classes

```python
class PermissionClass(StrEnum):
    READ    = "read"      # search, retrieve, analyse, compare — no checkpoint, fully logged
    PREPARE = "prepare"   # draft, stage, propose — nothing leaves or mutates without approval
    ASK     = "ask"       # per-action approval, specifics shown
    ACT     = "act"       # only under explicit, scoped, revocable, time-bounded standing authorisation

@tool(permission=PermissionClass.ASK)
def acquire_source(...): ...
```

The executor enforces the class. `ASK` tools raise `ApprovalRequired` carrying the **specifics** — not `"access external archive?"` but:

> *"Request 340 items from Archive A, ~2.1 GB, under licence L which forbids redistribution. Estimated 68 minutes at the published rate limit."*

Approvals are **scoped to the action**, never to the session. Log every approval and denial. Track approval rate per class: if a class is approved without exception over time, that is evidence it is misclassified and should become a bounded standing authorisation — which is more honest than a ritual click.

### 9.2 Source registry

```yaml
- id: bl_newspapers
  name: British Library Newspapers
  access: api
  rate_limit: { requests: 1, per_seconds: 2 }
  identify_as: "DHRA/0.1 (contact: ...)"
  bulk_download: prohibited
  redistribution: prohibited
  tdm_basis: licensed
  robots_respected: true
  notes: "Per-item retrieval permitted; systematic download prohibited by terms."
```

The tool layer checks these **before** every request. Rate limits are hard constraints, not preferences. Cache aggressively; back off on error rather than retrying; identify in every request.

**Where terms prohibit automated access, the correct behaviour is to say so and support manual acquisition — never to route around it.** The fastest route to these tools being blocked institution-wide is one badly behaved client. Implement no user-agent spoofing, no proxy rotation, no robots.txt bypass. If you find yourself writing code that makes the system look less like itself, stop.

### 9.3 Restricted and community-held material

Support access-restricted zones within a corpus: items flagged with a protocol constraint are excluded from export, from shared corpora and from aggregate display unless explicitly unlocked by the researcher with a recorded justification. A protocol restriction is **not an error to be worked around**; when it blocks an action the system says so and stops.

---

## 10. The generation boundary

This is the architectural decision that determines what can fail. The system is **not a model that has been given documents; it is a retrieval and provenance system that uses a model to move around inside it.**

**The model may:** construct and expand queries; summarise text that is present in retrieved passages; propose candidate relevance judgements for verification; propose research questions and disconfirmation strategies; draft correspondence and prose for approval; explain the system's own trace.

**The model may not:** assert any fact about the past that is not carried by a validated passage; produce a citation; resolve a contradiction between sources; assign epistemic status; decide an exclusion.

### 10.1 Two-channel response contract

```python
@dataclass
class Response:
    evidence: list[EvidenceItem]   # structured, validated, every item locator-bound
    narrative: str | None          # generated prose, ephemeral, MARKED
    trace: TraceSummary
    corpus_version: str
```

Hard rules, enforced in code:

- `narrative` is rejected when `evidence` is empty (I10). The UI renders narrative **below** evidence, never above, and never in a separate view.
- Every `EvidenceItem` passes the verbatim check before serialisation: the quoted text must be found at exactly `[start:end]` of `rep.text`. Mismatch raises; it does not warn.
- `narrative` is stored as ephemeral and excluded from the reproducibility guarantees. Say this in the export.

### 10.2 Reproducibility, honestly

Two kinds, do not conflate them:

- **Process reproducibility** — corpus, queries, retrievals, exclusions, locators, statuses. Achievable, deterministic, guaranteed. This is what the log delivers.
- **Output reproducibility** — the same prose again. **Not achievable across model versions. Do not promise it anywhere in the UI or the export.**

---

## 11. API surface

Indicative; keep it small and REST-ish, versioned under `/api/v1`.

### 11.1 Corpus
```
POST /corpus/items                 ingest (multipart or source reference)
GET  /corpus/items?version=&filter=
GET  /corpus/items/{id}            item + assertions (all, conflicting) + rep chain
POST /corpus/items/{id}/exclude    {reason, threshold?}   → event
POST /corpus/items/{id}/restore    one action, reverses any exclusion
GET  /corpus/versions              list; each with manifest hash
GET  /corpus/versions/{v}/manifest
GET  /corpus/bias-report?version=
GET  /corpus/exclusions?version=   aggregated by reason — the diagnostic view
```

### 11.2 Evidence
```
POST /evidence/search              → Response (two-channel)
GET  /evidence/locator/{...}       → ResolvedPassage (must always succeed)
POST /evidence/compare             align accounts; agreement / divergence / silence
POST /evidence/independence        candidate items → verdict + descent evidence
POST /evidence/disconfirm          {claim} → refutation searches + outcomes
GET  /evidence/provenance/{item}   full chain: claim → passage → rep chain → blob
```

### 11.3 Trace
```
GET  /trace/summary?task=          level 1
GET  /trace/decisions?task=        level 2 — every discretionary judgement
GET  /trace/raw?task=              level 3 — tool calls, params, model versions
GET  /trace/export?format=jsonl
```

Level 2 is the one that matters and the one usually missing. Summary transparency reassures without informing; raw traces inform without being read. **Decision-level disclosure is what a researcher can actually audit in the time available** — build it as a first-class view, not as a filtered log.

### 11.4 Methods export

`POST /export/methods` produces a document containing: corpus definition and version hash; acquisition sources with dates, access conditions and licence basis; the transformation chain with tool versions; selection criteria with counts at each stage; exclusion summary by reason; the full query set; model identities and versions used, with purposes; and a statement of known limitations drawn from the bias report (including access failures).

---

## 12. UI requirements

Keep it plain. Server-rendered or a thin SPA; no heavyweight framework.

**Mandatory:**
- Evidence panel is primary and above; narrative is secondary and below, visually marked as generated.
- Every quotation has its locator visible and one-click resolution to the source, with page image where available.
- Epistemic status is displayed as a code with its meaning on hover — **never as a number**. A researcher cannot dispute 0.83; a researcher can dispute *"E2, on the grounds that these two newspapers are independent"*, and disputing it is the point.
- Exclusions view, grouped by reason, with one-click restore and immediate downstream effect.
- Bias report reachable from every aggregate view, and shown *before* first aggregate results in a session.
- Decision-level trace one interaction from any result.

**Forbidden:**
- Any numeric confidence presented as an epistemic judgement.
- A summary or synthesis rendered above or without its evidence.
- A "clean up corpus" action that deletes anything.
- Silent normalisation anywhere in display.
- Progress language that implies certainty ("Found the answer", "Confirmed").

---

## 13. Acceptance test battery

Implement as `tests/acceptance/`. These are the deliverable as much as the features are.

### 13.1 Mechanical
- `test_traceability_rate` — 100% of evidentiary statements carry a resolving locator. Anything below 100% is a leak in the architecture, not a tuning problem.
- `test_quotation_fidelity` — 100% byte-exact against stored representations. Include adversarial cases: smart quotes, ligatures, soft hyphens, combining diacritics, RTL text.
- `test_exclusion_reversibility` — one action, immediate downstream recomputation.
- `test_version_reconstruction` — rebuild a six-month-old corpus state exactly.
- `test_export_round_trip` — reconstruct from export alone in a clean directory (I12).
- `test_projection_rebuild` — delete `derived.db` + `index/`, replay, assert identical state.

### 13.2 Epistemic
- `test_independence_seeded` — the reprint-family fixture collapses to one witness, citing the shared error.
- `test_status_monotonicity` — repeated querying never upgrades E5 → E2.
- `test_status_demotion` — adding a contradicting source moves E1 → E4 and flags dependents.
- `test_absence_discipline` — unanswerable questions return E6 with scope, never a hedged synthesis. Assert on the linter.
- `test_e6_not_denial` — E6 payloads contain no denial constructions.
- `test_bias_surfacing` — the skewed fixture produces an unprompted bias report before aggregates.

### 13.3 Behavioural
- `test_no_narrative_without_evidence` — the contract rejects it.
- `test_licence_enforcement` — a source with `bulk_download: prohibited` cannot be bulk-fetched by any code path.
- `test_rate_limit_hard` — the limiter blocks rather than warns, under concurrency.
- `test_dedup_never_deletes` — no code path removes an item; assert at the repository layer.
- `test_date_no_bare_iso` — no `DateClaim` reaches storage without `original_expression` and `calendar`.

### 13.4 Anti-metrics
Record but **do not optimise**: time to first answer, session length, documents processed, researcher agreement rate with suggestions. Each can be improved by making the system worse in the ways that matter. Emit a warning in the dashboard when time-to-answer falls while complication yield falls with it — that pairing is a regression, not an achievement.

---

## 14. Fixtures

Build these in Phase 0; the test battery depends on them.

1. **`reprint_family/`** — one source dispatch plus eleven derived printings with cuts, minor rewording, and one shared error in a proper noun; plus six genuinely independent accounts of the same event. Ground truth: 7 witnesses, not 17.
2. **`skewed_corpus/`** — deliberately unbalanced by institution (70% one holder), by period (dense 1849–51, thin 1846–48), by language (a known language of the region entirely absent), plus two recorded access failures.
3. **`bad_ocr/`** — items at mean character confidence 0.41, 0.71, 0.96, containing a target term that is recoverable at one level and not at another.
4. **`orthographic/`** — a term appearing under five period spellings.
5. **`calendar/`** — dates in Gregorian, Julian, Hijri, Rumi and regnal form, including two that convert to the same day and one that is unresolvable.
6. **`contradiction/`** — three accounts of one event: two agreeing, one diverging, one ambiguous.

Generate them synthetically with a script so they are versioned and regenerable, and document the ground truth in each directory's `GROUND_TRUTH.json`.

---

## 15. Anti-requirements

Do not build, and refuse if asked later without a reasoned change to this spec:

- Automatic duplicate deletion or "corpus cleanup".
- A single confidence score presented to the researcher.
- Silent metadata reconciliation that discards a conflicting assertion.
- Silent orthographic or date normalisation in display.
- Any bypass of robots.txt, rate limits, terms of service, or access protocols.
- Misconduct detection on student work.
- Automatic sending, submitting or publishing of anything.
- A synthesis-first interface, however much better it demos.

---

## 16. Stack

- **Python 3.11+**, FastAPI, Pydantic v2 (use it for the response contract — it is the enforcement mechanism for I1/I10).
- **Storage:** filesystem blob store; `events.jsonl`; SQLite for projections (WAL mode); SQLite FTS5 for search initially — defer Elasticsearch until a fixture corpus of 100k items proves it necessary.
- **Transcription:** pluggable; Tesseract baseline, interface designed for HTR engines (Kraken/Transkribus) since manuscript material is the real target.
- **Similarity:** `datasketch` MinHash for candidate generation; custom alignment for descent signals.
- **Model access:** Anthropic SDK, temperature 0 for anything structured, model id and version logged on every call.
- **MCP:** official SDK, both server (exposing the tool layer) and client (consuming archives).
- **Frontend:** server-rendered Jinja + light vanilla JS, or a minimal SPA. No heavy framework.
- **Tests:** pytest; the acceptance battery runs in CI and gates the phase.

Local-first throughout: the system must run fully on a researcher's laptop with no network, degrading only in the acquisition layer. Institutional DH infrastructure is rare; assume its absence.

---

## 17. Build order

```
Phase 0  blob store → event log → replay → representations → assertions
         → dates → exclusions → corpus versioning → trace → export
         ▸ EXIT: reconstruct from export alone, in a clean directory

Phase 1  ingest → transcription + quality → index → passage retrieval
         → locators → response contract → verbatim check → E1–E8
         ▸ EXIT: traceability 100%, fidelity 100%, absence discipline passes

Phase 2  variant clustering → independence engine → bias report
         → disconfirmation search → drillable maps
         ▸ EXIT: seeded reprint family collapses correctly; bias surfaces unprompted

Phase 3  source registry → permissions → MCP server → MCP clients
         → Zotero/TEI → orthography → calendars
         ▸ EXIT: a real archive run, within limits, fully recorded

Phase 4  monitoring → drafting → collaboration → methods export → teaching
         ▸ EXIT: methods statement complete and round-trips
```

Start at Phase 0. Write `tests/acceptance/test_phase0.py` before `src/`.

---

## 18. A note on what success looks like

The system is working when a researcher searching for support finds 37 passages, and the system tells them that eleven of those share a descent and count as one — dropping the evidentiary base by an order of magnitude and making the eventual claim weaker and defensible.

A faster tool would have produced a well-sourced, confident, and probably wrong paragraph. Build for the first outcome.
