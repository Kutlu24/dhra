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
        "app.tagline": "Digital Humanities Research Agent &mdash; evidence before narrative, always.",
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
    },
    "de": {
        # --- app chrome / nav ---------------------------------------------------
        "app.tagline": "Digital Humanities Research Agent &mdash; immer erst der Beleg, dann die Erzählung.",
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
    },
    "fr": {
        # --- app chrome / nav ---------------------------------------------------
        "app.tagline": "Digital Humanities Research Agent &mdash; toujours la preuve avant le récit.",
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
