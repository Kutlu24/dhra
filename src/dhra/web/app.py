"""Local web UI -- DHRA_BUILD_SPEC.md section 12.

Server-rendered (Jinja2 + light vanilla JS, section 16 -- no heavy
frontend framework), runs on the researcher's own machine against their
own `DHRARepo`. This is the human-facing counterpart to
`dhra.mcp_server` (the agent-facing tool layer) -- same underlying
modules, different surface.

Section 12's mandatory/forbidden lists are enforced here, not just
described:
  - Evidence is always rendered above narrative; narrative never renders
    without evidence (response.py already refuses to build that
    Response at all).
  - Epistemic status is always a code (E1..E8) with its meaning in a
    `title` tooltip -- grep this file for `class="status-code"`; there
    is no other place a Status renders, so there is nowhere for a bare
    number to leak in as a stand-in for a judgement.
  - The bias report is part of the *same* template render as the
    aggregate buckets (`AggregateResponse.bias_report` is not optional),
    so there is no route that can return buckets without it.
  - No delete routes exist anywhere in this module -- only
    exclude/restore (reversible) and approve/deny (logged either way).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dhra.aggregate import aggregate_by_source
from dhra.annotation import add_annotation, annotations_for
from dhra.bias import compute_bias_report
from dhra.chat import answer as chat_answer
from dhra.drafting import list_drafts
from dhra.evidence import search as evidence_search
from dhra.literature_watch import (
    LiteratureWatchError,
    add_watch_query,
    check_for_updates,
    dismiss_candidate,
    list_candidates,
    list_dismissed_candidates,
    list_watch_queries,
    remove_watch_query,
    restore_candidate,
)
from dhra.llm import LLMClient, LLMConfig, LLMError
from dhra.models import ExclusionReason, Locator
from dhra.peer_review import review_paper
from dhra.repo import DHRARepo
from dhra.research_assistant import suggest_research_questions
from dhra.status import Status
from dhra.teaching import assess_paper_against_rubric, draft_exam_questions, draft_reading_list
from dhra.web.i18n import LANGUAGE_LABELS, LANGUAGES, resolve_language, translate
from dhra.trace import trace_decisions, trace_raw, trace_summary

RESEARCH_DRAFT_KINDS = ("research_questions", "peer_review")
TEACHING_DRAFT_KINDS = ("exam_questions", "rubric_assessment", "reading_list")

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# UI-chrome translations only -- see dhra.web.i18n's module docstring for
# the exact scope boundary (never the corpus/evidence text, never the
# dynamically-generated domain text from dhra.evidence/bias/chat/etc.).
STATUS_MEANING_KEYS = {
    Status.ATTESTED: "status.attested",
    Status.CORROBORATED: "status.corroborated",
    Status.INFERRED: "status.inferred",
    Status.CONTESTED: "status.contested",
    Status.SINGLE_WITNESS: "status.single_witness",
    Status.UNSUPPORTED: "status.unsupported",
    Status.NEGATIVE: "status.negative",
    Status.OUT_OF_SCOPE: "status.out_of_scope",
}

LANGUAGE_COOKIE = "dhra_lang"


def build_app(repo: DHRARepo, *, expected_languages: set[str] | None = None, demo_banner: str | None = None) -> FastAPI:
    app = FastAPI(title="DHRA", description="Digital Humanities Research Agent -- local evidence browser")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["status_meaning"] = lambda s, lang: translate(lang, STATUS_MEANING_KEYS.get(Status(s), ""))
    templates.env.globals["status_tone"] = lambda s: "warn" if Status(s) in (Status.CONTESTED, Status.UNSUPPORTED, Status.NEGATIVE) else "ok"
    templates.env.globals["languages"] = LANGUAGES
    templates.env.globals["language_labels"] = LANGUAGE_LABELS
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def _ctx(active: str, request: Request, *, lang: str | None = None, **extra: Any) -> dict[str, Any]:
        """`lang=None` (every pre-existing call site): derived from the
        `dhra_lang` cookie, as before -- one URL, language picked client-side.
        `lang=<code>` (the five /{lang}/... content routes below): the URL
        itself is the language -- real, distinct, crawlable pages per
        language, which a cookie-only switch can never give a search engine
        (it never sends cookies, so it would only ever see English)."""
        if lang is None:
            lang = resolve_language(request.cookies.get(LANGUAGE_COOKIE))
        segments = request.url.path.split("/", 2)
        first_segment = segments[1] if len(segments) > 1 else ""
        lang_url_based = first_segment in LANGUAGES
        if lang_url_based:
            rest = "/" + (segments[2] if len(segments) > 2 else "")
            lang_urls = {code: f"/{code}{rest}" for code in LANGUAGES}
        else:
            lang_urls = {code: f"/lang/{code}" for code in LANGUAGES}
        return {
            "active": active,
            "corpus_version": repo.corpus_version().manifest_hash[:12],
            "demo_banner": demo_banner,
            "lang": lang,
            "lang_urls": lang_urls,
            "lang_url_based": lang_url_based,
            "t": lambda key, **kw: translate(lang, key, **kw),
            **extra,
        }

    def _valid_lang(lang: str) -> str:
        if lang not in LANGUAGES:
            raise HTTPException(status_code=404, detail="unknown language")
        return lang

    @app.get("/lang/{code}")
    def set_language(code: str, request: Request) -> RedirectResponse:
        dest = request.headers.get("referer") or "/"
        resp = RedirectResponse(dest, status_code=303)
        resp.set_cookie(LANGUAGE_COOKIE, resolve_language(code), max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp

    # --- Home / search (section 12: evidence above, narrative below) -------

    def _home_page(request: Request, q: str | None, lang: str | None) -> HTMLResponse:
        response = None
        if q:
            response = evidence_search(repo, q)
        return templates.TemplateResponse(request, "search.html", _ctx("search", request, lang=lang, q=q or "", response=response))

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, q: str | None = None) -> HTMLResponse:
        return _home_page(request, q, lang=None)

    @app.get("/{lang}/", response_class=HTMLResponse)
    def home_lang(request: Request, lang: str, q: str | None = None) -> HTMLResponse:
        lang = _valid_lang(lang)
        resp = _home_page(request, q, lang=lang)
        resp.set_cookie(LANGUAGE_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp

    @app.get("/robots.txt", response_class=Response)
    def robots_txt(request: Request) -> Response:
        origin = f"{request.url.scheme}://{request.url.netloc}"
        return Response(f"User-agent: *\nAllow: /\n\nSitemap: {origin}/sitemap.xml\n", media_type="text/plain")

    @app.get("/sitemap.xml", response_class=Response)
    def sitemap_xml(request: Request) -> Response:
        origin = f"{request.url.scheme}://{request.url.netloc}"
        # single-language pages (cookie-switched only, not worth a separate
        # crawlable URL per language)
        single_lang_paths = ["/ingest", "/claims", "/aggregate", "/exclusions", "/trace"]
        # real per-language URLs -- these are what actually let Google index
        # the German/French content separately, which a cookie never could
        content_paths = ["/", "/chat", "/tutorial", "/assistant", "/updates"]
        urls = "".join(f"<url><loc>{origin}{p}</loc></url>" for p in single_lang_paths)
        urls += "".join(f"<url><loc>{origin}/{code}{p}</loc></url>" for code in LANGUAGES for p in content_paths)
        xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
        return Response(xml, media_type="application/xml")

    def _llm_client_or_none() -> LLMClient | None:
        try:
            return LLMClient(LLMConfig.from_env())
        except LLMError:
            return None

    # --- Chat (grounded: no evidence, no LLM call, no answer -- I10's
    # spirit, applied to a conversational surface). Stateless on the
    # server -- see dhra.chat's module docstring for why a public,
    # accountless demo deployment needs that. ------------------------------

    def _chat_page(request: Request, lang: str | None) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "chat.html", _ctx("chat", request, lang=lang, history=[], history_json="[]", llm_configured=_llm_client_or_none() is not None)
        )

    @app.get("/chat", response_class=HTMLResponse)
    def chat_get(request: Request) -> HTMLResponse:
        return _chat_page(request, lang=None)

    @app.get("/{lang}/chat", response_class=HTMLResponse)
    def chat_get_lang(request: Request, lang: str) -> HTMLResponse:
        lang = _valid_lang(lang)
        resp = _chat_page(request, lang=lang)
        resp.set_cookie(LANGUAGE_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp

    @app.post("/chat", response_class=HTMLResponse)
    def chat_post(request: Request, message: str = Form(...), history_json: str = Form("[]")) -> HTMLResponse:
        try:
            history = json.loads(history_json)
        except json.JSONDecodeError:
            history = []
        client = _llm_client_or_none()
        lang = resolve_language(request.cookies.get(LANGUAGE_COOKIE))
        result = chat_answer(repo, client, question=message, history=history, lang=lang)

        evidence_dicts = [
            {
                "text": p.text,
                "locator": {"item_id": p.locator.item_id, "rep_id": p.locator.rep_id, "start": p.locator.start, "end": p.locator.end},
            }
            for p in result.evidence
        ]
        new_turns = [
            {"role": "user", "text": message},
            {"role": "assistant", "text": result.answer, "evidence": evidence_dicts, "absence_note": result.absence_note, "llm_error": result.llm_error},
        ]
        updated_history = history + new_turns
        return templates.TemplateResponse(
            request,
            "chat.html",
            _ctx("chat", request, history=updated_history, history_json=json.dumps(updated_history), llm_configured=client is not None),
        )

    # --- Ingestion: manual_upload only (real network acquisition, e.g.
    # Zenodo, is ASK-gated and only reachable via dhra.mcp_server so far --
    # OPEN_QUESTIONS.md #23) ---------------------------------------------

    @app.get("/ingest", response_class=HTMLResponse)
    def ingest_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "ingest.html", _ctx("ingest", request))

    @app.post("/ingest")
    def ingest_submit(
        source_id: str = Form(...),
        access_basis: str = Form("public_domain"),
        licence_id: str = Form(""),
        original_reference: str = Form(""),
        text: str = Form(""),
        file: UploadFile | None = None,
    ) -> RedirectResponse:
        kwargs: dict[str, Any] = {
            "source_id": source_id,
            "access_basis": access_basis,
            "licence_id": licence_id or None,
            "original_reference": original_reference or None,
        }
        if file is not None and file.filename:
            data = file.file.read()
            name = file.filename.lower()
            if name.endswith(".pdf"):
                item_id, _rep_id = repo.ingest_pdf(data, **kwargs)
            elif name.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
                item_id, _rep_id = repo.ingest_image(data, **kwargs)
            elif name.endswith((".xml", ".tei")):
                item_id, _rep_id = repo.ingest_tei(data, **kwargs)
            else:
                item_id, _rep_id = repo.ingest_text(data.decode("utf-8", errors="replace"), **kwargs)
        elif text.strip():
            item_id, _rep_id = repo.ingest_text(text, **kwargs)
        else:
            raise HTTPException(status_code=400, detail="provide either text or a file")
        return RedirectResponse(f"/item/{item_id}", status_code=303)

    # --- Locator resolution (section 4.6: resolves in one call, or it's a bug) --

    @app.get("/locator/{item_id}/{rep_id}/{start}/{end}", response_class=HTMLResponse)
    def locator_detail(request: Request, item_id: str, rep_id: str, start: int, end: int) -> HTMLResponse:
        locator = Locator(item_id=item_id, rep_id=rep_id, start=start, end=end)
        try:
            passage = repo.resolve(locator)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        projection = repo.projection()
        item = projection.items.get(item_id)
        rep = projection.representations.get(rep_id)
        thread = annotations_for(repo, target_type="item", target_id=item_id)
        is_image = bool(item and item.media_type.startswith("image/"))
        return templates.TemplateResponse(
            request,
            "locator.html",
            _ctx("search", request, locator=locator, passage=passage, item=item, rep=rep, is_image=is_image, thread=thread),
        )

    @app.get("/item/{item_id}")
    def item_redirect(item_id: str) -> RedirectResponse:
        """Drill-down target for aggregate buckets (section 8.4): every
        element of an aggregate must open to its passages in one action."""
        projection = repo.projection()
        rep_ids = projection.reps_by_item.get(item_id, [])
        if not rep_ids:
            raise HTTPException(status_code=404, detail="item has no representations")
        rep = projection.representations[rep_ids[0]]
        return RedirectResponse(f"/locator/{item_id}/{rep_ids[0]}/0/{len(rep.text)}", status_code=307)

    @app.get("/blob/{item_id}")
    def blob(item_id: str) -> Response:
        projection = repo.projection()
        item = projection.items.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="no such item")
        data = repo.blobs.get(item.blob_sha256)
        return Response(content=data, media_type=item.media_type)

    @app.post("/annotate")
    def annotate(target_type: str = Form(...), target_id: str = Form(...), text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        add_annotation(repo, target_type=target_type, target_id=target_id, text=text, actor=actor)
        if target_type == "item":
            projection = repo.projection()
            rep_id = projection.reps_by_item.get(target_id, [None])[0]
            if rep_id:
                rep = projection.representations[rep_id]
                return RedirectResponse(f"/locator/{target_id}/{rep_id}/0/{len(rep.text)}", status_code=303)
        return RedirectResponse("/", status_code=303)

    # --- Exclusions (section 12: grouped by reason, one-click restore) -----

    @app.get("/exclusions", response_class=HTMLResponse)
    def exclusions(request: Request) -> HTMLResponse:
        projection = repo.projection()
        grouped: dict[str, list] = {}
        for item_id, excl in projection.active_exclusions.items():
            grouped.setdefault(excl.reason.value, []).append((item_id, excl))
        return templates.TemplateResponse(request, "exclusions.html", _ctx("exclusions", request, grouped=grouped))

    @app.post("/exclusions/{item_id}/restore")
    def restore(item_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        repo.restore_item(item_id=item_id, actor=actor)
        return RedirectResponse("/exclusions", status_code=303)

    # --- Literature watch (external, OpenAlex -- section 6 monitoring, ------
    # extended past the corpus boundary; see literature_watch.py docstring) --

    def _updates_page(request: Request, error: str, lang: str | None) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "updates.html",
            _ctx(
                "updates",
                request,
                lang=lang,
                queries=list_watch_queries(repo),
                candidates=list_candidates(repo),
                dismissed=list_dismissed_candidates(repo),
                error=error or None,
            ),
        )

    @app.get("/updates", response_class=HTMLResponse)
    def updates(request: Request, error: str = "") -> HTMLResponse:
        return _updates_page(request, error, lang=None)

    @app.get("/{lang}/updates", response_class=HTMLResponse)
    def updates_lang(request: Request, lang: str, error: str = "") -> HTMLResponse:
        lang = _valid_lang(lang)
        resp = _updates_page(request, error, lang=lang)
        resp.set_cookie(LANGUAGE_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp

    @app.post("/updates/queries")
    def updates_add_query(query_text: str = Form(...), actor: str = Form("researcher")) -> RedirectResponse:
        add_watch_query(repo, query_text=query_text, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/queries/{watch_id}/remove")
    def updates_remove_query(watch_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        remove_watch_query(repo, watch_id, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/check")
    def updates_check() -> RedirectResponse:
        try:
            check_for_updates(repo)
        except LiteratureWatchError as exc:
            return RedirectResponse(f"/updates?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/candidates/{work_id}/dismiss")
    def updates_dismiss(work_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        dismiss_candidate(repo, work_id, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/candidates/{work_id}/restore")
    def updates_restore(work_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        restore_candidate(repo, work_id, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    # --- Aggregate + bias (section 12: bias shown before aggregate data) ---

    @app.get("/aggregate", response_class=HTMLResponse)
    def aggregate(request: Request) -> HTMLResponse:
        result = aggregate_by_source(repo, expected_languages=expected_languages)
        return templates.TemplateResponse(request, "aggregate.html", _ctx("aggregate", request, result=result))

    # --- Claims (section 12: status as a code, never a number) -------------

    @app.get("/claims", response_class=HTMLResponse)
    def claims_list(request: Request) -> HTMLResponse:
        projection = repo.projection()
        claims = sorted(projection.claims.values(), key=lambda c: c.claim_id)
        return templates.TemplateResponse(request, "claims.html", _ctx("claims", request, claims=claims))

    @app.get("/claims/new", response_class=HTMLResponse)
    def claim_new(request: Request, item_id: str = "", rep_id: str = "", start: str = "", end: str = "") -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "claim_new.html",
            _ctx("claims", request, item_id=item_id, rep_id=rep_id, start=start, end=end),
        )

    @app.get("/claims/{claim_id}", response_class=HTMLResponse)
    def claim_detail(request: Request, claim_id: str) -> HTMLResponse:
        assessment = repo.get_claim_assessment(claim_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="no such claim")
        history = repo.claim_history(claim_id)
        return templates.TemplateResponse(request, "claim_detail.html", _ctx("claims", request, assessment=assessment, history=history))

    def _parse_locators(raw: str) -> list[Locator]:
        """One 'item_id,rep_id,start,end' per line -- the plain-text
        locator-entry format the claim form posts."""
        locators = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 4:
                raise HTTPException(status_code=400, detail=f"malformed locator line: {line!r}")
            item_id, rep_id, start, end = parts
            locators.append(Locator(item_id=item_id, rep_id=rep_id, start=int(start), end=int(end)))
        return locators

    @app.post("/claims/assess")
    def claim_assess(
        claim_id: str = Form(...),
        claim_text: str = Form(...),
        actor: str = Form("researcher"),
        supporting: str = Form(""),
        contradicting: str = Form(""),
        negating: str = Form(""),
        run_independence: bool = Form(False),
    ) -> RedirectResponse:
        supporting_locs = _parse_locators(supporting)
        contradicting_locs = _parse_locators(contradicting)
        negating_locs = _parse_locators(negating)

        if run_independence and supporting_locs:
            repo.assess_claim_with_independence(claim_id=claim_id, claim_text=claim_text, supporting=supporting_locs, actor=actor)
        else:
            repo.assess_claim(
                claim_id=claim_id,
                claim_text=claim_text,
                supporting=supporting_locs,
                contradicting=contradicting_locs,
                negating=negating_locs,
            )
        return RedirectResponse(f"/claims/{claim_id}", status_code=303)

    # --- Trace (section 12: decision-level trace one interaction away) -----

    @app.get("/trace", response_class=HTMLResponse)
    def trace(request: Request, task: str | None = None) -> HTMLResponse:
        summary = trace_summary(repo.events, task)
        decisions = trace_decisions(repo.events, task)
        raw = trace_raw(repo.events, task) if task else []
        return templates.TemplateResponse(
            request,
            "trace.html",
            _ctx("trace", request, task=task, summary=summary, decisions=decisions, raw=raw),
        )

    def _tutorial_page(request: Request, lang: str | None) -> HTMLResponse:
        return templates.TemplateResponse(request, "tutorial.html", _ctx("tutorial", request, lang=lang))

    @app.get("/tutorial", response_class=HTMLResponse)
    def tutorial(request: Request) -> HTMLResponse:
        return _tutorial_page(request, lang=None)

    @app.get("/{lang}/tutorial", response_class=HTMLResponse)
    def tutorial_lang(request: Request, lang: str) -> HTMLResponse:
        lang = _valid_lang(lang)
        resp = _tutorial_page(request, lang=lang)
        resp.set_cookie(LANGUAGE_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp

    # --- Research & Teaching assistant (LLM-backed, section 10's boundary:
    # the model only ever proposes -- see dhra.llm/research_assistant/
    # teaching/peer_review) -------------------------------------------------

    def _assistant_page(request: Request, lang: str | None) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "assistant.html",
            _ctx(
                "assistant",
                request,
                lang=lang,
                wide=True,
                llm_configured=_llm_client_or_none() is not None,
                research_drafts=list_drafts(repo, kinds=RESEARCH_DRAFT_KINDS),
                teaching_drafts=list_drafts(repo, kinds=TEACHING_DRAFT_KINDS),
            ),
        )

    @app.get("/assistant", response_class=HTMLResponse)
    def assistant(request: Request) -> HTMLResponse:
        return _assistant_page(request, lang=None)

    @app.get("/{lang}/assistant", response_class=HTMLResponse)
    def assistant_lang(request: Request, lang: str) -> HTMLResponse:
        lang = _valid_lang(lang)
        resp = _assistant_page(request, lang=lang)
        resp.set_cookie(LANGUAGE_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp

    def _require_llm() -> LLMClient:
        client = _llm_client_or_none()
        if client is None:
            raise HTTPException(status_code=503, detail="No LLM backend configured -- set DHRA_GLM_BASE_URL and DHRA_GLM_API_KEY.")
        return client

    @app.post("/assistant/research-questions")
    def assistant_research_questions(context_query: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        try:
            suggest_research_questions(repo, client, context_query=context_query, actor=actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/peer-review")
    def assistant_peer_review(paper_text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        try:
            review_paper(repo, client, paper_text=paper_text, actor=actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/exam-questions")
    def assistant_exam_questions(source_text: str = Form(...), n_questions: int = Form(5), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        try:
            draft_exam_questions(repo, client, source_text=source_text, n_questions=n_questions, actor=actor)
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/rubric")
    def assistant_rubric(paper_text: str = Form(...), rubric_text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        try:
            assess_paper_against_rubric(repo, client, paper_text=paper_text, rubric_text=rubric_text, actor=actor)
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/reading-list")
    def assistant_reading_list(course_topic: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        try:
            draft_reading_list(repo, client, course_topic=course_topic, actor=actor)
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    return app
