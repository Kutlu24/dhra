"""Web UI translations -- English, German, French.

Scope is deliberately the UI chrome only (nav, headings, labels, buttons,
static instructional/tutorial prose, and the E1-E8 status-code tooltip
meanings) -- never the corpus/evidence text itself (that's the
researcher's own primary sources; translating it would be a fidelity
violation, not a UI nicety), and never the dynamically-generated domain
text that comes back from `dhra.evidence`, `dhra.bias`, `dhra.chat`,
`dhra.research_assistant`, etc. (evidence rationale strings, absence
notes, bias-report warnings, claim-assessment notes, GLM answers).
Those are produced by core modules shared with the CLI and MCP server;
localizing them would mean threading a `lang` parameter through the
whole domain layer, a materially bigger project than a trilingual web
chrome. `dhra ingest`/`dhra search`/etc. command examples inside
`<pre><code>` blocks are also left untranslated on purpose -- they are
literal, copy-pasteable shell commands, identical in every language.

Every value may contain literal HTML (a `<code>`, `<a>`, `<em>`) --
these are static, developer-authored strings, never user input, so
templates render them with `| safe` uniformly rather than tracking
which keys need it.
"""

from __future__ import annotations

from markupsafe import Markup

LANGUAGES = ("en", "de", "fr")
DEFAULT_LANGUAGE = "en"

LANGUAGE_LABELS = {"en": "EN", "de": "DE", "fr": "FR"}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # --- app chrome / nav ---------------------------------------------------
        "app.tagline": "Digital Humanities Research Assistant &mdash; evidence before narrative, always.",
        "nav.search": "Search",
        "nav.chat": "Chat",
        "nav.add_item": "Add item",
        "nav.claims": "Claims",
        "nav.aggregate": "Aggregate",
        "nav.exclusions": "Exclusions",
        "nav.trace": "Trace",
        "nav.updates": "Updates",
        "nav.assistant": "Research &amp; Teaching",
        "nav.tutorial": "Getting started",
        "footer.corpus": "corpus",
        # --- search.html ---------------------------------------------------------
        "search.title": "Evidence search",
        "search.lede": 'Literal, locator-bound. New here? <a href="/tutorial">Getting started &rarr;</a>',
        "search.placeholder": "literal query",
        "search.button": "Search",
        "search.variants_note": "Orthographic variants also searched: {variants}",
        "search.evidence_heading": "Evidence ({n})",
        "search.rationale_prefix": "rationale:",
        "search.use_as_evidence": "use as evidence for a claim &rarr;",
        "search.narrative_badge": "Generated -- not verified, not reproducible (see docs)",
        "search.decision_trace": "decision trace &rarr;",
        # --- chat.html -------------------------------------------------------------
        "chat.title": "Chat",
        "chat.lede": "Every answer is grounded in a real search of the corpus, shown above the "
        'answer, with its own locator. No evidence, no answer &mdash; the model '
        'never guesses. <a href="/tutorial">Getting started &rarr;</a>',
        "chat.not_configured": "No LLM backend configured &mdash; showing evidence only, no generated answer. "
        "Set <code>DHRA_GLM_BASE_URL</code> / <code>DHRA_GLM_API_KEY</code> to enable answers.",
        "chat.you": "You:",
        "chat.evidence_label": "Evidence:",
        "chat.source_link": "[source]",
        "chat.llm_error_prefix": "Couldn't reach the LLM backend just now, showing evidence only.",
        "chat.generated_badge": "Generated -- grounded only in the evidence above",
        "chat.placeholder": "Ask about your corpus...",
        "chat.send": "Send",
        "chat.action_find_supporting": "Find supporting evidence",
        "chat.action_find_contradicting": "Find contradicting evidence",
        "chat.action_compare_sources": "Compare sources",
        "chat.action_identify_gaps": "Identify gaps",
        # --- ingest.html -----------------------------------------------------------
        "ingest.title": "Add an item",
        "ingest.description": "Manual upload only (section 9.2's licence/rate-limit gating applies to "
        "real archive acquisition, not to material you already have). Paste text, "
        "or upload a file &mdash; <code>.pdf</code> uses <code>pdftotext</code>, "
        "<code>.png/.jpg/.tif</code> uses Tesseract OCR, <code>.xml/.tei</code> is "
        "parsed as TEI, anything else is stored as plain text.",
        "ingest.source_id_label": "Source id",
        "ingest.access_basis_label": "Access basis",
        "ingest.licence_label": "Licence id (optional)",
        "ingest.reference_label": "Original reference / URL (optional)",
        "ingest.paste_label": "Paste text",
        "ingest.paste_placeholder": "leave empty if uploading a file",
        "ingest.file_label": "...or upload a file",
        "ingest.submit": "Add item",
        # --- locator.html ------------------------------------------------------------
        "locator.title": "Resolved passage",
        "locator.provenance": "Provenance",
        "locator.source": "source",
        "locator.method": "method",
        "locator.retrieved": "retrieved",
        "locator.access_basis": "access basis",
        "locator.licence": "licence",
        "locator.unknown": "(unknown)",
        "locator.redistributable": "redistributable",
        "locator.redistributable_unknown": "(unknown -- unknown is not permission)",
        "locator.original_reference": "original reference",
        "locator.representation": "Representation",
        "locator.kind": "kind",
        "locator.producer": "producer",
        "locator.ocr_quality": "OCR quality signal",
        "locator.ocr_quality_note": "(transcription quality, not an epistemic judgement)",
        "locator.annotations": "Annotations",
        "locator.resolved": "resolved",
        "locator.no_annotations": "No annotations yet.",
        "locator.your_name": "Your name",
        "locator.note": "Note",
        "locator.add_annotation": "Add annotation",
        # --- exclusions.html --------------------------------------------------------
        "exclusions.title": "Exclusions",
        "exclusions.description": "Reversible annotations, never deletion (I4). Restore is one click.",
        "exclusions.col_item": "item",
        "exclusions.col_reason": "reason",
        "exclusions.col_actor": "actor",
        "exclusions.col_ts": "ts",
        "exclusions.restore": "Restore",
        "exclusions.none": "No active exclusions.",
        # --- updates.html -------------------------------------------------------------
        "updates.title": "Literature updates",
        "updates.lede": "Saved queries re-run against OpenAlex's open works index on demand &mdash; "
        "no background process, so nothing is \"watching\" between checks. Click "
        "<strong>Check now</strong> whenever you want, or run <code>dhra watch check</code> "
        'from your own cron for real periodicity. <a href="/tutorial">Getting started &rarr;</a>',
        "updates.error_prefix": "Couldn't reach OpenAlex just now:",
        "updates.queries_heading": "Watch queries",
        "updates.col_query": "query",
        "updates.col_added_by": "added by",
        "updates.remove": "Remove",
        "updates.none_yet": "No watch queries yet &mdash; add one below.",
        "updates.query_placeholder": "e.g. Ottoman manuscripts",
        "updates.add_query": "Add query",
        "updates.check_now": "Check now",
        "updates.new_heading": "New ({n})",
        "updates.no_authors": "(no listed authors)",
        "updates.open_link": "open &rarr;",
        "updates.found_prefix": "found",
        "updates.dismiss": "Dismiss",
        "updates.no_new": "No new matches since the last check.",
        "updates.dismissed_heading": "Dismissed ({n})",
        "updates.restore": "Restore",
        # --- aggregate.html ------------------------------------------------------------
        "aggregate.bias_title": "Bias report",
        "aggregate.bias_description": "Shown before any aggregate result, unprompted (section 12) &mdash; "
        "{n} items in the active corpus.",
        "aggregate.no_warnings": "No warnings raised by this report.",
        "aggregate.title": "Aggregate: items by source",
        "aggregate.col_source": "source",
        "aggregate.col_items": "items",
        "aggregate.col_drilldown": "drill down",
        # --- claims.html -----------------------------------------------------------------
        "claims.title": "Claims",
        "claims.new_link": "+ assess a new claim",
        "claims.col_status": "status",
        "claims.col_claim": "claim",
        "claims.none": "No claims assessed yet.",
        # --- claim_new.html --------------------------------------------------------------
        "claim_new.title": "Assess a claim",
        "claim_new.description": "Status is assigned by deterministic code from the evidence you list here &mdash; "
        "never by the model, never as a number (section 10). One locator per line: "
        "<code>item_id,rep_id,start,end</code>.",
        "claim_new.claim_id_label": "Claim id",
        "claim_new.claim_text_label": "Claim text",
        "claim_new.actor_label": "Actor",
        "claim_new.supporting_label": "Supporting locators",
        "claim_new.contradicting_label": "Contradicting locators",
        "claim_new.negating_label": "Negating locators (source positively asserts non-occurrence)",
        "claim_new.independence_label": "Run the independence engine over the supporting locators first (required for E2 &mdash; I6)",
        "claim_new.submit": "Assess",
        # --- claim_detail.html -----------------------------------------------------------
        "claim_detail.hover_note": "(hover for meaning &mdash; never shown as a number)",
        "claim_detail.supporting": "Supporting",
        "claim_detail.contradicting": "Contradicting",
        "claim_detail.negating": "Negating",
        "claim_detail.history": "History",
        "claim_detail.col_status": "status",
        "claim_detail.col_note": "note",
        "claim_detail.reassess": "+ reassess with new evidence",
        # --- trace.html ------------------------------------------------------------------
        "trace.title": "Decision trace",
        "trace.filter_placeholder": "task id (blank = everything)",
        "trace.filter_button": "Filter",
        "trace.level1": "Level 1 &mdash; summary",
        "trace.event_count": "{n} event(s)",
        "trace.for_task": "for task",
        "trace.col_type": "type",
        "trace.col_count": "count",
        "trace.level2": "Level 2 &mdash; decisions",
        "trace.level2_desc": "Every discretionary judgement: exclusions, restorations, claim assessments, approvals.",
        "trace.col_seq": "seq",
        "trace.col_ts": "ts",
        "trace.none_pick_task": "None &mdash; pick a task to see level 2/3.",
        "trace.none": "None.",
        "trace.level3": "Level 3 &mdash; raw",
        # --- assistant.html ----------------------------------------------------------------
        "assistant.title": "Research &amp; Teaching assistant",
        "assistant.lede": "The model only ever proposes &mdash; every result below is a reviewable draft, "
        'never applied automatically. <a href="/tutorial">What\'s grounded vs. not &rarr;</a>',
        "assistant.not_configured": "No LLM backend configured. Set <code>DHRA_GLM_BASE_URL</code> and "
        '<code>DHRA_GLM_API_KEY</code> (see <a href="/tutorial">Getting started</a>) '
        "before using anything on this page.",
        "assistant.research_heading": "Research",
        "assistant.suggest_title": "Suggest research questions",
        "assistant.suggest_desc": "Searches your corpus for the topic, shows the model only real matching excerpts.",
        "assistant.topic_label": "Topic / query",
        "assistant.your_name_label": "Your name",
        "assistant.suggest_button": "Suggest",
        "assistant.disconfirm_title": "Disconfirmation search",
        "assistant.disconfirm_desc": "The model proposes refutation-oriented search phrases for a claim; real corpus search runs each one for real.",
        "assistant.claim_text_label": "Claim to try to disprove",
        "assistant.disconfirm_button": "Search for refutation",
        "assistant.review_title": "Review a paper against your corpus",
        "assistant.review_desc": "Extracts candidate claims (proposal), finds real corpus evidence for each. Never assigns a status.",
        "assistant.paper_text_label": "Paper text",
        "assistant.review_button": "Review",
        "assistant.teaching_heading": "Teaching",
        "assistant.exam_title": "Draft exam questions",
        "assistant.course_material_label": "Course material",
        "assistant.n_questions_label": "How many questions",
        "assistant.draft_button": "Draft",
        "assistant.rubric_title": "First-pass rubric reading",
        "assistant.rubric_desc": "Never a grade &mdash; flags points against your rubric for you to review.",
        "assistant.rubric_label": "Rubric",
        "assistant.student_submission_label": "Student submission",
        "assistant.read_button": "Read",
        "assistant.reading_list_title": "Reading list / syllabus",
        "assistant.reading_list_desc": "Two parts: real excerpts from your own corpus, and separately-labelled "
        "<strong>unverified</strong> suggestions (book chapters, articles) from the "
        "model's own knowledge &mdash; check every one before adding it to a syllabus.",
        "assistant.reading_list_websearch_on": "Web search is configured: secondary readings are grounded in real, retrieved results instead of the model's own recall.",
        "assistant.reading_list_websearch_off": "No web search backend configured (<code>DHRA_SEARXNG_URL</code>) &mdash; secondary readings still come from the model's own recall, unverified.",
        "assistant.course_topic_label": "Course topic",
        "assistant.reading_list_button": "Draft reading list",
        # --- tutorial.html ------------------------------------------------------------------
        "tutorial.title": "Getting started",
        "tutorial.lede": "DHRA keeps every claim traceable to a source, and shows you when it can't. "
        "Everything below works the same whether you click through this page or "
        "type <code>dhra</code> commands in a terminal &mdash; use whichever fits "
        "the moment.",
        "tutorial.step1_heading": "1. Add something to the corpus",
        "tutorial.step1_body": '<a href="/ingest">Add item &rarr;</a> &mdash; paste text, or upload a '
        "<code>.pdf</code>/<code>.png</code>/<code>.jpg</code>/<code>.tif</code>/<code>.xml</code> "
        "file. PDFs are read with <code>pdftotext</code>, images with real Tesseract "
        "OCR &mdash; not simulated. You'll land on the new item's page once it's in.",
        "tutorial.terminal_equivalent": "Terminal equivalent:",
        "tutorial.step2_heading": "2. Search it",
        "tutorial.step2_body": '<a href="/">Search &rarr;</a> is literal, case-insensitive full-text '
        "search. A hit shows you exactly where it came from (a locator you can "
        "click to see the full source and its provenance) and why it matched. A "
        "miss tells you how much of the corpus was actually searched and how "
        'legible it was &mdash; never just "not found".',
        "tutorial.step3_heading": "3. Assess a claim",
        "tutorial.step3_body": "Found evidence for something? Click <em>use as evidence for a claim</em> "
        'next to any search result, or go to <a href="/claims">Claims &rarr;</a> '
        "directly. You write the claim in your own words and list the locators "
        "that support (or contradict, or negate) it &mdash; DHRA's own code "
        "decides the status from that list, never a model, never a number:",
        "tutorial.status_attested": "attested",
        "tutorial.status_single_witness": "single witness",
        "tutorial.status_contested": "contested",
        "tutorial.status_unsupported": "unsupported",
        "tutorial.step3_hover_note": "Hover any status code anywhere in the app to see what it means &mdash; that tooltip is the only place a status's meaning lives.",
        "tutorial.step4_heading": "4. Check the corpus for bias",
        "tutorial.step4_body": '<a href="/aggregate">Aggregate &rarr;</a> always shows a bias report '
        "first &mdash; source concentration, uneven date coverage, languages you "
        "expected but never see, failed acquisitions &mdash; before any breakdown "
        "of the corpus itself. It's not something you have to remember to check.",
        "tutorial.step5_heading": "5. Exclude, don't delete",
        "tutorial.step5_body": "Bad OCR, wrong date range, off-topic &mdash; excluding an item takes it "
        "out of search and aggregates, but the item itself is never deleted. "
        '<a href="/exclusions">Exclusions &rarr;</a> lists every one, grouped by '
        "reason, restorable in one click.",
        "tutorial.step6_heading": "6. Track new publications",
        "tutorial.step6_body": 'Save a keyword query and <a href="/updates">Updates &rarr;</a> checks '
        "it against OpenAlex's open works index whenever you ask &mdash; no "
        "background process, so nothing is watching between checks. New matches "
        "show title, authors, date and a link; dismiss the ones you don't need, "
        "restore them if you change your mind.",
        "tutorial.step7_heading": "7. See exactly what happened",
        "tutorial.step7_body": '<a href="/trace">Trace &rarr;</a> is the audit trail: every search, '
        "every exclusion, every claim assessment, as an event with a timestamp. "
        "Nothing in this app changes corpus state outside that log.",
        "tutorial.terminal_heading": "Working from a terminal or a script",
        "tutorial.terminal_body": "Every command above is real, scriptable, and talks to the same store "
        "directory as this page &mdash; point <code>--store</code> (or the "
        "<code>DHRA_STORE_DIR</code> environment variable) at it:",
        "tutorial.terminal_mcp_note": "An MCP-connected agent (e.g. Claude Code/Desktop) can also "
        "drive DHRA directly &mdash; see <code>dhra.mcp_server</code> in the repo.",
        "tutorial.download_heading": "Get your own copy",
        "tutorial.download_body": "This site is a shared demo &mdash; its data resets on restart and isn't "
        "private. For a persistent, private corpus, run DHRA on your own machine: "
        '<a href="https://github.com/Kutlu24/dhra/releases">download a ready-to-run copy</a> '
        "(no terminal needed), or "
        '<a href="https://github.com/Kutlu24/dhra">clone the source</a> and follow the '
        "install instructions in the README.",
        # --- status meanings (E1-E8 tooltips) ------------------------------------------------
        "status.attested": "E1 -- explicitly stated in a source in the corpus.",
        "status.corroborated": "E2 -- attested in &gt;=2 sources that passed an independence check.",
        "status.inferred": "E3 -- follows from E1/E2 by a stated chain.",
        "status.contested": "E4 -- sources in the corpus disagree.",
        "status.single_witness": "E5 -- one source, reliability unestablished.",
        "status.unsupported": "E6 -- not found; scope of search stated. Not evidence of non-occurrence.",
        "status.negative": "E7 -- a source positively asserts non-occurrence.",
        "status.out_of_scope": "E8 -- this corpus cannot in principle address this claim.",
        # --- status short labels (status_badge macro) -----------------------------------
        "status_label.attested": "Attested",
        "status_label.corroborated": "Corroborated",
        "status_label.inferred": "Inferred",
        "status_label.contested": "Contested",
        "status_label.single_witness": "Single witness",
        "status_label.unsupported": "Unsupported",
        "status_label.negative": "Negative",
        "status_label.out_of_scope": "Out of scope",
        # --- v2 nav (base.html) -----------------------------------------------------------
        "nav.section_research": "Research",
        "nav.section_sources": "Sources",
        "nav.section_audit": "Audit",
        "nav.section_teaching": "Teaching",
        "nav.overview": "Overview",
        "nav.evidence": "Evidence",
        "nav.research_assistant": "Research Assistant",
        "nav.analysis": "Analysis",
        "nav.corpus": "Corpus",
        "nav.add_sources": "Add Sources",
        "nav.help": "Help",
        "nav.section_ecosystem": "Ecosystem",
        "nav.interpreter": "Simultaneous Interpreter",
        "nav.compliance_assistant": "DSG & DSA Compliance Assistant",
        # --- macros/cards.html (evidence_card) ---------------------------------------------
        "evidence.open_source": "Open source &rarr;",
        # --- dashboard.html (new homepage, was search.html's empty state) -----------------
        "dashboard.h1": "Evidence-Grounded Research for the Digital Humanities",
        "dashboard.lede": "Search your sources, trace every claim to its source, and challenge your own conclusions.",
        "dashboard.search_placeholder": "What are you researching?",
        "dashboard.search_button": "Start research",
        "dashboard.stat_sources": "Sources",
        "dashboard.stat_claims": "Claims",
        "dashboard.stat_contested": "Contested",
        "dashboard.how_it_works_heading": "How it works",
        "dashboard.step1_heading": "Add sources",
        "dashboard.step1_body": "Upload a PDF, scanned image, TEI/XML file, or paste text directly.",
        "dashboard.step2_heading": "Find evidence",
        "dashboard.step2_body": "Literal, locator-bound search finds the exact passage, never a summary.",
        "dashboard.step3_heading": "Build claims",
        "dashboard.step3_body": "Write your claim, link the evidence that supports or contradicts it.",
        "dashboard.step4_heading": "Audit your research",
        "dashboard.step4_body": "Check source concentration, date coverage, and gaps before you trust a conclusion.",
        "dashboard.recent_heading": "Recent",
        "dashboard.recent_none": "Nothing yet &mdash; try a search or add your first source.",
        "dashboard.first_visit_cta": '<a href="/start">New here? Take the 60-second tour &rarr;</a>',
        # --- start.html (onboarding wizard) -------------------------------------------------
        "start.title": "Start a research project",
        "start.step1_heading": "What are you researching?",
        "start.step1_placeholder": "e.g. Ottoman urban history",
        "start.continue": "Continue &rarr;",
        "start.step2_heading": "Add your sources",
        "start.step2_body": "Upload what you have, or explore with whatever is already in this corpus.",
        "start.step2_add": "Add sources &rarr;",
        "start.step2_skip": "Skip for now &rarr;",
        "start.step3_heading": "What would you like to do?",
        "start.step3_evidence": "Find evidence",
        "start.step3_claim": "Test a claim",
        "start.step3_paper": "Review a paper",
        "start.step4_heading": "Ready",
        "start.step4_body": "Your research workspace is ready.",
        "start.step4_cta_evidence": "Start exploring &rarr;",
        "start.step4_cta_claims": "Assess a claim &rarr;",
        # --- sources.html (corpus browse, new) ----------------------------------------------
        "sources.title": "Corpus",
        "sources.lede": "Every active source in this corpus, grouped by where it came from.",
        "sources.col_source": "source",
        "sources.col_items": "items",
        "sources.col_items_list": "items",
        "sources.none": "No sources yet.",
        # --- claim_detail.html additions ---------------------------------------------------
        "claim_detail.view_provenance": "View evidence graph &rarr;",
        # --- macros/graph.html ---------------------------------------------------------------
        "graph.none": "None.",
        # --- trace.html / audit trail --------------------------------------------------------
        "trace.audit_heading": "Research Audit Trail",
        "trace.audit_none": "No activity recorded yet.",
        "trace.export": "Export audit trail",
        "trace.decisions_toggle": "Decision log",
        "trace.raw_toggle": "Raw event log",
        # --- aggregate.html (Corpus Analysis redesign) ---------------------------------------
        "aggregate.no_warnings_heading": "&#10003; No corpus-level warnings detected",
        "aggregate.no_warnings_body": "We checked source concentration, date coverage, language coverage and failed acquisitions.",
        "aggregate.limitations_detected": "{n} limitation(s) detected",
        "aggregate.source_concentration_heading": "Source concentration",
        "aggregate.date_coverage_heading": "Date coverage",
        "aggregate.language_heading": "Language",
        "aggregate.gap_detected": "Gap detected",
        # --- exclusions.html (5-bucket regroup) ----------------------------------------------
        "exclusions.group_duplicate": "Duplicate",
        "exclusions.group_low_quality": "Low quality",
        "exclusions.group_outside_scope": "Outside research scope",
        "exclusions.group_acquisition_problem": "Acquisition problem",
        "exclusions.group_other": "Other",
        "exclusions.remain_auditable": "Excluded sources remain auditable.",
        "exclusions.view_history": "View exclusion history &rarr;",
        # --- assistant.html / teaching.html (Research/Teaching split) -----------------------
        "assistant.title_v2": "Research Assistant",
        "teaching.title": "Teaching",
        "teaching.lede": "The model only ever proposes &mdash; every result below is a reviewable draft, never applied automatically.",
        # --- demo banner (visual redesign, copy stays operator-controlled) ------------------
        "demo_banner.label": "Demo environment",
        # --- content pages (how-it-works / about / evidence-based-research) -----------------
        "how_it_works.title": "How DHRA works",
        "how_it_works.lede": "Four steps from a source on your desk to an auditable, evidence-bound conclusion.",
        "about.title": "About DHRA",
        "about.body": "<p>DHRA is an evidence-grounded research workspace for the humanities. Its central "
        "rule is simple: <strong>evidence before narrative, always</strong>. Every claim you assess is "
        "given a status &mdash; attested, contested, single witness, unsupported &mdash; by deterministic "
        "code reading the evidence you linked to it, never by a model's judgement.</p>"
        '<p>DHRA is not an authority and does not resolve disagreements between sources for you: when '
        'sources disagree, that disagreement is the finding (status E4, contested), preserved and shown, '
        'never silently picked for you.</p>'
        '<p>The same corpus is reachable three ways: this web interface, a scriptable CLI, and an MCP '
        'server for AI-agent workflows &mdash; see <a href="/tutorial">Getting started</a> for all three.</p>',
        "evidence_based_research.title": "Evidence-Based Research, Grounded in Your Own Sources",
        "evidence_based_research.body": "<p>Evidence-based research starts with a simple discipline: never assert "
        "more than your sources actually support, and always keep the path from a conclusion back to its "
        "source intact. DHRA builds that discipline into the tool itself rather than leaving it to "
        "memory or footnote hygiene.</p>"
        "<p>Every search result is locator-bound &mdash; it names the exact source, page, and passage it "
        "came from. Every claim you assess carries an epistemic status (attested, contested, single "
        "witness, unsupported) computed by code from the evidence you linked, not asserted by an AI "
        "model. When two sources disagree, DHRA shows the disagreement rather than picking a side.</p>"
        '<p>This is what separates an evidence-based research assistant from a general-purpose chatbot: '
        'DHRA never answers without evidence, and never hides what it could not find. See '
        '<a href="/how-it-works">how it works</a> or <a href="/tutorial">get started</a>.</p>',
        # --- signup.html / login.html (accounts) ---------------------------------------------
        "signup.title": "Sign up",
        "signup.lede": "Create your own private workspace -- a corpus, claims, and audit trail only you can see.",
        "signup.ephemeral_note": "This deployment's storage resets on restart, your account included. For a real, persistent private copy, self-host DHRA or use a deployment with persistent storage.",
        "signup.username_label": "Username",
        "signup.password_label": "Password",
        "signup.password_confirm_label": "Confirm password",
        "signup.submit": "Create account",
        "signup.have_account": 'Already have an account? <a href="/login">Log in</a>.',
        "login.title": "Log in",
        "login.submit": "Log in",
        "login.no_account": 'No account yet? <a href="/signup">Sign up</a>.',
        # --- base.html sidebar auth status --------------------------------------------------
        "auth.signed_in_as": "Signed in as {username}",
        "auth.log_out": "Log out",
        "auth.sign_up": "Sign up",
        "auth.log_in": "Log in",
        # --- content pages, batch 2 (remaining SEO pages + documentation/blog/welcome) --------
        "dh_research.title": "Digital Humanities Research Software Built Around Evidence",
        "dh_research.body": "<p>Digital humanities researchers already work across TEI editions, IIIF image servers, "
        "archival finding aids and OCR pipelines -- but most tools in that stack optimize for cataloguing or "
        "publishing a source, not for the connective tissue between a source and a conclusion you draw from it. "
        "DHRA is not a digital-edition tool or a repository; it's the research workspace that sits after "
        "acquisition and before publication.</p>"
        "<p>Ingest what you already have -- scans, transcriptions, plain text, TEI/XML -- and DHRA keeps the full "
        "chain from blob to transcription to translation intact, never collapsing it into one clean-looking final "
        "text. Search is literal and locator-bound, not a semantic guess. Claims you build carry a status computed "
        "by deterministic code from the evidence you actually linked, never asserted by a model.</p>"
        '<p>See <a href="/how-it-works">how it works</a> or read the case for '
        '<a href="/evidence-based-research">evidence-based research</a>.</p>',
        "research_assistant_page.title": "An AI Research Assistant That Only Proposes, Never Decides",
        "research_assistant_page.body": "<p>DHRA's research assistant -- chat, research-question suggestions, "
        "disconfirmation search, and paper review -- is grounded the same way as every other surface in the tool: "
        "it drafts, you review, nothing is applied automatically.</p>"
        "<p>Chat never answers without first running a real search of your corpus -- no evidence, no answer, not "
        "even a hedge. Disconfirmation search asks the model to propose refutation-oriented search phrasings for a "
        "claim, then runs each one as a real search against your sources -- the model never gets to decide whether "
        "the claim actually held up. Paper review extracts candidate claims from a paper and finds real corpus "
        "evidence for each one; it never assigns a verdict.</p>"
        "<p>Every output lands as a reviewable draft, timestamped and attributed, sitting next to the real search "
        "results that produced it -- not folded into prose you'd have to take on faith.</p>",
        "claims_evidence_page.title": "How DHRA Decides a Claim's Status",
        "claims_evidence_page.body": "<p>Every claim you assess in DHRA gets one of eight status codes -- E1 "
        "attested, E2 corroborated, E3 inferred, E4 contested, E5 single witness, E6 unsupported, E7 negative, E8 "
        "out of scope -- and every one of them is computed by a small, deterministic function reading the evidence "
        "locators you linked. There is no code path anywhere in DHRA where a language model assigns a status.</p>"
        "<p>The rules are simple and fixed: any contradicting locator makes a claim E4 (contested) regardless of "
        "how much supporting evidence exists -- disagreement between sources is itself the finding, not something "
        "to average away. A claim's status can fall freely as evidence changes, but it can only rise when the "
        "evidence set backing it strictly grows -- re-asking the same question, or rephrasing it, can never "
        "upgrade a claim's status on its own.</p>"
        '<p>See the full status table in <a href="/tutorial">Getting started</a>, or read the broader case for '
        '<a href="/evidence-based-research">evidence-based research</a>.</p>',
        "dh_ai_page.title": "AI for Digital Humanities: Grounded, Not Guessing",
        "dh_ai_page.body": "<p>Most \"AI for research\" tools are optimized for producing a fluent, confident-"
        "sounding answer quickly. DHRA is optimized for producing a defensible one -- even when that means "
        "answering more slowly, or not answering at all. The difference shows up everywhere: a chat that refuses "
        "to answer without evidence, a claim status a model is structurally barred from assigning, a bias report "
        "that runs before any aggregate view rather than after you've already drawn a conclusion.</p>"
        "<p>DHRA is also reachable three ways over the exact same corpus -- a web interface for reading and "
        "reviewing, a scriptable command-line tool for batch work, and an MCP server so an AI coding agent (Claude "
        "Code, Claude Desktop, or any other MCP client) can search, ingest and assess claims directly, under the "
        "same evidence rules as everything else. Use whichever surface fits the moment -- the underlying corpus "
        "and the rules governing it never change.</p>",
        "historical_docs_page.title": "Working With Historical Documents and Primary Sources",
        "historical_docs_page.body": "<p>A historical source rarely arrives as clean text. It's a scan, then an "
        "OCR or manual transcription, sometimes a translation or normalisation on top of that -- each step a real "
        "transformation with its own producer, version, and error rate. DHRA models this explicitly as a chain of "
        "representations (transcription &rarr; translation &rarr; normalisation, each with a parent pointing back "
        "toward the original blob) instead of quietly discarding it once a clean-looking final text exists.</p>"
        "<p>Upload a PDF, a scanned image, or a TEI/XML file directly. OCR confidence and other quality signals "
        "stay attached to the passage they describe -- shown as a transcription-quality note, never smoothed over "
        "or hidden. When a scan is genuinely too poor to search reliably, it's excluded (never deleted) with a "
        "stated, reversible reason, and stays out of aggregates and search until restored.</p>"
        '<p>See <a href="/how-it-works">how it works</a> for the full add-source-to-claim path.</p>',
        "documentation_page.title": "Documentation",
        "documentation_page.body": "<p>DHRA is reachable three ways over the same corpus: this web interface, a "
        "scriptable command-line tool, and an MCP server for AI-agent workflows. The in-app "
        '<a href="/tutorial">Getting started</a> walkthrough covers the web UI step by step, including the '
        "terminal-equivalent command for each step. Below is a short reference for working from a terminal or "
        "script directly.</p>",
        "documentation_page.cli_note": "Every command above talks to the same store directory as the web UI -- point --store (or DHRA_STORE_DIR) at it.",
        "documentation_page.source_link": "Source code and full README on GitHub",
        "blog_page.title": "Blog",
        "blog_page.lede": "Notes on building an evidence-grounded research tool -- design decisions and why DHRA works the way it does.",
        "blog_page.post1_title": "Why DHRA Never Lets the Model Decide",
        "blog_page.post1_body": "<p>The single design decision that shapes everything else in DHRA is this: a "
        "claim's epistemic status -- attested, contested, single witness, unsupported -- is never something a "
        "language model gets to assign. It's computed by a small, deterministic function reading the evidence "
        "locators a researcher (or a verified independence check) has already linked to that claim.</p>"
        "<p>This sounds like a small technical detail, but it changes what the tool can honestly claim about "
        "itself. A model that assigns confidence scores is making a judgement call dressed up as a number -- "
        "impossible for anyone else to audit, and trivially wrong in ways that sound authoritative. Deterministic "
        "code reading an explicit evidence set is boring by comparison, and that's the point: you can read the "
        "function, you can see exactly why a claim is E1 instead of E4, and the answer doesn't change depending on "
        "which model happened to answer, or how the question was phrased.</p>"
        "<p>Everywhere else DHRA uses a language model -- chat, research-question suggestions, disconfirmation "
        "search, paper review -- the same discipline applies: the model proposes, and something checkable (a real "
        "search, a real locator, a researcher's own review) decides. It's a narrower job for AI than most research "
        "tools ask of it, and that narrowness is the whole value proposition.</p>",
        "welcome_page.hero_title": "Research From Evidence, Not Assumptions.",
        "welcome_page.hero_lede": "DHRA helps humanities researchers find, test and trace claims across their own source corpus.",
        "welcome_page.cta_try": "Try the demo",
        "welcome_page.cta_signup": "Sign up for your own workspace",
        "welcome_page.flow_heading": "From source to claim",
        "welcome_page.flow_source": "SOURCE",
        "welcome_page.flow_evidence": "EVIDENCE",
        "welcome_page.flow_claim": "CLAIM",
        "welcome_page.flow_contradiction": "CONTRADICTION",
        "welcome_page.flow_audit": "AUDIT",
        "welcome_page.why_heading": "Why DHRA is different",
        "welcome_page.why1_title": "Every result has a locator",
        "welcome_page.why1_body": "Not a paraphrase -- the exact source, page, and passage a result came from.",
        "welcome_page.why2_title": "Claims are traceable to evidence",
        "welcome_page.why2_body": "Every status is computed from linked locators, never asserted by a model.",
        "welcome_page.why3_title": "Contradicting evidence is preserved",
        "welcome_page.why3_body": "When sources disagree, that disagreement is the finding -- shown, not resolved for you.",
        "welcome_page.why4_title": "Sources are excluded, never silently deleted",
        "welcome_page.why4_body": "A reversible, reasoned annotation -- the original item is never gone.",
        "welcome_page.why5_title": "Every research action is auditable",
        "welcome_page.why5_body": "Searches, exclusions, and claim assessments are all in one readable trail.",
        "welcome_page.why6_title": "AI proposes, humans decide",
        "welcome_page.why6_body": "The model drafts; deterministic code and your own review decide what stands.",
    },
    "de": {
        # --- app chrome / nav ---------------------------------------------------
        "app.tagline": "Digital Humanities Research Assistant &mdash; immer erst der Beleg, dann die Erzählung.",
        "nav.search": "Suche",
        "nav.chat": "Chat",
        "nav.add_item": "Objekt hinzufügen",
        "nav.claims": "Behauptungen",
        "nav.aggregate": "Aggregation",
        "nav.exclusions": "Ausschlüsse",
        "nav.trace": "Protokoll",
        "nav.updates": "Neuigkeiten",
        "nav.assistant": "Forschung &amp; Lehre",
        "nav.tutorial": "Erste Schritte",
        "footer.corpus": "Korpus",
        # --- search.html ---------------------------------------------------------
        "search.title": "Belegsuche",
        "search.lede": 'Wörtlich, an Fundstellen gebunden. Neu hier? <a href="/tutorial">Erste Schritte &rarr;</a>',
        "search.placeholder": "wörtliche Suchanfrage",
        "search.button": "Suchen",
        "search.variants_note": "Auch orthographische Varianten durchsucht: {variants}",
        "search.evidence_heading": "Belege ({n})",
        "search.rationale_prefix": "Begründung:",
        "search.use_as_evidence": "als Beleg für eine Behauptung verwenden &rarr;",
        "search.narrative_badge": "Generiert -- nicht verifiziert, nicht reproduzierbar (siehe Dokumentation)",
        "search.decision_trace": "Entscheidungsprotokoll &rarr;",
        # --- chat.html -------------------------------------------------------------
        "chat.title": "Chat",
        "chat.lede": "Jede Antwort stützt sich auf eine echte Suche im Korpus, oben mit eigener "
        "Fundstelle angezeigt. Kein Beleg, keine Antwort &mdash; das Modell rät nie. "
        '<a href="/tutorial">Erste Schritte &rarr;</a>',
        "chat.not_configured": "Kein LLM-Backend konfiguriert &mdash; es werden nur Belege gezeigt, keine "
        "generierte Antwort. Setzen Sie <code>DHRA_GLM_BASE_URL</code> / "
        "<code>DHRA_GLM_API_KEY</code>, um Antworten zu aktivieren.",
        "chat.you": "Sie:",
        "chat.evidence_label": "Belege:",
        "chat.source_link": "[Quelle]",
        "chat.llm_error_prefix": "Das LLM-Backend war gerade nicht erreichbar, es werden nur Belege gezeigt.",
        "chat.generated_badge": "Generiert -- ausschließlich auf Basis der obigen Belege",
        "chat.placeholder": "Fragen Sie etwas zu Ihrem Korpus...",
        "chat.send": "Senden",
        # --- ingest.html -----------------------------------------------------------
        "ingest.title": "Objekt hinzufügen",
        "ingest.description": "Nur manueller Upload (die Lizenz-/Ratenbegrenzung aus Abschnitt 9.2 gilt für "
        "den Bezug aus echten Archiven, nicht für bereits vorhandenes Material). Text "
        "einfügen oder Datei hochladen &mdash; <code>.pdf</code> nutzt "
        "<code>pdftotext</code>, <code>.png/.jpg/.tif</code> nutzt Tesseract-OCR, "
        "<code>.xml/.tei</code> wird als TEI geparst, alles andere als reiner Text gespeichert.",
        "ingest.source_id_label": "Quellen-ID",
        "ingest.access_basis_label": "Zugangsgrundlage",
        "ingest.licence_label": "Lizenz-ID (optional)",
        "ingest.reference_label": "Originalverweis / URL (optional)",
        "ingest.paste_label": "Text einfügen",
        "ingest.paste_placeholder": "leer lassen, wenn eine Datei hochgeladen wird",
        "ingest.file_label": "...oder eine Datei hochladen",
        "ingest.submit": "Objekt hinzufügen",
        # --- locator.html ------------------------------------------------------------
        "locator.title": "Aufgelöste Textstelle",
        "locator.provenance": "Provenienz",
        "locator.source": "Quelle",
        "locator.method": "Methode",
        "locator.retrieved": "abgerufen",
        "locator.access_basis": "Zugangsgrundlage",
        "locator.licence": "Lizenz",
        "locator.unknown": "(unbekannt)",
        "locator.redistributable": "weiterverbreitbar",
        "locator.redistributable_unknown": "(unbekannt -- unbekannt ist keine Erlaubnis)",
        "locator.original_reference": "Originalverweis",
        "locator.representation": "Repräsentation",
        "locator.kind": "Art",
        "locator.producer": "Erzeugt von",
        "locator.ocr_quality": "OCR-Qualitätssignal",
        "locator.ocr_quality_note": "(Transkriptionsqualität, kein Beweiswerturteil)",
        "locator.annotations": "Anmerkungen",
        "locator.resolved": "gelöst",
        "locator.no_annotations": "Noch keine Anmerkungen.",
        "locator.your_name": "Ihr Name",
        "locator.note": "Notiz",
        "locator.add_annotation": "Anmerkung hinzufügen",
        # --- exclusions.html --------------------------------------------------------
        "exclusions.title": "Ausschlüsse",
        "exclusions.description": "Umkehrbare Markierungen, niemals Löschung (I4). Wiederherstellen mit einem Klick.",
        "exclusions.col_item": "Objekt",
        "exclusions.col_actor": "Person",
        "exclusions.col_ts": "Zeitpunkt",
        "exclusions.restore": "Wiederherstellen",
        "exclusions.none": "Keine aktiven Ausschlüsse.",
        # --- updates.html -------------------------------------------------------------
        "updates.title": "Literaturneuigkeiten",
        "updates.lede": "Gespeicherte Suchanfragen werden auf Wunsch gegen den offenen Werke-Index von "
        'OpenAlex erneut ausgeführt &mdash; kein Hintergrundprozess, es "beobachtet" also '
        "nichts zwischen den Prüfungen. Klicken Sie jederzeit auf "
        "<strong>Jetzt prüfen</strong>, oder lassen Sie <code>dhra watch check</code> "
        'aus Ihrem eigenen Cron laufen, für echte Periodizität. <a href="/tutorial">Erste Schritte &rarr;</a>',
        "updates.error_prefix": "OpenAlex war gerade nicht erreichbar:",
        "updates.queries_heading": "Beobachtungsabfragen",
        "updates.col_query": "Suchanfrage",
        "updates.col_added_by": "hinzugefügt von",
        "updates.remove": "Entfernen",
        "updates.none_yet": "Noch keine Beobachtungsabfragen &mdash; unten eine hinzufügen.",
        "updates.query_placeholder": "z. B. Osmanische Handschriften",
        "updates.add_query": "Abfrage hinzufügen",
        "updates.check_now": "Jetzt prüfen",
        "updates.new_heading": "Neu ({n})",
        "updates.no_authors": "(keine angegebenen Autoren)",
        "updates.open_link": "öffnen &rarr;",
        "updates.found_prefix": "gefunden am",
        "updates.dismiss": "Verwerfen",
        "updates.no_new": "Keine neuen Treffer seit der letzten Prüfung.",
        "updates.dismissed_heading": "Verworfen ({n})",
        "updates.restore": "Wiederherstellen",
        # --- aggregate.html ------------------------------------------------------------
        "aggregate.bias_title": "Verzerrungsbericht",
        "aggregate.bias_description": "Wird unaufgefordert vor jedem Aggregationsergebnis gezeigt (Abschnitt 12) &mdash; "
        "{n} Objekte im aktiven Korpus.",
        "aggregate.no_warnings": "Dieser Bericht enthält keine Warnungen.",
        "aggregate.title": "Aggregation: Objekte nach Quelle",
        "aggregate.col_source": "Quelle",
        "aggregate.col_items": "Objekte",
        "aggregate.col_drilldown": "im Detail",
        # --- claims.html -----------------------------------------------------------------
        "claims.title": "Behauptungen",
        "claims.new_link": "+ neue Behauptung bewerten",
        "claims.col_status": "Status",
        "claims.col_claim": "Behauptung",
        "claims.none": "Noch keine Behauptungen bewertet.",
        # --- claim_new.html --------------------------------------------------------------
        "claim_new.title": "Behauptung bewerten",
        "claim_new.description": "Der Status wird von deterministischem Code aus den hier aufgelisteten Belegen "
        "vergeben &mdash; niemals vom Modell, niemals als Zahl (Abschnitt 10). Eine "
        "Fundstelle pro Zeile: <code>item_id,rep_id,start,end</code>.",
        "claim_new.claim_id_label": "Behauptungs-ID",
        "claim_new.claim_text_label": "Text der Behauptung",
        "claim_new.actor_label": "Person",
        "claim_new.supporting_label": "Stützende Fundstellen",
        "claim_new.contradicting_label": "Widersprechende Fundstellen",
        "claim_new.negating_label": "Verneinende Fundstellen (Quelle bejaht ausdrücklich das Nicht-Eintreten)",
        "claim_new.independence_label": "Zuerst die Unabhängigkeitsprüfung über die stützenden Fundstellen laufen lassen (erforderlich für E2 &mdash; I6)",
        "claim_new.submit": "Bewerten",
        # --- claim_detail.html -----------------------------------------------------------
        "claim_detail.hover_note": "(zum Ansehen der Bedeutung darüberfahren &mdash; nie als Zahl angezeigt)",
        "claim_detail.supporting": "Stützend",
        "claim_detail.contradicting": "Widersprechend",
        "claim_detail.negating": "Verneinend",
        "claim_detail.history": "Verlauf",
        "claim_detail.col_status": "Status",
        "claim_detail.col_note": "Notiz",
        "claim_detail.reassess": "+ mit neuen Belegen neu bewerten",
        # --- trace.html ------------------------------------------------------------------
        "trace.title": "Entscheidungsprotokoll",
        "trace.filter_placeholder": "Aufgaben-ID (leer = alles)",
        "trace.filter_button": "Filtern",
        "trace.level1": "Ebene 1 &mdash; Zusammenfassung",
        "trace.event_count": "{n} Ereignis(se)",
        "trace.for_task": "für Aufgabe",
        "trace.col_type": "Typ",
        "trace.col_count": "Anzahl",
        "trace.level2": "Ebene 2 &mdash; Entscheidungen",
        "trace.level2_desc": "Jede diskretionäre Entscheidung: Ausschlüsse, Wiederherstellungen, Behauptungsbewertungen, Genehmigungen.",
        "trace.col_seq": "Nr.",
        "trace.col_ts": "Zeitpunkt",
        "trace.none_pick_task": "Keine &mdash; eine Aufgabe wählen, um Ebene 2/3 zu sehen.",
        "trace.none": "Keine.",
        "trace.level3": "Ebene 3 &mdash; Rohdaten",
        # --- assistant.html ----------------------------------------------------------------
        "assistant.title": "Forschungs- &amp; Lehrassistent",
        "assistant.lede": "Das Modell schlägt immer nur vor &mdash; jedes Ergebnis unten ist ein "
        "überprüfbarer Entwurf, nie automatisch übernommen. "
        '<a href="/tutorial">Was ist belegt, was nicht &rarr;</a>',
        "assistant.not_configured": "Kein LLM-Backend konfiguriert. Setzen Sie <code>DHRA_GLM_BASE_URL</code> und "
        '<code>DHRA_GLM_API_KEY</code> (siehe <a href="/tutorial">Erste Schritte</a>), '
        "bevor Sie diese Seite nutzen.",
        "assistant.research_heading": "Forschung",
        "assistant.suggest_title": "Forschungsfragen vorschlagen",
        "assistant.suggest_desc": "Durchsucht Ihr Korpus nach dem Thema, zeigt dem Modell nur echte passende Ausschnitte.",
        "assistant.topic_label": "Thema / Suchanfrage",
        "assistant.your_name_label": "Ihr Name",
        "assistant.suggest_button": "Vorschlagen",
        "assistant.disconfirm_title": "Widerlegungssuche",
        "assistant.disconfirm_desc": "Das Modell schlägt widerlegungsorientierte Suchphrasen für eine Behauptung vor; die echte Korpussuche führt jede davon wirklich aus.",
        "assistant.claim_text_label": "Zu widerlegende Behauptung",
        "assistant.disconfirm_button": "Nach Widerlegung suchen",
        "assistant.review_title": "Einen Aufsatz gegen Ihr Korpus prüfen",
        "assistant.review_desc": "Extrahiert mögliche Behauptungen (Vorschlag), findet für jede echte Korpusbelege. Vergibt nie einen Status.",
        "assistant.paper_text_label": "Text des Aufsatzes",
        "assistant.review_button": "Prüfen",
        "assistant.teaching_heading": "Lehre",
        "assistant.exam_title": "Klausurfragen entwerfen",
        "assistant.course_material_label": "Kursmaterial",
        "assistant.n_questions_label": "Wie viele Fragen",
        "assistant.draft_button": "Entwerfen",
        "assistant.rubric_title": "Erste Durchsicht nach Bewertungsraster",
        "assistant.rubric_desc": "Nie eine Note &mdash; markiert Punkte gegen Ihr Raster zur eigenen Überprüfung.",
        "assistant.rubric_label": "Bewertungsraster",
        "assistant.student_submission_label": "Einreichung der Studierenden",
        "assistant.read_button": "Durchsehen",
        "assistant.reading_list_title": "Leseliste / Syllabus",
        "assistant.reading_list_desc": "Zwei Teile: echte Ausschnitte aus Ihrem eigenen Korpus und getrennt "
        "gekennzeichnete, <strong>unverifizierte</strong> Vorschläge (Buchkapitel, "
        "Artikel) aus dem Wissen des Modells &mdash; jeden einzeln prüfen, bevor er in einen Syllabus kommt.",
        "assistant.reading_list_websearch_on": "Websuche ist konfiguriert: Sekundärliteratur basiert auf echten, abgerufenen Ergebnissen statt auf dem Wissen des Modells.",
        "assistant.reading_list_websearch_off": "Kein Websuche-Backend konfiguriert (<code>DHRA_SEARXNG_URL</code>) &mdash; Sekundärliteratur stammt weiterhin aus dem Wissen des Modells, unverifiziert.",
        "assistant.course_topic_label": "Kursthema",
        "assistant.reading_list_button": "Leseliste entwerfen",
        # --- tutorial.html ------------------------------------------------------------------
        "tutorial.title": "Erste Schritte",
        "tutorial.lede": "DHRA hält jede Behauptung bis zu einer Quelle nachverfolgbar und zeigt, wenn "
        "das nicht möglich ist. Alles Folgende funktioniert gleich, ob Sie sich durch "
        "diese Seite klicken oder <code>dhra</code>-Befehle im Terminal eingeben &mdash; "
        "je nachdem, was gerade passt.",
        "tutorial.step1_heading": "1. Etwas zum Korpus hinzufügen",
        "tutorial.step1_body": '<a href="/ingest">Objekt hinzufügen &rarr;</a> &mdash; Text einfügen oder eine '
        "<code>.pdf</code>/<code>.png</code>/<code>.jpg</code>/<code>.tif</code>/<code>.xml</code>-"
        "Datei hochladen. PDFs werden mit <code>pdftotext</code> gelesen, Bilder mit echter "
        "Tesseract-OCR &mdash; nicht simuliert. Sie landen auf der Seite des neuen Objekts, sobald es da ist.",
        "tutorial.terminal_equivalent": "Entsprechung im Terminal:",
        "tutorial.step2_heading": "2. Durchsuchen",
        "tutorial.step2_body": '<a href="/">Suche &rarr;</a> ist eine wörtliche, Groß-/Kleinschreibung ignorierende '
        "Volltextsuche. Ein Treffer zeigt genau, woher er stammt (eine Fundstelle, die Sie "
        "anklicken können, um die vollständige Quelle und ihre Provenienz zu sehen) und "
        "warum er passte. Ein Fehlschlag sagt Ihnen, wie viel vom Korpus tatsächlich durchsucht "
        "wurde und wie lesbar es war &mdash; nie einfach nur „nicht gefunden“.",
        "tutorial.step3_heading": "3. Eine Behauptung bewerten",
        "tutorial.step3_body": "Beleg für etwas gefunden? Klicken Sie neben einem Suchergebnis auf "
        "<em>als Beleg für eine Behauptung verwenden</em>, oder gehen Sie direkt zu "
        '<a href="/claims">Behauptungen &rarr;</a>. Sie formulieren die Behauptung in '
        "eigenen Worten und listen die Fundstellen auf, die sie stützen (oder ihr "
        "widersprechen, oder sie verneinen) &mdash; DHRAs eigener Code entscheidet aus "
        "dieser Liste über den Status, nie ein Modell, nie eine Zahl:",
        "tutorial.status_attested": "belegt",
        "tutorial.status_single_witness": "einzelne Quelle",
        "tutorial.status_contested": "umstritten",
        "tutorial.status_unsupported": "unbelegt",
        "tutorial.step3_hover_note": "Überfahren Sie einen Status-Code an beliebiger Stelle in der App mit der Maus, um seine "
        "Bedeutung zu sehen &mdash; dieser Tooltipp ist der einzige Ort, an dem die Bedeutung eines Status steht.",
        "tutorial.step4_heading": "4. Das Korpus auf Verzerrung prüfen",
        "tutorial.step4_body": '<a href="/aggregate">Aggregation &rarr;</a> zeigt immer zuerst einen '
        "Verzerrungsbericht &mdash; Quellenkonzentration, ungleiche Datumsabdeckung, "
        "erwartete, aber nie vorkommende Sprachen, fehlgeschlagene Erwerbungen &mdash; "
        "vor jeder Aufschlüsselung des Korpus selbst. Das ist nichts, an das Sie sich erinnern müssen.",
        "tutorial.step5_heading": "5. Ausschließen, nicht löschen",
        "tutorial.step5_body": "Schlechte OCR, falscher Zeitraum, themenfremd &mdash; ein Ausschluss nimmt ein "
        "Objekt aus Suche und Aggregation heraus, aber das Objekt selbst wird nie "
        'gelöscht. <a href="/exclusions">Ausschlüsse &rarr;</a> listet jeden einzelnen, '
        "gruppiert nach Grund, mit einem Klick wiederherstellbar.",
        "tutorial.step6_heading": "6. Neue Publikationen verfolgen",
        "tutorial.step6_body": 'Eine Stichwort-Suchanfrage speichern, und <a href="/updates">Neuigkeiten &rarr;</a> '
        "prüft sie auf Wunsch gegen den offenen Werke-Index von OpenAlex &mdash; kein "
        "Hintergrundprozess, es beobachtet also nichts zwischen den Prüfungen. Neue Treffer "
        "zeigen Titel, Autoren, Datum und einen Link; nicht benötigte verwerfen, bei "
        "Bedarf wiederherstellen.",
        "tutorial.step7_heading": "7. Genau sehen, was passiert ist",
        "tutorial.step7_body": '<a href="/trace">Protokoll &rarr;</a> ist die Audit-Spur: jede Suche, jeder '
        "Ausschluss, jede Behauptungsbewertung, als Ereignis mit Zeitstempel. Nichts in "
        "dieser App ändert den Korpuszustand außerhalb dieses Protokolls.",
        "tutorial.terminal_heading": "Arbeiten vom Terminal oder aus einem Skript",
        "tutorial.terminal_body": "Jeder obige Befehl ist echt, skriptfähig und spricht mit demselben "
        "Store-Verzeichnis wie diese Seite &mdash; richten Sie <code>--store</code> "
        "(oder die Umgebungsvariable <code>DHRA_STORE_DIR</code>) darauf aus:",
        "tutorial.terminal_mcp_note": "Ein MCP-verbundener Agent (z. B. Claude Code/Desktop) kann DHRA auch "
        "direkt steuern &mdash; siehe <code>dhra.mcp_server</code> im Repository.",
        "tutorial.download_heading": "Eigene Kopie holen",
        "tutorial.download_body": "Diese Seite ist eine gemeinsam genutzte Demo &mdash; ihre Daten werden bei "
        "jedem Neustart zurückgesetzt und sind nicht privat. Für ein dauerhaftes, privates "
        "Korpus DHRA auf dem eigenen Rechner ausführen: "
        '<a href="https://github.com/Kutlu24/dhra/releases">eine startfertige Kopie herunterladen</a> '
        "(kein Terminal nötig), oder "
        '<a href="https://github.com/Kutlu24/dhra">den Quellcode klonen</a> und der '
        "Installationsanleitung in der README folgen.",
        # --- status meanings (E1-E8 tooltips) ------------------------------------------------
        "status.attested": "E1 -- ausdrücklich in einer Quelle des Korpus festgehalten.",
        "status.corroborated": "E2 -- in &gt;=2 Quellen belegt, die eine Unabhängigkeitsprüfung bestanden haben.",
        "status.inferred": "E3 -- folgt aus E1/E2 durch eine angegebene Ableitungskette.",
        "status.contested": "E4 -- Quellen im Korpus widersprechen sich.",
        "status.single_witness": "E5 -- eine einzelne Quelle, Zuverlässigkeit nicht geklärt.",
        "status.unsupported": "E6 -- nicht gefunden; Suchumfang angegeben. Kein Beleg für Nicht-Eintreten.",
        "status.negative": "E7 -- eine Quelle bejaht ausdrücklich das Nicht-Eintreten.",
        "status.out_of_scope": "E8 -- dieses Korpus kann diese Behauptung prinzipiell nicht adressieren.",
        # --- status short labels (status_badge macro) -----------------------------------
        "status_label.attested": "Belegt",
        "status_label.corroborated": "Bestätigt",
        "status_label.inferred": "Gefolgert",
        "status_label.contested": "Umstritten",
        "status_label.single_witness": "Einzelquelle",
        "status_label.unsupported": "Unbelegt",
        "status_label.negative": "Verneint",
        "status_label.out_of_scope": "Außerhalb des Umfangs",
        # --- v2 nav (base.html) -----------------------------------------------------------
        "nav.section_research": "Forschung",
        "nav.section_sources": "Quellen",
        "nav.section_audit": "Prüfpfad",
        "nav.section_teaching": "Lehre",
        "nav.overview": "Übersicht",
        "nav.evidence": "Belege",
        "nav.research_assistant": "Forschungsassistent",
        "nav.analysis": "Analyse",
        "nav.corpus": "Korpus",
        "nav.add_sources": "Quellen hinzufügen",
        "nav.help": "Hilfe",
        "nav.section_ecosystem": "Weitere Tools",
        "nav.interpreter": "Simultandolmetscher",
        "nav.compliance_assistant": "DSG- & DSA-Compliance-Assistent",
        # --- macros/cards.html (evidence_card) ---------------------------------------------
        "evidence.open_source": "Quelle öffnen &rarr;",
        # --- dashboard.html (new homepage, was search.html's empty state) -----------------
        "dashboard.h1": "Beleggestützte Forschung für die Digital Humanities",
        "dashboard.lede": "Durchsuchen Sie Ihre Quellen, verfolgen Sie jede Behauptung bis zur Quelle zurück und stellen Sie Ihre eigenen Schlussfolgerungen infrage.",
        "dashboard.search_placeholder": "Was erforschen Sie?",
        "dashboard.search_button": "Forschung starten",
        "dashboard.stat_sources": "Quellen",
        "dashboard.stat_claims": "Behauptungen",
        "dashboard.stat_contested": "Umstritten",
        "dashboard.how_it_works_heading": "So funktioniert es",
        "dashboard.step1_heading": "Quellen hinzufügen",
        "dashboard.step1_body": "Laden Sie ein PDF, ein gescanntes Bild, eine TEI/XML-Datei hoch oder fügen Sie Text direkt ein.",
        "dashboard.step2_heading": "Belege finden",
        "dashboard.step2_body": "Die wörtliche, an Fundstellen gebundene Suche findet die genaue Textstelle, nie nur eine Zusammenfassung.",
        "dashboard.step3_heading": "Behauptungen aufbauen",
        "dashboard.step3_body": "Formulieren Sie Ihre Behauptung, verknüpfen Sie Belege, die sie stützen oder ihr widersprechen.",
        "dashboard.step4_heading": "Ihre Forschung prüfen",
        "dashboard.step4_body": "Prüfen Sie Quellenkonzentration, zeitliche Abdeckung und Lücken, bevor Sie einer Schlussfolgerung vertrauen.",
        "dashboard.recent_heading": "Zuletzt",
        "dashboard.recent_none": "Noch nichts &mdash; probieren Sie eine Suche oder fügen Sie Ihre erste Quelle hinzu.",
        "dashboard.first_visit_cta": '<a href="/start">Neu hier? Die 60-Sekunden-Tour &rarr;</a>',
        # --- start.html (onboarding wizard) -------------------------------------------------
        "start.title": "Ein Forschungsprojekt starten",
        "start.step1_heading": "Was erforschen Sie?",
        "start.step1_placeholder": "z.B. osmanische Stadtgeschichte",
        "start.continue": "Weiter &rarr;",
        "start.step2_heading": "Fügen Sie Ihre Quellen hinzu",
        "start.step2_body": "Laden Sie hoch, was Sie haben, oder erkunden Sie mit dem, was bereits in diesem Korpus vorhanden ist.",
        "start.step2_add": "Quellen hinzufügen &rarr;",
        "start.step2_skip": "Vorerst überspringen &rarr;",
        "start.step3_heading": "Was möchten Sie tun?",
        "start.step3_evidence": "Belege finden",
        "start.step3_claim": "Eine Behauptung prüfen",
        "start.step3_paper": "Ein Papier begutachten",
        "start.step4_heading": "Bereit",
        "start.step4_body": "Ihr Forschungsarbeitsbereich ist bereit.",
        "start.step4_cta_evidence": "Erkundung starten &rarr;",
        "start.step4_cta_claims": "Eine Behauptung prüfen &rarr;",
        # --- sources.html (corpus browse, new) ----------------------------------------------
        "sources.title": "Korpus",
        "sources.lede": "Jede aktive Quelle in diesem Korpus, gruppiert nach Herkunft.",
        "sources.col_source": "Quelle",
        "sources.col_items": "Objekte",
        "sources.col_items_list": "Objekte",
        "sources.none": "Noch keine Quellen.",
        # --- claim_detail.html additions ---------------------------------------------------
        "claim_detail.view_provenance": "Belegdiagramm ansehen &rarr;",
        # --- macros/graph.html ---------------------------------------------------------------
        "graph.none": "Keine.",
        # --- trace.html / audit trail --------------------------------------------------------
        "trace.audit_heading": "Forschungsprüfpfad",
        "trace.audit_none": "Noch keine Aktivität erfasst.",
        "trace.export": "Prüfpfad exportieren",
        "trace.decisions_toggle": "Entscheidungsprotokoll",
        "trace.raw_toggle": "Rohes Ereignisprotokoll",
        # --- aggregate.html (Corpus Analysis redesign) ---------------------------------------
        "aggregate.no_warnings_heading": "&#10003; Keine Warnungen auf Korpusebene festgestellt",
        "aggregate.no_warnings_body": "Wir haben Quellenkonzentration, zeitliche Abdeckung, Sprachabdeckung und fehlgeschlagene Erwerbungen geprüft.",
        "aggregate.limitations_detected": "{n} Einschränkung(en) festgestellt",
        "aggregate.source_concentration_heading": "Quellenkonzentration",
        "aggregate.date_coverage_heading": "Zeitliche Abdeckung",
        "aggregate.language_heading": "Sprache",
        "aggregate.gap_detected": "Lücke festgestellt",
        # --- exclusions.html (5-bucket regroup) ----------------------------------------------
        "exclusions.group_duplicate": "Duplikat",
        "exclusions.group_low_quality": "Geringe Qualität",
        "exclusions.group_outside_scope": "Außerhalb des Forschungsumfangs",
        "exclusions.group_acquisition_problem": "Erwerbungsproblem",
        "exclusions.group_other": "Sonstiges",
        "exclusions.remain_auditable": "Ausgeschlossene Quellen bleiben prüfbar.",
        "exclusions.view_history": "Ausschlussverlauf ansehen &rarr;",
        "exclusions.col_reason": "Grund",
        # --- assistant.html / teaching.html (Research/Teaching split) -----------------------
        "assistant.title_v2": "Forschungsassistent",
        "teaching.title": "Lehre",
        "teaching.lede": "Das Modell schlägt nur vor &mdash; jedes Ergebnis unten ist ein zu prüfender Entwurf, nie automatisch übernommen.",
        # --- demo banner (visual redesign, copy stays operator-controlled) ------------------
        "demo_banner.label": "Demo-Umgebung",
        # --- chat.html action buttons ----------------------------------------------------------
        "chat.action_find_supporting": "Stützende Belege finden",
        "chat.action_find_contradicting": "Widersprechende Belege finden",
        "chat.action_compare_sources": "Quellen vergleichen",
        "chat.action_identify_gaps": "Lücken identifizieren",
        # --- content pages (how-it-works / about / evidence-based-research) -----------------
        "how_it_works.title": "So funktioniert DHRA",
        "how_it_works.lede": "Vier Schritte von einer Quelle auf Ihrem Schreibtisch zu einer prüfbaren, beleggestützten Schlussfolgerung.",
        "about.title": "Über DHRA",
        "about.body": "<p>DHRA ist ein beleggestützter Forschungsarbeitsbereich für die Geisteswissenschaften. Seine zentrale "
        "Regel ist einfach: <strong>immer erst der Beleg, dann die Erzählung</strong>. Jeder Behauptung, die Sie prüfen, wird "
        "ein Status zugewiesen &mdash; belegt, umstritten, Einzelquelle, unbelegt &mdash; durch deterministischen Code, der die "
        "verknüpften Belege liest, nie durch das Urteil eines Modells.</p>"
        '<p>DHRA ist keine Autorität und löst Widersprüche zwischen Quellen nicht für Sie auf: Wenn Quellen widersprechen, ist '
        'dieser Widerspruch selbst der Befund (Status E4, umstritten), erhalten und angezeigt, nie stillschweigend für Sie entschieden.</p>'
        '<p>Dasselbe Korpus ist auf drei Wegen erreichbar: diese Weboberfläche, eine skriptfähige CLI und ein MCP-Server für '
        'KI-Agenten-Workflows &mdash; siehe <a href="/tutorial">Erste Schritte</a> für alle drei.</p>',
        "evidence_based_research.title": "Beleggestützte Forschung, verankert in Ihren eigenen Quellen",
        "evidence_based_research.body": "<p>Beleggestützte Forschung beginnt mit einer einfachen Disziplin: nie mehr behaupten, "
        "als Ihre Quellen tatsächlich stützen, und den Weg von einer Schlussfolgerung zurück zu ihrer Quelle immer intakt "
        "halten. DHRA verankert diese Disziplin im Werkzeug selbst, statt sie dem Gedächtnis oder der Fußnotenpflege zu überlassen.</p>"
        "<p>Jedes Suchergebnis ist an eine Fundstelle gebunden &mdash; es nennt die genaue Quelle, Seite und Textstelle, aus der "
        "es stammt. Jede geprüfte Behauptung trägt einen epistemischen Status (belegt, umstritten, Einzelquelle, unbelegt), der "
        "von Code aus den verknüpften Belegen berechnet wird, nicht von einem KI-Modell behauptet. Wenn sich zwei Quellen "
        "widersprechen, zeigt DHRA den Widerspruch, statt eine Seite zu wählen.</p>"
        '<p>Das unterscheidet einen beleggestützten Forschungsassistenten von einem allgemeinen Chatbot: DHRA antwortet nie ohne '
        'Belege und verbirgt nie, was es nicht finden konnte. Siehe <a href="/how-it-works">So funktioniert es</a> oder '
        '<a href="/tutorial">Erste Schritte</a>.</p>',
        # --- signup.html / login.html (accounts) ---------------------------------------------
        "signup.title": "Registrieren",
        "signup.lede": "Erstellen Sie Ihren eigenen privaten Arbeitsbereich -- ein Korpus, Behauptungen und einen Prüfpfad, die nur Sie sehen.",
        "signup.ephemeral_note": "Der Speicher dieses Deployments wird bei jedem Neustart zurückgesetzt, Ihr Konto eingeschlossen. Für eine echte, dauerhafte private Kopie hosten Sie DHRA selbst oder nutzen Sie ein Deployment mit dauerhaftem Speicher.",
        "signup.username_label": "Benutzername",
        "signup.password_label": "Passwort",
        "signup.password_confirm_label": "Passwort bestätigen",
        "signup.submit": "Konto erstellen",
        "signup.have_account": 'Bereits ein Konto? <a href="/login">Anmelden</a>.',
        "login.title": "Anmelden",
        "login.submit": "Anmelden",
        "login.no_account": 'Noch kein Konto? <a href="/signup">Registrieren</a>.',
        # --- base.html sidebar auth status --------------------------------------------------
        "auth.signed_in_as": "Angemeldet als {username}",
        "auth.log_out": "Abmelden",
        "auth.sign_up": "Registrieren",
        "auth.log_in": "Anmelden",
        # --- content pages, batch 2 (remaining SEO pages + documentation/blog/welcome) --------
        "dh_research.title": "Software für Digital-Humanities-Forschung, aufgebaut um Belege",
        "dh_research.body": "<p>Digital-Humanities-Forscher arbeiten bereits mit TEI-Editionen, IIIF-Bildservern, "
        "Archivfindmitteln und OCR-Pipelines -- aber die meisten Werkzeuge in dieser Kette sind auf die "
        "Katalogisierung oder Veröffentlichung einer Quelle ausgelegt, nicht auf das Bindeglied zwischen einer "
        "Quelle und der Schlussfolgerung, die man aus ihr zieht. DHRA ist kein Digital-Edition-Werkzeug und kein "
        "Repositorium; es ist der Forschungsarbeitsbereich, der nach dem Erwerb und vor der Veröffentlichung steht.</p>"
        "<p>Laden Sie hoch, was Sie bereits haben -- Scans, Transkriptionen, Klartext, TEI/XML -- und DHRA hält die "
        "gesamte Kette vom Rohdatum über die Transkription bis zur Übersetzung intakt, statt sie zu einem sauber "
        "aussehenden Endtext zusammenzufalten. Die Suche ist wörtlich und an Fundstellen gebunden, keine "
        "semantische Vermutung. Behauptungen, die Sie aufbauen, tragen einen Status, der von deterministischem "
        "Code aus den tatsächlich verknüpften Belegen berechnet wird, nie von einem Modell behauptet.</p>"
        '<p>Siehe <a href="/how-it-works">So funktioniert es</a> oder lesen Sie das Argument für '
        '<a href="/evidence-based-research">beleggestützte Forschung</a>.</p>',
        "research_assistant_page.title": "Ein KI-Forschungsassistent, der nur vorschlägt, nie entscheidet",
        "research_assistant_page.body": "<p>DHRAs Forschungsassistent -- Chat, Vorschläge für Forschungsfragen, "
        "Widerlegungssuche und Papierprüfung -- ist auf dieselbe Weise verankert wie jede andere Oberfläche des "
        "Werkzeugs: er entwirft, Sie prüfen, nichts wird automatisch übernommen.</p>"
        "<p>Der Chat antwortet nie, ohne zuvor eine echte Suche in Ihrem Korpus durchzuführen -- kein Beleg, keine "
        "Antwort, nicht einmal eine Einschränkung. Die Widerlegungssuche bittet das Modell, widerlegungsorientierte "
        "Suchformulierungen für eine Behauptung vorzuschlagen, und führt dann jede als echte Suche gegen Ihre "
        "Quellen aus -- das Modell darf nie selbst entscheiden, ob die Behauptung standhielt. Die Papierprüfung "
        "extrahiert Kandidatenbehauptungen aus einem Papier und findet für jede echte Korpusbelege; sie vergibt nie "
        "ein Urteil.</p>"
        "<p>Jedes Ergebnis landet als prüfbarer Entwurf, mit Zeitstempel und Zuordnung, direkt neben den echten "
        "Suchergebnissen, die es hervorgebracht haben -- nicht in Prosa verpackt, der man einfach vertrauen müsste.</p>",
        "claims_evidence_page.title": "Wie DHRA den Status einer Behauptung bestimmt",
        "claims_evidence_page.body": "<p>Jede Behauptung, die Sie in DHRA prüfen, erhält einen von acht "
        "Statuscodes -- E1 belegt, E2 bestätigt, E3 gefolgert, E4 umstritten, E5 Einzelquelle, E6 unbelegt, E7 "
        "verneint, E8 außerhalb des Umfangs -- und jeder davon wird von einer kleinen, deterministischen Funktion "
        "berechnet, die die verknüpften Belegfundstellen liest. Es gibt in DHRA keinen Codepfad, in dem ein "
        "Sprachmodell einen Status vergibt.</p>"
        "<p>Die Regeln sind einfach und fest: Jede widersprechende Fundstelle macht eine Behauptung E4 (umstritten), "
        "unabhängig davon, wie viel stützender Beleg existiert -- Uneinigkeit zwischen Quellen ist selbst der "
        "Befund, nichts, das man wegmitteln sollte. Der Status einer Behauptung kann mit sich ändernden Belegen "
        "frei fallen, aber nur steigen, wenn die zugrundeliegende Belegmenge tatsächlich strikt wächst -- dieselbe "
        "Frage erneut zu stellen oder umzuformulieren kann den Status einer Behauptung nie von selbst anheben.</p>"
        '<p>Die vollständige Statustabelle finden Sie unter <a href="/tutorial">Erste Schritte</a>, oder lesen Sie '
        'das breitere Argument für <a href="/evidence-based-research">beleggestützte Forschung</a>.</p>',
        "dh_ai_page.title": "KI für Digital Humanities: verankert, nicht ratend",
        "dh_ai_page.body": "<p>Die meisten \"KI für Forschung\"-Werkzeuge sind darauf ausgelegt, schnell eine "
        "flüssig und selbstsicher klingende Antwort zu liefern. DHRA ist darauf ausgelegt, eine vertretbare zu "
        "liefern -- selbst wenn das langsamer bedeutet, oder gar keine Antwort. Der Unterschied zeigt sich überall: "
        "ein Chat, der ohne Beleg nicht antwortet, ein Behauptungsstatus, den ein Modell strukturell nicht vergeben "
        "darf, ein Bias-Bericht, der vor jeder Aggregatansicht läuft statt nachdem Sie bereits eine Schlussfolgerung "
        "gezogen haben.</p>"
        "<p>DHRA ist außerdem auf drei Wegen über dasselbe Korpus erreichbar -- eine Weboberfläche zum Lesen und "
        "Prüfen, ein skriptfähiges Kommandozeilenwerkzeug für Stapelarbeiten, und ein MCP-Server, damit ein "
        "KI-Coding-Agent (Claude Code, Claude Desktop oder jeder andere MCP-Client) direkt suchen, aufnehmen und "
        "Behauptungen prüfen kann, unter denselben Belegregeln wie alles andere. Nutzen Sie, was gerade passt -- "
        "das zugrundeliegende Korpus und seine Regeln ändern sich nie.</p>",
        "historical_docs_page.title": "Arbeiten mit historischen Dokumenten und Primärquellen",
        "historical_docs_page.body": "<p>Eine historische Quelle kommt selten als sauberer Text an. Es ist ein "
        "Scan, dann eine OCR- oder manuelle Transkription, manchmal darauf eine Übersetzung oder Normalisierung -- "
        "jeder Schritt eine echte Transformation mit eigenem Ersteller, eigener Version und Fehlerrate. DHRA "
        "modelliert dies explizit als Kette von Repräsentationen (Transkription &rarr; Übersetzung &rarr; "
        "Normalisierung, jede mit einem Elternverweis zurück zum ursprünglichen Rohdatum), statt sie stillschweigend "
        "zu verwerfen, sobald ein sauber aussehender Endtext existiert.</p>"
        "<p>Laden Sie ein PDF, ein gescanntes Bild oder eine TEI/XML-Datei direkt hoch. OCR-Konfidenz und andere "
        "Qualitätssignale bleiben an die Textstelle geheftet, die sie beschreiben -- als "
        "Transkriptionsqualitätshinweis angezeigt, nie geglättet oder verborgen. Wenn ein Scan tatsächlich zu "
        "schlecht ist, um zuverlässig durchsucht zu werden, wird er ausgeschlossen (nie gelöscht), mit einem "
        "angegebenen, umkehrbaren Grund, und bleibt bis zur Wiederherstellung aus Suche und Aggregaten heraus.</p>"
        '<p>Siehe <a href="/how-it-works">So funktioniert es</a> für den vollständigen Weg von der Quelle zur '
        'Behauptung.</p>',
        "documentation_page.title": "Dokumentation",
        "documentation_page.body": "<p>DHRA ist auf drei Wegen über dasselbe Korpus erreichbar: diese "
        "Weboberfläche, ein skriptfähiges Kommandozeilenwerkzeug und ein MCP-Server für KI-Agenten-Workflows. Die "
        'App-interne <a href="/tutorial">Erste-Schritte</a>-Anleitung führt Schritt für Schritt durch die '
        "Weboberfläche, inklusive des Terminal-Äquivalents für jeden Schritt. Unten folgt eine kurze Referenz für "
        "die Arbeit direkt vom Terminal oder Skript aus.</p>",
        "documentation_page.cli_note": "Jeder obige Befehl spricht mit demselben Store-Verzeichnis wie die Weboberfläche -- richten Sie --store (oder DHRA_STORE_DIR) darauf.",
        "documentation_page.source_link": "Quellcode und vollständiges README auf GitHub",
        "blog_page.title": "Blog",
        "blog_page.lede": "Notizen zum Aufbau eines beleggestützten Forschungswerkzeugs -- Designentscheidungen und warum DHRA so funktioniert, wie es funktioniert.",
        "blog_page.post1_title": "Warum DHRA das Modell nie entscheiden lässt",
        "blog_page.post1_body": "<p>Die eine Designentscheidung, die alles andere in DHRA prägt, ist diese: Der "
        "epistemische Status einer Behauptung -- belegt, umstritten, Einzelquelle, unbelegt -- ist niemals etwas, "
        "das ein Sprachmodell vergeben darf. Er wird von einer kleinen, deterministischen Funktion berechnet, die "
        "die Belegfundstellen liest, die ein Forscher (oder eine verifizierte Unabhängigkeitsprüfung) bereits mit "
        "dieser Behauptung verknüpft hat.</p>"
        "<p>Das klingt nach einem kleinen technischen Detail, ändert aber, was das Werkzeug ehrlich über sich "
        "selbst behaupten kann. Ein Modell, das Konfidenzwerte vergibt, trifft eine Ermessensentscheidung, "
        "verkleidet als Zahl -- für niemand anderen prüfbar, und auf eine Weise trivial falsch sein kann, die "
        "dennoch autoritativ klingt. Deterministischer Code, der eine explizite Belegmenge liest, ist im Vergleich "
        "langweilig, und das ist der Punkt: Sie können die Funktion lesen, Sie sehen genau, warum eine Behauptung "
        "E1 statt E4 ist, und die Antwort ändert sich nicht danach, welches Modell gerade geantwortet hat oder wie "
        "die Frage formuliert war.</p>"
        "<p>Überall sonst, wo DHRA ein Sprachmodell nutzt -- Chat, Vorschläge für Forschungsfragen, "
        "Widerlegungssuche, Papierprüfung -- gilt dieselbe Disziplin: Das Modell schlägt vor, und etwas Prüfbares "
        "(eine echte Suche, eine echte Fundstelle, die eigene Prüfung des Forschers) entscheidet. Das ist eine "
        "engere Aufgabe für KI, als die meisten Forschungswerkzeuge ihr geben, und genau diese Enge ist das ganze "
        "Wertversprechen.</p>",
        "welcome_page.hero_title": "Forschung aus Belegen, nicht aus Annahmen.",
        "welcome_page.hero_lede": "DHRA hilft Geisteswissenschaftlern, Behauptungen im eigenen Quellenkorpus zu finden, zu prüfen und zurückzuverfolgen.",
        "welcome_page.cta_try": "Demo ausprobieren",
        "welcome_page.cta_signup": "Eigenen Arbeitsbereich registrieren",
        "welcome_page.flow_heading": "Von der Quelle zur Behauptung",
        "welcome_page.flow_source": "QUELLE",
        "welcome_page.flow_evidence": "BELEG",
        "welcome_page.flow_claim": "BEHAUPTUNG",
        "welcome_page.flow_contradiction": "WIDERSPRUCH",
        "welcome_page.flow_audit": "PRÜFUNG",
        "welcome_page.why_heading": "Warum DHRA anders ist",
        "welcome_page.why1_title": "Jedes Ergebnis hat eine Fundstelle",
        "welcome_page.why1_body": "Keine Paraphrase -- die genaue Quelle, Seite und Textstelle, aus der ein Ergebnis stammt.",
        "welcome_page.why2_title": "Behauptungen sind bis zum Beleg zurückverfolgbar",
        "welcome_page.why2_body": "Jeder Status wird aus verknüpften Fundstellen berechnet, nie von einem Modell behauptet.",
        "welcome_page.why3_title": "Widersprechende Belege bleiben erhalten",
        "welcome_page.why3_body": "Wenn Quellen widersprechen, ist dieser Widerspruch selbst der Befund -- gezeigt, nicht für Sie aufgelöst.",
        "welcome_page.why4_title": "Quellen werden ausgeschlossen, nie stillschweigend gelöscht",
        "welcome_page.why4_body": "Eine umkehrbare, begründete Annotation -- das ursprüngliche Objekt ist nie weg.",
        "welcome_page.why5_title": "Jede Forschungsaktion ist prüfbar",
        "welcome_page.why5_body": "Suchen, Ausschlüsse und Behauptungsprüfungen stehen alle in einem lesbaren Protokoll.",
        "welcome_page.why6_title": "KI schlägt vor, Menschen entscheiden",
        "welcome_page.why6_body": "Das Modell entwirft; deterministischer Code und Ihre eigene Prüfung entscheiden, was Bestand hat.",
    },
    "fr": {
        # --- app chrome / nav ---------------------------------------------------
        "app.tagline": "Digital Humanities Research Assistant &mdash; toujours la preuve avant le récit.",
        "nav.search": "Recherche",
        "nav.chat": "Discussion",
        "nav.add_item": "Ajouter un élément",
        "nav.claims": "Affirmations",
        "nav.aggregate": "Agrégation",
        "nav.exclusions": "Exclusions",
        "nav.trace": "Journal",
        "nav.updates": "Actualités",
        "nav.assistant": "Recherche &amp; Enseignement",
        "nav.tutorial": "Prise en main",
        "footer.corpus": "corpus",
        # --- search.html ---------------------------------------------------------
        "search.title": "Recherche de preuves",
        "search.lede": 'Littérale, liée à un repère. Nouveau ici ? <a href="/tutorial">Prise en main &rarr;</a>',
        "search.placeholder": "requête littérale",
        "search.button": "Rechercher",
        "search.variants_note": "Variantes orthographiques également recherchées : {variants}",
        "search.evidence_heading": "Preuves ({n})",
        "search.rationale_prefix": "justification :",
        "search.use_as_evidence": "utiliser comme preuve pour une affirmation &rarr;",
        "search.narrative_badge": "Généré -- non vérifié, non reproductible (voir la documentation)",
        "search.decision_trace": "journal des décisions &rarr;",
        # --- chat.html -------------------------------------------------------------
        "chat.title": "Discussion",
        "chat.lede": "Chaque réponse s'appuie sur une recherche réelle dans le corpus, affichée "
        "au-dessus de la réponse avec son propre repère. Pas de preuve, pas de réponse "
        '&mdash; le modèle ne devine jamais. <a href="/tutorial">Prise en main &rarr;</a>',
        "chat.not_configured": "Aucun backend LLM configuré &mdash; seules les preuves sont affichées, "
        "pas de réponse générée. Définissez <code>DHRA_GLM_BASE_URL</code> / "
        "<code>DHRA_GLM_API_KEY</code> pour activer les réponses.",
        "chat.you": "Vous :",
        "chat.evidence_label": "Preuves :",
        "chat.source_link": "[source]",
        "chat.llm_error_prefix": "Impossible de joindre le backend LLM à l'instant, affichage des preuves uniquement.",
        "chat.generated_badge": "Généré -- fondé uniquement sur les preuves ci-dessus",
        "chat.placeholder": "Posez une question sur votre corpus...",
        "chat.send": "Envoyer",
        # --- ingest.html -----------------------------------------------------------
        "ingest.title": "Ajouter un élément",
        "ingest.description": "Import manuel uniquement (le contrôle de licence/limite de débit de la "
        "section 9.2 s'applique à l'acquisition réelle depuis une archive, pas à un "
        "matériel que vous possédez déjà). Collez du texte ou importez un fichier "
        "&mdash; <code>.pdf</code> utilise <code>pdftotext</code>, "
        "<code>.png/.jpg/.tif</code> utilise l'OCR Tesseract, <code>.xml/.tei</code> "
        "est analysé comme TEI, tout le reste est stocké en texte brut.",
        "ingest.source_id_label": "Identifiant de la source",
        "ingest.access_basis_label": "Base d'accès",
        "ingest.licence_label": "Identifiant de licence (optionnel)",
        "ingest.reference_label": "Référence originale / URL (optionnel)",
        "ingest.paste_label": "Coller le texte",
        "ingest.paste_placeholder": "laisser vide si vous importez un fichier",
        "ingest.file_label": "...ou importer un fichier",
        "ingest.submit": "Ajouter l'élément",
        # --- locator.html ------------------------------------------------------------
        "locator.title": "Passage résolu",
        "locator.provenance": "Provenance",
        "locator.source": "source",
        "locator.method": "méthode",
        "locator.retrieved": "récupéré le",
        "locator.access_basis": "base d'accès",
        "locator.licence": "licence",
        "locator.unknown": "(inconnu)",
        "locator.redistributable": "redistribuable",
        "locator.redistributable_unknown": "(inconnu -- inconnu n'est pas une autorisation)",
        "locator.original_reference": "référence originale",
        "locator.representation": "Représentation",
        "locator.kind": "type",
        "locator.producer": "produit par",
        "locator.ocr_quality": "signal de qualité OCR",
        "locator.ocr_quality_note": "(qualité de transcription, pas un jugement épistémique)",
        "locator.annotations": "Annotations",
        "locator.resolved": "résolu",
        "locator.no_annotations": "Aucune annotation pour l'instant.",
        "locator.your_name": "Votre nom",
        "locator.note": "Note",
        "locator.add_annotation": "Ajouter une annotation",
        # --- exclusions.html --------------------------------------------------------
        "exclusions.title": "Exclusions",
        "exclusions.description": "Annotations réversibles, jamais de suppression (I4). Restauration en un clic.",
        "exclusions.col_item": "élément",
        "exclusions.col_actor": "personne",
        "exclusions.col_ts": "horodatage",
        "exclusions.restore": "Restaurer",
        "exclusions.none": "Aucune exclusion active.",
        # --- updates.html -------------------------------------------------------------
        "updates.title": "Veille documentaire",
        "updates.lede": "Les requêtes enregistrées sont relancées à la demande contre l'index "
        "ouvert des travaux d'OpenAlex &mdash; aucun processus en arrière-plan, rien ne "
        '"surveille" entre deux vérifications. Cliquez sur <strong>Vérifier '
        "maintenant</strong> quand vous voulez, ou lancez <code>dhra watch check</code> "
        'depuis votre propre cron pour une véritable périodicité. <a href="/tutorial">Prise en main &rarr;</a>',
        "updates.error_prefix": "Impossible de joindre OpenAlex à l'instant :",
        "updates.queries_heading": "Requêtes de veille",
        "updates.col_query": "requête",
        "updates.col_added_by": "ajoutée par",
        "updates.remove": "Retirer",
        "updates.none_yet": "Aucune requête de veille pour l'instant &mdash; ajoutez-en une ci-dessous.",
        "updates.query_placeholder": "p. ex. manuscrits ottomans",
        "updates.add_query": "Ajouter la requête",
        "updates.check_now": "Vérifier maintenant",
        "updates.new_heading": "Nouveautés ({n})",
        "updates.no_authors": "(aucun auteur indiqué)",
        "updates.open_link": "ouvrir &rarr;",
        "updates.found_prefix": "trouvé le",
        "updates.dismiss": "Ignorer",
        "updates.no_new": "Aucun nouveau résultat depuis la dernière vérification.",
        "updates.dismissed_heading": "Ignorés ({n})",
        "updates.restore": "Restaurer",
        # --- aggregate.html ------------------------------------------------------------
        "aggregate.bias_title": "Rapport de biais",
        "aggregate.bias_description": "Affiché avant tout résultat agrégé, sans qu'on le demande (section 12) "
        "&mdash; {n} éléments dans le corpus actif.",
        "aggregate.no_warnings": "Ce rapport ne soulève aucune alerte.",
        "aggregate.title": "Agrégation : éléments par source",
        "aggregate.col_source": "source",
        "aggregate.col_items": "éléments",
        "aggregate.col_drilldown": "détail",
        # --- claims.html -----------------------------------------------------------------
        "claims.title": "Affirmations",
        "claims.new_link": "+ évaluer une nouvelle affirmation",
        "claims.col_status": "statut",
        "claims.col_claim": "affirmation",
        "claims.none": "Aucune affirmation évaluée pour l'instant.",
        # --- claim_new.html --------------------------------------------------------------
        "claim_new.title": "Évaluer une affirmation",
        "claim_new.description": "Le statut est attribué par du code déterministe à partir des preuves "
        "listées ici &mdash; jamais par le modèle, jamais sous forme de nombre "
        "(section 10). Un repère par ligne : <code>item_id,rep_id,start,end</code>.",
        "claim_new.claim_id_label": "Identifiant de l'affirmation",
        "claim_new.claim_text_label": "Texte de l'affirmation",
        "claim_new.actor_label": "Personne",
        "claim_new.supporting_label": "Repères à l'appui",
        "claim_new.contradicting_label": "Repères contradictoires",
        "claim_new.negating_label": "Repères infirmatifs (la source affirme positivement la non-occurrence)",
        "claim_new.independence_label": "Exécuter d'abord le moteur d'indépendance sur les repères à l'appui (requis pour E2 &mdash; I6)",
        "claim_new.submit": "Évaluer",
        # --- claim_detail.html -----------------------------------------------------------
        "claim_detail.hover_note": "(survolez pour voir la signification &mdash; jamais affiché sous forme de nombre)",
        "claim_detail.supporting": "À l'appui",
        "claim_detail.contradicting": "Contradictoire",
        "claim_detail.negating": "Infirmatif",
        "claim_detail.history": "Historique",
        "claim_detail.col_status": "statut",
        "claim_detail.col_note": "note",
        "claim_detail.reassess": "+ réévaluer avec de nouvelles preuves",
        # --- trace.html ------------------------------------------------------------------
        "trace.title": "Journal des décisions",
        "trace.filter_placeholder": "identifiant de tâche (vide = tout)",
        "trace.filter_button": "Filtrer",
        "trace.level1": "Niveau 1 &mdash; résumé",
        "trace.event_count": "{n} événement(s)",
        "trace.for_task": "pour la tâche",
        "trace.col_type": "type",
        "trace.col_count": "nombre",
        "trace.level2": "Niveau 2 &mdash; décisions",
        "trace.level2_desc": "Chaque jugement discrétionnaire : exclusions, restaurations, évaluations d'affirmations, approbations.",
        "trace.col_seq": "n°",
        "trace.col_ts": "horodatage",
        "trace.none_pick_task": "Aucun &mdash; choisissez une tâche pour voir les niveaux 2/3.",
        "trace.none": "Aucun.",
        "trace.level3": "Niveau 3 &mdash; données brutes",
        # --- assistant.html ----------------------------------------------------------------
        "assistant.title": "Assistant de recherche &amp; d'enseignement",
        "assistant.lede": "Le modèle ne fait jamais que proposer &mdash; chaque résultat ci-dessous est "
        "un brouillon à relire, jamais appliqué automatiquement. "
        '<a href="/tutorial">Ce qui est fondé ou non &rarr;</a>',
        "assistant.not_configured": "Aucun backend LLM configuré. Définissez <code>DHRA_GLM_BASE_URL</code> et "
        '<code>DHRA_GLM_API_KEY</code> (voir <a href="/tutorial">Prise en main</a>) '
        "avant d'utiliser quoi que ce soit sur cette page.",
        "assistant.research_heading": "Recherche",
        "assistant.suggest_title": "Suggérer des questions de recherche",
        "assistant.suggest_desc": "Recherche le sujet dans votre corpus, ne montre au modèle que des extraits réels correspondants.",
        "assistant.topic_label": "Sujet / requête",
        "assistant.your_name_label": "Votre nom",
        "assistant.suggest_button": "Suggérer",
        "assistant.disconfirm_title": "Recherche de réfutation",
        "assistant.disconfirm_desc": "Le modèle propose des formulations de recherche orientées réfutation pour une affirmation ; la recherche réelle dans le corpus exécute chacune d'elles pour de vrai.",
        "assistant.claim_text_label": "Affirmation à tenter de réfuter",
        "assistant.disconfirm_button": "Rechercher une réfutation",
        "assistant.review_title": "Confronter un article à votre corpus",
        "assistant.review_desc": "Extrait des affirmations candidates (proposition), trouve pour chacune de vraies preuves du corpus. N'attribue jamais de statut.",
        "assistant.paper_text_label": "Texte de l'article",
        "assistant.review_button": "Confronter",
        "assistant.teaching_heading": "Enseignement",
        "assistant.exam_title": "Rédiger des questions d'examen",
        "assistant.course_material_label": "Matériel de cours",
        "assistant.n_questions_label": "Nombre de questions",
        "assistant.draft_button": "Rédiger",
        "assistant.rubric_title": "Première lecture selon une grille",
        "assistant.rubric_desc": "Jamais une note &mdash; signale des points à examiner au regard de votre grille.",
        "assistant.rubric_label": "Grille d'évaluation",
        "assistant.student_submission_label": "Copie de l'étudiant",
        "assistant.read_button": "Lire",
        "assistant.reading_list_title": "Liste de lecture / syllabus",
        "assistant.reading_list_desc": "Deux parties : de vrais extraits de votre propre corpus, et des suggestions "
        "<strong>non vérifiées</strong> clairement séparées (chapitres de livres, "
        "articles) issues des connaissances du modèle &mdash; à vérifier une par une avant de les ajouter à un syllabus.",
        "assistant.reading_list_websearch_on": "La recherche web est configurée : les lectures secondaires s'appuient sur de vrais résultats récupérés plutôt que sur les connaissances du modèle.",
        "assistant.reading_list_websearch_off": "Aucun backend de recherche web configuré (<code>DHRA_SEARXNG_URL</code>) &mdash; les lectures secondaires proviennent toujours des connaissances du modèle, non vérifiées.",
        "assistant.course_topic_label": "Sujet du cours",
        "assistant.reading_list_button": "Rédiger la liste de lecture",
        # --- tutorial.html ------------------------------------------------------------------
        "tutorial.title": "Prise en main",
        "tutorial.lede": "DHRA garde chaque affirmation traçable jusqu'à une source, et vous le "
        "signale quand ce n'est pas possible. Tout ce qui suit fonctionne de la même "
        "manière que vous naviguiez sur cette page ou tapiez des commandes "
        "<code>dhra</code> dans un terminal &mdash; utilisez ce qui convient sur le moment.",
        "tutorial.step1_heading": "1. Ajouter quelque chose au corpus",
        "tutorial.step1_body": '<a href="/ingest">Ajouter un élément &rarr;</a> &mdash; collez du texte, ou '
        "importez un fichier <code>.pdf</code>/<code>.png</code>/<code>.jpg</code>/"
        "<code>.tif</code>/<code>.xml</code>. Les PDF sont lus avec <code>pdftotext</code>, "
        "les images avec une véritable OCR Tesseract &mdash; pas simulée. Vous arriverez "
        "sur la page du nouvel élément une fois importé.",
        "tutorial.terminal_equivalent": "Équivalent en terminal :",
        "tutorial.step2_heading": "2. Le rechercher",
        "tutorial.step2_body": '<a href="/">Recherche &rarr;</a> est une recherche plein texte littérale, '
        "insensible à la casse. Un résultat montre exactement d'où il vient (un repère "
        "que vous pouvez cliquer pour voir la source complète et sa provenance) et "
        "pourquoi il correspond. Une absence de résultat vous dit combien du corpus a "
        "réellement été fouillé et sa lisibilité &mdash; jamais simplement « introuvable ».",
        "tutorial.step3_heading": "3. Évaluer une affirmation",
        "tutorial.step3_body": "Vous avez trouvé une preuve pour quelque chose ? Cliquez sur "
        "<em>utiliser comme preuve pour une affirmation</em> à côté de n'importe quel "
        'résultat, ou allez directement sur <a href="/claims">Affirmations &rarr;</a>. '
        "Vous rédigez l'affirmation dans vos propres mots et listez les repères qui "
        "l'appuient (ou la contredisent, ou l'infirment) &mdash; c'est le code de DHRA "
        "lui-même qui décide du statut à partir de cette liste, jamais un modèle, jamais un nombre :",
        "tutorial.status_attested": "attestée",
        "tutorial.status_single_witness": "témoin unique",
        "tutorial.status_contested": "contestée",
        "tutorial.status_unsupported": "non étayée",
        "tutorial.step3_hover_note": "Survolez n'importe quel code de statut dans l'application pour en voir la "
        "signification &mdash; cette infobulle est le seul endroit où vit la signification d'un statut.",
        "tutorial.step4_heading": "4. Vérifier les biais du corpus",
        "tutorial.step4_body": '<a href="/aggregate">Agrégation &rarr;</a> montre toujours d\'abord un rapport '
        "de biais &mdash; concentration des sources, couverture temporelle inégale, "
        "langues attendues mais jamais présentes, acquisitions échouées &mdash; avant "
        "toute ventilation du corpus lui-même. Ce n'est pas à vous d'y penser.",
        "tutorial.step5_heading": "5. Exclure, ne pas supprimer",
        "tutorial.step5_body": "Mauvaise OCR, mauvaise période, hors sujet &mdash; exclure un élément le "
        "retire de la recherche et des agrégations, mais l'élément lui-même n'est "
        'jamais supprimé. <a href="/exclusions">Exclusions &rarr;</a> les liste toutes, '
        "groupées par motif, restaurables en un clic.",
        "tutorial.step6_heading": "6. Suivre les nouvelles publications",
        "tutorial.step6_body": 'Enregistrez une requête par mots-clés, et <a href="/updates">Actualités &rarr;</a> '
        "la vérifie à la demande contre l'index ouvert des travaux d'OpenAlex &mdash; "
        "aucun processus en arrière-plan, rien ne surveille entre deux vérifications. Les "
        "nouveaux résultats affichent titre, auteurs, date et un lien ; ignorez ceux "
        "dont vous n'avez pas besoin, restaurez-les si vous changez d'avis.",
        "tutorial.step7_heading": "7. Voir exactement ce qui s'est passé",
        "tutorial.step7_body": '<a href="/trace">Journal &rarr;</a> est la piste d\'audit : chaque recherche, '
        "chaque exclusion, chaque évaluation d'affirmation, comme un événement horodaté. "
        "Rien dans cette application ne modifie l'état du corpus en dehors de ce journal.",
        "tutorial.terminal_heading": "Travailler depuis un terminal ou un script",
        "tutorial.terminal_body": "Chaque commande ci-dessus est réelle, scriptable, et s'adresse au même "
        "répertoire de stockage que cette page &mdash; pointez <code>--store</code> "
        "(ou la variable d'environnement <code>DHRA_STORE_DIR</code>) vers celui-ci :",
        "tutorial.terminal_mcp_note": "Un agent connecté via MCP (p. ex. Claude Code/Desktop) peut aussi "
        "piloter DHRA directement &mdash; voir <code>dhra.mcp_server</code> dans le dépôt.",
        "tutorial.download_heading": "Obtenir votre propre copie",
        "tutorial.download_body": "Ce site est une démo partagée &mdash; ses données sont réinitialisées à "
        "chaque redémarrage et ne sont pas privées. Pour un corpus persistant et privé, "
        "exécutez DHRA sur votre propre machine : "
        '<a href="https://github.com/Kutlu24/dhra/releases">téléchargez une copie prête à '
        "l'emploi</a> (aucun terminal requis), ou "
        '<a href="https://github.com/Kutlu24/dhra">clonez le code source</a> et suivez les '
        "instructions d'installation du README.",
        # --- status meanings (E1-E8 tooltips) ------------------------------------------------
        "status.attested": "E1 -- explicitement énoncé dans une source du corpus.",
        "status.corroborated": "E2 -- attesté dans &gt;=2 sources ayant passé un contrôle d'indépendance.",
        "status.inferred": "E3 -- découle de E1/E2 par une chaîne explicite.",
        "status.contested": "E4 -- les sources du corpus se contredisent.",
        "status.single_witness": "E5 -- une seule source, fiabilité non établie.",
        "status.unsupported": "E6 -- introuvable ; portée de la recherche indiquée. N'est pas une preuve de non-occurrence.",
        "status.negative": "E7 -- une source affirme positivement la non-occurrence.",
        "status.out_of_scope": "E8 -- ce corpus ne peut en principe pas traiter cette affirmation.",
        # --- status short labels (status_badge macro) -----------------------------------
        "status_label.attested": "Attesté",
        "status_label.corroborated": "Corroboré",
        "status_label.inferred": "Déduit",
        "status_label.contested": "Contesté",
        "status_label.single_witness": "Témoin unique",
        "status_label.unsupported": "Non étayé",
        "status_label.negative": "Négatif",
        "status_label.out_of_scope": "Hors champ",
        # --- v2 nav (base.html) -----------------------------------------------------------
        "nav.section_research": "Recherche",
        "nav.section_sources": "Sources",
        "nav.section_audit": "Audit",
        "nav.section_teaching": "Enseignement",
        "nav.overview": "Aperçu",
        "nav.evidence": "Preuves",
        "nav.research_assistant": "Assistant de recherche",
        "nav.analysis": "Analyse",
        "nav.corpus": "Corpus",
        "nav.add_sources": "Ajouter des sources",
        "nav.help": "Aide",
        "nav.section_ecosystem": "Autres outils",
        "nav.interpreter": "Interprète simultané",
        "nav.compliance_assistant": "Assistant de conformité DSG et DSA",
        # --- macros/cards.html (evidence_card) ---------------------------------------------
        "evidence.open_source": "Ouvrir la source &rarr;",
        # --- dashboard.html (new homepage, was search.html's empty state) -----------------
        "dashboard.h1": "Recherche fondée sur des preuves pour les humanités numériques",
        "dashboard.lede": "Recherchez dans vos sources, retracez chaque affirmation jusqu'à sa source et remettez en question vos propres conclusions.",
        "dashboard.search_placeholder": "Que recherchez-vous ?",
        "dashboard.search_button": "Démarrer la recherche",
        "dashboard.stat_sources": "Sources",
        "dashboard.stat_claims": "Affirmations",
        "dashboard.stat_contested": "Contestées",
        "dashboard.how_it_works_heading": "Comment ça marche",
        "dashboard.step1_heading": "Ajouter des sources",
        "dashboard.step1_body": "Téléversez un PDF, une image scannée, un fichier TEI/XML, ou collez du texte directement.",
        "dashboard.step2_heading": "Trouver des preuves",
        "dashboard.step2_body": "La recherche littérale, liée à un repère précis, trouve le passage exact, jamais un résumé.",
        "dashboard.step3_heading": "Construire des affirmations",
        "dashboard.step3_body": "Rédigez votre affirmation, reliez les preuves qui la soutiennent ou la contredisent.",
        "dashboard.step4_heading": "Auditer votre recherche",
        "dashboard.step4_body": "Vérifiez la concentration des sources, la couverture temporelle et les lacunes avant de faire confiance à une conclusion.",
        "dashboard.recent_heading": "Récent",
        "dashboard.recent_none": "Rien pour l'instant &mdash; essayez une recherche ou ajoutez votre première source.",
        "dashboard.first_visit_cta": '<a href="/start">Nouveau ici ? La visite de 60 secondes &rarr;</a>',
        # --- start.html (onboarding wizard) -------------------------------------------------
        "start.title": "Démarrer un projet de recherche",
        "start.step1_heading": "Que recherchez-vous ?",
        "start.step1_placeholder": "p. ex. histoire urbaine ottomane",
        "start.continue": "Continuer &rarr;",
        "start.step2_heading": "Ajoutez vos sources",
        "start.step2_body": "Téléversez ce que vous avez, ou explorez avec ce qui se trouve déjà dans ce corpus.",
        "start.step2_add": "Ajouter des sources &rarr;",
        "start.step2_skip": "Passer pour l'instant &rarr;",
        "start.step3_heading": "Que souhaitez-vous faire ?",
        "start.step3_evidence": "Trouver des preuves",
        "start.step3_claim": "Tester une affirmation",
        "start.step3_paper": "Examiner un article",
        "start.step4_heading": "Prêt",
        "start.step4_body": "Votre espace de recherche est prêt.",
        "start.step4_cta_evidence": "Commencer l'exploration &rarr;",
        "start.step4_cta_claims": "Évaluer une affirmation &rarr;",
        # --- sources.html (corpus browse, new) ----------------------------------------------
        "sources.title": "Corpus",
        "sources.lede": "Chaque source active de ce corpus, regroupée par provenance.",
        "sources.col_source": "source",
        "sources.col_items": "objets",
        "sources.col_items_list": "objets",
        "sources.none": "Aucune source pour l'instant.",
        # --- claim_detail.html additions ---------------------------------------------------
        "claim_detail.view_provenance": "Voir le graphe de preuves &rarr;",
        # --- macros/graph.html ---------------------------------------------------------------
        "graph.none": "Aucun.",
        # --- trace.html / audit trail --------------------------------------------------------
        "trace.audit_heading": "Journal d'audit de recherche",
        "trace.audit_none": "Aucune activité enregistrée pour l'instant.",
        "trace.export": "Exporter le journal d'audit",
        "trace.decisions_toggle": "Journal des décisions",
        "trace.raw_toggle": "Journal brut des événements",
        # --- aggregate.html (Corpus Analysis redesign) ---------------------------------------
        "aggregate.no_warnings_heading": "&#10003; Aucun avertissement au niveau du corpus détecté",
        "aggregate.no_warnings_body": "Nous avons vérifié la concentration des sources, la couverture temporelle, la couverture linguistique et les échecs d'acquisition.",
        "aggregate.limitations_detected": "{n} limitation(s) détectée(s)",
        "aggregate.source_concentration_heading": "Concentration des sources",
        "aggregate.date_coverage_heading": "Couverture temporelle",
        "aggregate.language_heading": "Langue",
        "aggregate.gap_detected": "Lacune détectée",
        # --- exclusions.html (5-bucket regroup) ----------------------------------------------
        "exclusions.group_duplicate": "Doublon",
        "exclusions.group_low_quality": "Qualité insuffisante",
        "exclusions.group_outside_scope": "Hors du champ de recherche",
        "exclusions.group_acquisition_problem": "Problème d'acquisition",
        "exclusions.group_other": "Autre",
        "exclusions.remain_auditable": "Les sources exclues restent vérifiables.",
        "exclusions.view_history": "Voir l'historique des exclusions &rarr;",
        "exclusions.col_reason": "motif",
        # --- assistant.html / teaching.html (Research/Teaching split) -----------------------
        "assistant.title_v2": "Assistant de recherche",
        "teaching.title": "Enseignement",
        "teaching.lede": "Le modèle ne fait que proposer &mdash; chaque résultat ci-dessous est un brouillon à examiner, jamais appliqué automatiquement.",
        # --- demo banner (visual redesign, copy stays operator-controlled) ------------------
        "demo_banner.label": "Environnement de démonstration",
        # --- chat.html action buttons ----------------------------------------------------------
        "chat.action_find_supporting": "Trouver des preuves à l'appui",
        "chat.action_find_contradicting": "Trouver des preuves contradictoires",
        "chat.action_compare_sources": "Comparer les sources",
        "chat.action_identify_gaps": "Identifier les lacunes",
        # --- content pages (how-it-works / about / evidence-based-research) -----------------
        "how_it_works.title": "Comment fonctionne DHRA",
        "how_it_works.lede": "Quatre étapes d'une source sur votre bureau à une conclusion vérifiable et fondée sur des preuves.",
        "about.title": "À propos de DHRA",
        "about.body": "<p>DHRA est un espace de recherche fondé sur des preuves pour les humanités. Sa règle centrale est simple : "
        "<strong>toujours la preuve avant le récit</strong>. Chaque affirmation que vous évaluez reçoit un statut &mdash; attesté, "
        "contesté, témoin unique, non étayé &mdash; par un code déterministe qui lit les preuves qui lui sont liées, jamais par "
        "le jugement d'un modèle.</p>"
        "<p>DHRA n'est pas une autorité et ne résout pas les désaccords entre sources à votre place : lorsque les sources se "
        "contredisent, ce désaccord est lui-même le résultat (statut E4, contesté), conservé et affiché, jamais tranché "
        "silencieusement à votre place.</p>"
        '<p>Le même corpus est accessible de trois façons : cette interface web, une CLI scriptable, et un serveur MCP pour les '
        'workflows d\'agents IA &mdash; voir <a href="/tutorial">Premiers pas</a> pour les trois.</p>',
        "evidence_based_research.title": "Une recherche fondée sur des preuves, ancrée dans vos propres sources",
        "evidence_based_research.body": "<p>La recherche fondée sur des preuves commence par une discipline simple : ne jamais "
        "affirmer plus que ce que vos sources soutiennent réellement, et toujours garder intact le chemin d'une conclusion "
        "jusqu'à sa source. DHRA intègre cette discipline dans l'outil lui-même plutôt que de la laisser à la mémoire ou à "
        "l'hygiène des notes de bas de page.</p>"
        "<p>Chaque résultat de recherche est lié à un repère précis &mdash; il nomme la source exacte, la page et le "
        "passage dont il provient. Chaque affirmation que vous évaluez porte un statut épistémique (attesté, contesté, témoin "
        "unique, non étayé) calculé par du code à partir des preuves liées, jamais affirmé par un modèle d'IA. Lorsque deux "
        "sources se contredisent, DHRA montre la contradiction plutôt que de choisir un camp.</p>"
        '<p>C\'est ce qui distingue un assistant de recherche fondé sur des preuves d\'un chatbot généraliste : DHRA ne répond '
        'jamais sans preuve, et ne cache jamais ce qu\'il n\'a pas pu trouver. Voir <a href="/how-it-works">comment ça '
        'marche</a> ou <a href="/tutorial">premiers pas</a>.</p>',
        # --- signup.html / login.html (accounts) ---------------------------------------------
        "signup.title": "S'inscrire",
        "signup.lede": "Créez votre propre espace de travail privé -- un corpus, des affirmations et un journal d'audit que vous seul pouvez voir.",
        "signup.ephemeral_note": "Le stockage de ce déploiement est réinitialisé à chaque redémarrage, votre compte y compris. Pour une copie privée réellement persistante, hébergez DHRA vous-même ou utilisez un déploiement avec stockage persistant.",
        "signup.username_label": "Nom d'utilisateur",
        "signup.password_label": "Mot de passe",
        "signup.password_confirm_label": "Confirmer le mot de passe",
        "signup.submit": "Créer un compte",
        "signup.have_account": 'Déjà un compte ? <a href="/login">Se connecter</a>.',
        "login.title": "Se connecter",
        "login.submit": "Se connecter",
        "login.no_account": 'Pas encore de compte ? <a href="/signup">S\'inscrire</a>.',
        # --- base.html sidebar auth status --------------------------------------------------
        "auth.signed_in_as": "Connecté en tant que {username}",
        "auth.log_out": "Se déconnecter",
        "auth.sign_up": "S'inscrire",
        "auth.log_in": "Se connecter",
        # --- content pages, batch 2 (remaining SEO pages + documentation/blog/welcome) --------
        "dh_research.title": "Un logiciel de recherche en humanités numériques construit autour des preuves",
        "dh_research.body": "<p>Les chercheurs en humanités numériques travaillent déjà avec des éditions TEI, "
        "des serveurs d'images IIIF, des instruments de recherche d'archives et des chaînes OCR -- mais la plupart "
        "des outils de cette chaîne sont optimisés pour le catalogage ou la publication d'une source, pas pour le "
        "tissu conjonctif entre une source et la conclusion qu'on en tire. DHRA n'est ni un outil d'édition "
        "numérique ni un dépôt ; c'est l'espace de recherche qui se situe après l'acquisition et avant la "
        "publication.</p>"
        "<p>Importez ce que vous avez déjà -- scans, transcriptions, texte brut, TEI/XML -- et DHRA garde intacte "
        "toute la chaîne, du fichier brut à la transcription puis à la traduction, sans jamais la réduire à un "
        "texte final d'apparence propre. La recherche est littérale et liée à un repère précis, pas une "
        "supposition sémantique. Les affirmations que vous construisez portent un statut calculé par du code "
        "déterministe à partir des preuves réellement liées, jamais affirmé par un modèle.</p>"
        '<p>Voir <a href="/how-it-works">comment ça marche</a> ou lire l\'argumentaire pour la '
        '<a href="/evidence-based-research">recherche fondée sur des preuves</a>.</p>',
        "research_assistant_page.title": "Un assistant de recherche IA qui ne fait que proposer, jamais décider",
        "research_assistant_page.body": "<p>L'assistant de recherche de DHRA -- chat, suggestions de questions de "
        "recherche, recherche de réfutation et examen d'articles -- est ancré de la même manière que toute autre "
        "surface de l'outil : il rédige, vous examinez, rien n'est appliqué automatiquement.</p>"
        "<p>Le chat ne répond jamais sans avoir d'abord effectué une recherche réelle dans votre corpus -- pas de "
        "preuve, pas de réponse, pas même une réserve. La recherche de réfutation demande au modèle de proposer des "
        "formulations de recherche orientées vers la réfutation d'une affirmation, puis exécute chacune comme une "
        "recherche réelle dans vos sources -- le modèle ne décide jamais lui-même si l'affirmation a tenu. "
        "L'examen d'articles extrait des affirmations candidates d'un article et trouve pour chacune de vraies "
        "preuves du corpus ; il n'attribue jamais de verdict.</p>"
        "<p>Chaque résultat arrive comme un brouillon à examiner, horodaté et attribué, à côté des vrais résultats "
        "de recherche qui l'ont produit -- jamais noyé dans une prose qu'il faudrait croire sur parole.</p>",
        "claims_evidence_page.title": "Comment DHRA détermine le statut d'une affirmation",
        "claims_evidence_page.body": "<p>Chaque affirmation que vous évaluez dans DHRA reçoit l'un de huit codes "
        "de statut -- E1 attesté, E2 corroboré, E3 déduit, E4 contesté, E5 témoin unique, E6 non étayé, E7 négatif, "
        "E8 hors champ -- et chacun est calculé par une petite fonction déterministe qui lit les repères de preuve "
        "que vous avez liés. Il n'existe dans DHRA aucun chemin de code où un modèle de langage attribue un "
        "statut.</p>"
        "<p>Les règles sont simples et fixes : tout repère contradictoire rend une affirmation E4 (contestée), "
        "quelle que soit la quantité de preuves à l'appui -- le désaccord entre sources est lui-même le résultat, "
        "pas quelque chose à moyenner. Le statut d'une affirmation peut baisser librement à mesure que les preuves "
        "changent, mais ne peut monter que si l'ensemble de preuves sous-jacent croît réellement strictement -- "
        "reposer la même question, ou la reformuler, ne peut jamais à lui seul faire monter le statut d'une "
        "affirmation.</p>"
        '<p>Voir le tableau complet des statuts dans <a href="/tutorial">Premiers pas</a>, ou lire l\'argumentaire '
        'plus large pour la <a href="/evidence-based-research">recherche fondée sur des preuves</a>.</p>',
        "dh_ai_page.title": "L'IA pour les humanités numériques : ancrée, pas devinée",
        "dh_ai_page.body": "<p>La plupart des outils \"IA pour la recherche\" sont optimisés pour produire "
        "rapidement une réponse fluide et sûre d'elle-même. DHRA est optimisé pour produire une réponse défendable "
        "-- même si cela signifie répondre plus lentement, ou ne pas répondre du tout. La différence se voit "
        "partout : un chat qui refuse de répondre sans preuve, un statut d'affirmation qu'un modèle ne peut "
        "structurellement pas attribuer, un rapport de biais qui s'exécute avant toute vue agrégée plutôt qu'après "
        "que vous ayez déjà tiré une conclusion.</p>"
        "<p>DHRA est aussi accessible de trois façons sur exactement le même corpus -- une interface web pour lire "
        "et examiner, un outil en ligne de commande scriptable pour le travail par lots, et un serveur MCP pour "
        "qu'un agent de codage IA (Claude Code, Claude Desktop, ou tout autre client MCP) puisse chercher, "
        "importer et évaluer des affirmations directement, sous les mêmes règles de preuve que tout le reste. "
        "Utilisez la surface qui convient au moment -- le corpus sous-jacent et les règles qui le gouvernent ne "
        "changent jamais.</p>",
        "historical_docs_page.title": "Travailler avec des documents historiques et des sources primaires",
        "historical_docs_page.body": "<p>Une source historique arrive rarement comme un texte propre. C'est un "
        "scan, puis une transcription OCR ou manuelle, parfois une traduction ou une normalisation par-dessus -- "
        "chaque étape une vraie transformation avec son propre producteur, sa propre version, son propre taux "
        "d'erreur. DHRA modélise cela explicitement comme une chaîne de représentations (transcription &rarr; "
        "traduction &rarr; normalisation, chacune avec un parent pointant vers le fichier brut d'origine) au lieu "
        "de la faire discrètement disparaître une fois qu'un texte final d'apparence propre existe.</p>"
        "<p>Téléversez un PDF, une image scannée ou un fichier TEI/XML directement. La confiance OCR et les autres "
        "signaux de qualité restent attachés au passage qu'ils décrivent -- affichés comme une note de qualité de "
        "transcription, jamais lissés ou cachés. Quand un scan est réellement trop mauvais pour être recherché de "
        "façon fiable, il est exclu (jamais supprimé) avec un motif énoncé et réversible, et reste hors des "
        "recherches et agrégats jusqu'à sa restauration.</p>"
        '<p>Voir <a href="/how-it-works">comment ça marche</a> pour le parcours complet, de la source à '
        "l'affirmation.</p>",
        "documentation_page.title": "Documentation",
        "documentation_page.body": "<p>DHRA est accessible de trois façons sur le même corpus : cette interface "
        "web, un outil en ligne de commande scriptable, et un serveur MCP pour les workflows d'agents IA. Le guide "
        '<a href="/tutorial">Premiers pas</a> intégré à l\'application couvre l\'interface web étape par étape, '
        "avec la commande terminal équivalente pour chaque étape. Ci-dessous, une courte référence pour travailler "
        "directement depuis un terminal ou un script.</p>",
        "documentation_page.cli_note": "Chaque commande ci-dessus s'adresse au même répertoire de stockage que l'interface web -- pointez --store (ou DHRA_STORE_DIR) vers lui.",
        "documentation_page.source_link": "Code source et README complet sur GitHub",
        "blog_page.title": "Blog",
        "blog_page.lede": "Notes sur la construction d'un outil de recherche fondé sur des preuves -- décisions de conception et pourquoi DHRA fonctionne ainsi.",
        "blog_page.post1_title": "Pourquoi DHRA ne laisse jamais le modèle décider",
        "blog_page.post1_body": "<p>La décision de conception unique qui façonne tout le reste dans DHRA est "
        "celle-ci : le statut épistémique d'une affirmation -- attestée, contestée, témoin unique, non étayée -- "
        "n'est jamais quelque chose qu'un modèle de langage peut attribuer. Il est calculé par une petite fonction "
        "déterministe qui lit les repères de preuve qu'un chercheur (ou une vérification d'indépendance validée) a "
        "déjà liés à cette affirmation.</p>"
        "<p>Cela ressemble à un petit détail technique, mais cela change ce que l'outil peut honnêtement affirmer "
        "sur lui-même. Un modèle qui attribue des scores de confiance prend une décision arbitraire déguisée en "
        "nombre -- impossible à auditer pour quiconque d'autre, et pouvant se tromper de façon triviale tout en "
        "paraissant autoritaire. Un code déterministe qui lit un ensemble de preuves explicite est ennuyeux en "
        "comparaison, et c'est précisément le but : vous pouvez lire la fonction, vous voyez exactement pourquoi "
        "une affirmation est E1 plutôt que E4, et la réponse ne change pas selon le modèle qui a répondu, ni "
        "selon la formulation de la question.</p>"
        "<p>Partout ailleurs où DHRA utilise un modèle de langage -- chat, suggestions de questions de recherche, "
        "recherche de réfutation, examen d'articles -- la même discipline s'applique : le modèle propose, et "
        "quelque chose de vérifiable (une vraie recherche, un vrai repère, l'examen du chercheur lui-même) décide. "
        "C'est un rôle plus étroit pour l'IA que ce que demandent la plupart des outils de recherche, et cette "
        "étroitesse est toute la proposition de valeur.</p>",
        "welcome_page.hero_title": "La recherche à partir de preuves, pas d'hypothèses.",
        "welcome_page.hero_lede": "DHRA aide les chercheurs en humanités à trouver, tester et retracer des affirmations dans leur propre corpus de sources.",
        "welcome_page.cta_try": "Essayer la démo",
        "welcome_page.cta_signup": "S'inscrire pour votre propre espace",
        "welcome_page.flow_heading": "De la source à l'affirmation",
        "welcome_page.flow_source": "SOURCE",
        "welcome_page.flow_evidence": "PREUVE",
        "welcome_page.flow_claim": "AFFIRMATION",
        "welcome_page.flow_contradiction": "CONTRADICTION",
        "welcome_page.flow_audit": "AUDIT",
        "welcome_page.why_heading": "Pourquoi DHRA est différent",
        "welcome_page.why1_title": "Chaque résultat a un repère",
        "welcome_page.why1_body": "Pas une paraphrase -- la source, la page et le passage exacts d'où provient un résultat.",
        "welcome_page.why2_title": "Les affirmations sont traçables jusqu'à la preuve",
        "welcome_page.why2_body": "Chaque statut est calculé à partir de repères liés, jamais affirmé par un modèle.",
        "welcome_page.why3_title": "Les preuves contradictoires sont préservées",
        "welcome_page.why3_body": "Quand les sources se contredisent, cette contradiction est elle-même le résultat -- montrée, pas résolue à votre place.",
        "welcome_page.why4_title": "Les sources sont exclues, jamais supprimées silencieusement",
        "welcome_page.why4_body": "Une annotation réversible et motivée -- l'objet original n'a jamais disparu.",
        "welcome_page.why5_title": "Chaque action de recherche est vérifiable",
        "welcome_page.why5_body": "Recherches, exclusions et évaluations d'affirmations figurent toutes dans un journal lisible.",
        "welcome_page.why6_title": "L'IA propose, les humains décident",
        "welcome_page.why6_body": "Le modèle rédige ; le code déterministe et votre propre examen décident ce qui tient.",
    },
}


def translate(lang: str, key: str, **kwargs: object) -> Markup:
    """Returns a markupsafe.Markup, not a plain str -- every translation
    value is static and developer-authored (never user input), including
    the ones with literal HTML (<a>, <code>, <strong>) or apostrophes
    ("Couldn't", French "l'appui"), so it must never be re-escaped by
    Jinja's autoescaping. Markup.format() still escapes any *interpolated*
    kwargs (n=..., variants=...) normally -- only the translation template
    itself is trusted, exactly like Python's own MarkupSafe machinery is
    designed for."""
    table = TRANSLATIONS.get(lang) or TRANSLATIONS[DEFAULT_LANGUAGE]
    text = table.get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    markup = Markup(text)
    return markup.format(**kwargs) if kwargs else markup


def resolve_language(raw: str | None) -> str:
    return raw if raw in LANGUAGES else DEFAULT_LANGUAGE
