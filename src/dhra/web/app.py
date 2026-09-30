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

v2 nav (RESEARCH / SOURCES / AUDIT / TEACHING, see base.html) replaced a
flat 10-link list -- `/` is now a dashboard (was the search screen;
search moved to `/evidence`), and Research/Teaching split into separate
sections/routes (`/assistant` vs `/teaching`) instead of one page with
two columns.

Accounts (optional -- `accounts_dir=None` is single-tenant, unchanged
behaviour): every route resolves its own `DHRARepo` via `_current_repo
(request)` instead of closing over one shared `repo` directly. No
session/no accounts configured -> the shared `repo` (the public/guest
corpus, unchanged); a valid session -> that account's own, isolated
`DHRARepo` store. See `dhra.accounts`/`dhra.web.session`.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dhra.accounts import Account, AccountsError, AccountStore
from dhra.aggregate import aggregate_by_source
from dhra.annotation import add_annotation, annotations_for
from dhra.bias import compute_bias_report
from dhra.chat import answer as chat_answer
from dhra.disconfirm import propose_and_run_disconfirmation
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
from dhra.provenance import claim_provenance
from dhra.repo import DHRARepo
from dhra.research_assistant import suggest_research_questions
from dhra.status import Status
from dhra.teaching import assess_paper_against_rubric, draft_exam_questions, draft_reading_list
from dhra.web.i18n import LANGUAGE_LABELS, LANGUAGES, resolve_language, translate
from dhra.web.session import SESSION_COOKIE, SESSION_MAX_AGE, make_serializer, session_cookie_value, user_id_from_cookie
from dhra.trace import audit_narrative, trace_decisions, trace_raw, trace_summary
from dhra.websearch import WebSearchClient, WebSearchConfig, WebSearchError

RESEARCH_DRAFT_KINDS = ("research_questions", "peer_review", "disconfirmation")
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

STATUS_LABEL_KEYS = {
    Status.ATTESTED: "status_label.attested",
    Status.CORROBORATED: "status_label.corroborated",
    Status.INFERRED: "status_label.inferred",
    Status.CONTESTED: "status_label.contested",
    Status.SINGLE_WITNESS: "status_label.single_witness",
    Status.UNSUPPORTED: "status_label.unsupported",
    Status.NEGATIVE: "status_label.negative",
    Status.OUT_OF_SCOPE: "status_label.out_of_scope",
}

# UI-level grouping of the existing (more granular) ExclusionReason values
# into the 5 display buckets a researcher actually scans for -- not a
# change to the enum itself: events.jsonl is append-only, so past
# exclusion events' stored reason values are immutable history.
EXCLUSION_DISPLAY_GROUPS: dict[str, tuple[ExclusionReason, ...]] = {
    "duplicate": (ExclusionReason.DESCENT_CLUSTER_MEMBER,),
    "low_quality": (ExclusionReason.BELOW_QUALITY, ExclusionReason.BELOW_RELEVANCE, ExclusionReason.FORMAT_UNREADABLE),
    "outside_scope": (ExclusionReason.OUT_OF_DATE_RANGE, ExclusionReason.WRONG_LANGUAGE, ExclusionReason.DATE_UNRESOLVED),
    "acquisition_problem": (ExclusionReason.ACCESS_DENIED,),
    "other": (ExclusionReason.RESEARCHER_EXCLUDED,),
}
_REASON_TO_GROUP = {reason: group for group, reasons in EXCLUSION_DISPLAY_GROUPS.items() for reason in reasons}

LANGUAGE_COOKIE = "dhra_lang"


def build_app(
    repo: DHRARepo,
    *,
    expected_languages: set[str] | None = None,
    demo_banner: str | None = None,
    accounts_dir: Path | None = None,
    session_secret: str | None = None,
) -> FastAPI:
    app = FastAPI(title="DHRA", description="Digital Humanities Research Assistant -- local evidence browser")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["status_meaning"] = lambda s, lang: translate(lang, STATUS_MEANING_KEYS.get(Status(s), ""))
    templates.env.globals["status_tone"] = lambda s: "warn" if Status(s) in (Status.CONTESTED, Status.UNSUPPORTED, Status.NEGATIVE) else "ok"
    templates.env.globals["status_label"] = lambda s, lang: translate(lang, STATUS_LABEL_KEYS.get(Status(s), ""))
    templates.env.globals["languages"] = LANGUAGES
    templates.env.globals["language_labels"] = LANGUAGE_LABELS
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Simultaneous Interpreter: a separate live-speech tool (unrelated
    # domain, no code/data sharing with DHRA's own evidence/claims model),
    # mounted as its own sub-application rather than folded into DHRA's
    # routes/templates - it keeps its own FastAPI app, WebSocket rooms, and
    # frontend, just served under DHRA's own domain instead of a separate
    # Render deployment. See dhra/interpreter/frontend/index.html's `BASE`
    # constant for the corresponding frontend-side fix (it derives its API/
    # WebSocket paths from location.pathname so they resolve correctly
    # whether this ends up mounted here or served standalone).
    from dhra.interpreter.api.app import app as interpreter_app

    app.mount("/interpreter", interpreter_app)

    # --- Accounts (optional) ------------------------------------------------
    # `accounts_dir=None` (the default -- desktop.py never passes it, and
    # neither does any pre-existing caller) keeps every route's behaviour
    # byte-for-byte identical to before accounts existed: `_current_repo`
    # always returns the one shared `repo`. When set, a session cookie
    # (signed, see dhra.web.session) selects a per-account DHRARepo instead.
    account_store = AccountStore(accounts_dir) if accounts_dir is not None else None
    _serializer = make_serializer(session_secret or secrets.token_urlsafe(32)) if account_store is not None else None
    _user_repos: dict[str, DHRARepo] = {}

    def _current_user(request: Request) -> Account | None:
        if account_store is None or _serializer is None:
            return None
        user_id = user_id_from_cookie(_serializer, request.cookies.get(SESSION_COOKIE))
        if user_id is None:
            return None
        return account_store.get_by_id(user_id)

    def _current_repo(request: Request) -> DHRARepo:
        """No accounts configured, or no valid session -> the shared
        `repo` (the public/guest corpus -- unauthenticated visitors keep
        using the site exactly as before accounts existed). A logged-in
        account -> that account's own store, lazily constructed once and
        cached per user id for the life of this process (DHRARepo
        construction is cheap -- two mkdirs and a touch -- but there's no
        reason to repeat it every request)."""
        account = _current_user(request)
        if account is None:
            return repo
        if account.user_id not in _user_repos:
            _user_repos[account.user_id] = DHRARepo(account_store.user_store_path(account.user_id))  # type: ignore[union-attr]
        return _user_repos[account.user_id]

    def _set_session_cookie(resp: RedirectResponse, account: Account) -> RedirectResponse:
        assert _serializer is not None
        resp.set_cookie(
            SESSION_COOKIE,
            session_cookie_value(_serializer, account.user_id),
            max_age=SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
        return resp

    def _ctx(active: str, request: Request, *, lang: str | None = None, **extra: Any) -> dict[str, Any]:
        """`lang=None` (every pre-existing call site): derived from the
        `dhra_lang` cookie, as before -- one URL, language picked client-side.
        `lang=<code>` (the content routes below): the URL itself is the
        language -- real, distinct, crawlable pages per language, which a
        cookie-only switch can never give a search engine (it never sends
        cookies, so it would only ever see English)."""
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
        current_repo = _current_repo(request)
        return {
            "active": active,
            "corpus_version": current_repo.corpus_version().manifest_hash[:12],
            "demo_banner": demo_banner,
            "lang": lang,
            "lang_urls": lang_urls,
            "lang_url_based": lang_url_based,
            "t": lambda key, **kw: translate(lang, key, **kw),
            "current_user": _current_user(request),
            "accounts_enabled": account_store is not None,
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

    # --- Signup / login / logout --------------------------------------------

    def _require_accounts() -> AccountStore:
        if account_store is None:
            raise HTTPException(status_code=404, detail="Accounts are not enabled on this deployment.")
        return account_store

    @app.get("/signup", response_class=HTMLResponse)
    def signup_form(request: Request) -> HTMLResponse:
        _require_accounts()
        return templates.TemplateResponse(request, "signup.html", _ctx("", request, error=None))

    @app.post("/signup", response_model=None)
    def signup_submit(
        request: Request, username: str = Form(...), password: str = Form(...), password_confirm: str = Form(...)
    ) -> HTMLResponse | RedirectResponse:
        store = _require_accounts()
        if password != password_confirm:
            return templates.TemplateResponse(request, "signup.html", _ctx("", request, error="Passwords don't match."))
        try:
            account = store.create_account(username, password)
        except AccountsError as exc:
            return templates.TemplateResponse(request, "signup.html", _ctx("", request, error=str(exc)))
        return _set_session_cookie(RedirectResponse("/", status_code=303), account)

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request) -> HTMLResponse:
        _require_accounts()
        return templates.TemplateResponse(request, "login.html", _ctx("", request, error=None))

    @app.post("/login", response_model=None)
    def login_submit(request: Request, username: str = Form(...), password: str = Form(...)) -> HTMLResponse | RedirectResponse:
        store = _require_accounts()
        try:
            account = store.authenticate(username, password)
        except AccountsError as exc:
            return templates.TemplateResponse(request, "login.html", _ctx("", request, error=str(exc)))
        return _set_session_cookie(RedirectResponse("/", status_code=303), account)

    @app.post("/logout")
    def logout(request: Request) -> RedirectResponse:
        resp = RedirectResponse("/", status_code=303)
        resp.delete_cookie(SESSION_COOKIE)
        return resp

    # --- Dashboard (was the empty state of search.html; search itself is
    # now /evidence -- see doc review: the homepage should read as a
    # research workspace, not a bare search box) --------------------------

    def _dashboard_page(request: Request, lang: str | None) -> HTMLResponse:
        repo = _current_repo(request)
        projection = repo.projection()
        claims = list(projection.claims.values())
        n_contested = sum(1 for c in claims if c.status == Status.CONTESTED)
        recent = list(reversed(audit_narrative(repo.events)[-8:]))
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            _ctx(
                "overview",
                request,
                lang=lang,
                n_sources=len(projection.active_item_ids()),
                n_claims=len(claims),
                n_contested=n_contested,
                recent=recent,
            ),
        )

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request) -> HTMLResponse:
        return _dashboard_page(request, lang=None)

    @app.get("/{lang}/", response_class=HTMLResponse)
    def home_lang(request: Request, lang: str) -> HTMLResponse:
        lang = _valid_lang(lang)
        resp = _dashboard_page(request, lang=lang)
        resp.set_cookie(LANGUAGE_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
        return resp

    # --- Evidence search (section 12: evidence above, narrative below;
    # was search.html's q-driven view) -------------------------------------

    def _evidence_page(request: Request, q: str | None, lang: str | None) -> HTMLResponse:
        repo = _current_repo(request)
        response = None
        if q:
            response = evidence_search(repo, q)
        return templates.TemplateResponse(request, "evidence.html", _ctx("evidence", request, lang=lang, q=q or "", response=response))

    @app.get("/evidence", response_class=HTMLResponse)
    def evidence_page(request: Request, q: str | None = None) -> HTMLResponse:
        return _evidence_page(request, q, lang=None)

    @app.get("/{lang}/evidence", response_class=HTMLResponse)
    def evidence_page_lang(request: Request, lang: str, q: str | None = None) -> HTMLResponse:
        lang = _valid_lang(lang)
        resp = _evidence_page(request, q, lang=lang)
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
        single_lang_paths = ["/ingest", "/claims", "/aggregate", "/exclusions", "/trace", "/sources", "/teaching"]
        # real per-language URLs -- these are what actually let Google index
        # the German/French content separately, which a cookie never could
        content_paths = [
            "/", "/chat", "/tutorial", "/assistant", "/updates", "/evidence",
            "/how-it-works", "/about", "/evidence-based-research",
            "/digital-humanities-research", "/research-assistant", "/claims-and-evidence",
            "/digital-humanities-ai", "/historical-document-research", "/documentation", "/blog", "/welcome",
        ]
        urls = "".join(f"<url><loc>{origin}{p}</loc></url>" for p in single_lang_paths)
        urls += "".join(f"<url><loc>{origin}/{code}{p}</loc></url>" for code in LANGUAGES for p in content_paths)
        xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
        return Response(xml, media_type="application/xml")

    def _llm_client_or_none() -> LLMClient | None:
        try:
            return LLMClient(LLMConfig.from_env())
        except LLMError:
            return None

    def _websearch_client_or_none() -> WebSearchClient | None:
        try:
            return WebSearchClient(WebSearchConfig.from_env())
        except WebSearchError:
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
        repo = _current_repo(request)
        try:
            history = json.loads(history_json)
        except json.JSONDecodeError:
            history = []
        client = _llm_client_or_none()
        lang = resolve_language(request.cookies.get(LANGUAGE_COOKIE))
        result = chat_answer(repo, client, question=message, history=history, lang=lang)

        # Evidence-first cards need score/rationale/source alongside the
        # excerpt -- Passage already carries all three, this just stops
        # dropping them on the way into the round-tripped history JSON.
        projection = repo.projection()
        evidence_dicts = [
            {
                "text": p.text,
                "locator": {"item_id": p.locator.item_id, "rep_id": p.locator.rep_id, "start": p.locator.start, "end": p.locator.end},
                "score": p.score,
                "rationale": p.rationale,
                "source_label": projection.items[p.locator.item_id].acquisition.source_id if p.locator.item_id in projection.items else None,
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
        request: Request,
        source_id: str = Form(...),
        access_basis: str = Form("public_domain"),
        licence_id: str = Form(""),
        original_reference: str = Form(""),
        text: str = Form(""),
        file: UploadFile | None = None,
    ) -> RedirectResponse:
        repo = _current_repo(request)
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
        repo = _current_repo(request)
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
            _ctx("evidence", request, locator=locator, passage=passage, item=item, rep=rep, is_image=is_image, thread=thread),
        )

    @app.get("/item/{item_id}")
    def item_redirect(request: Request, item_id: str) -> RedirectResponse:
        """Drill-down target for aggregate buckets (section 8.4): every
        element of an aggregate must open to its passages in one action."""
        repo = _current_repo(request)
        projection = repo.projection()
        rep_ids = projection.reps_by_item.get(item_id, [])
        if not rep_ids:
            raise HTTPException(status_code=404, detail="item has no representations")
        rep = projection.representations[rep_ids[0]]
        return RedirectResponse(f"/locator/{item_id}/{rep_ids[0]}/0/{len(rep.text)}", status_code=307)

    @app.get("/blob/{item_id}")
    def blob(request: Request, item_id: str) -> Response:
        repo = _current_repo(request)
        projection = repo.projection()
        item = projection.items.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="no such item")
        data = repo.blobs.get(item.blob_sha256)
        return Response(content=data, media_type=item.media_type)

    @app.post("/annotate")
    def annotate(request: Request, target_type: str = Form(...), target_id: str = Form(...), text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        repo = _current_repo(request)
        add_annotation(repo, target_type=target_type, target_id=target_id, text=text, actor=actor)
        if target_type == "item":
            projection = repo.projection()
            rep_id = projection.reps_by_item.get(target_id, [None])[0]
            if rep_id:
                rep = projection.representations[rep_id]
                return RedirectResponse(f"/locator/{target_id}/{rep_id}/0/{len(rep.text)}", status_code=303)
        return RedirectResponse("/", status_code=303)

    # --- Sources (SOURCES > Corpus: browse framing, vs. Analysis's bias-
    # report framing on the same underlying aggregate_by_source data) -----

    @app.get("/sources", response_class=HTMLResponse)
    def sources(request: Request) -> HTMLResponse:
        repo = _current_repo(request)
        result = aggregate_by_source(repo, expected_languages=expected_languages)
        return templates.TemplateResponse(request, "sources.html", _ctx("sources", request, result=result))

    # --- Exclusions (section 12: grouped by reason, one-click restore) -----

    @app.get("/exclusions", response_class=HTMLResponse)
    def exclusions(request: Request) -> HTMLResponse:
        repo = _current_repo(request)
        projection = repo.projection()
        grouped: dict[str, list] = {group: [] for group in EXCLUSION_DISPLAY_GROUPS}
        for item_id, excl in projection.active_exclusions.items():
            group = _REASON_TO_GROUP.get(excl.reason, "other")
            grouped[group].append((item_id, excl))
        return templates.TemplateResponse(request, "exclusions.html", _ctx("exclusions", request, grouped=grouped))

    @app.post("/exclusions/{item_id}/restore")
    def restore(request: Request, item_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        repo = _current_repo(request)
        repo.restore_item(item_id=item_id, actor=actor)
        return RedirectResponse("/exclusions", status_code=303)

    # --- Literature watch (external, OpenAlex -- section 6 monitoring, ------
    # extended past the corpus boundary; see literature_watch.py docstring) --

    def _updates_page(request: Request, error: str, lang: str | None) -> HTMLResponse:
        repo = _current_repo(request)
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
    def updates_add_query(request: Request, query_text: str = Form(...), actor: str = Form("researcher")) -> RedirectResponse:
        repo = _current_repo(request)
        add_watch_query(repo, query_text=query_text, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/queries/{watch_id}/remove")
    def updates_remove_query(request: Request, watch_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        repo = _current_repo(request)
        remove_watch_query(repo, watch_id, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/check")
    def updates_check(request: Request) -> RedirectResponse:
        repo = _current_repo(request)
        try:
            check_for_updates(repo)
        except LiteratureWatchError as exc:
            return RedirectResponse(f"/updates?error={quote(str(exc))}", status_code=303)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/candidates/{work_id}/dismiss")
    def updates_dismiss(request: Request, work_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        repo = _current_repo(request)
        dismiss_candidate(repo, work_id, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    @app.post("/updates/candidates/{work_id}/restore")
    def updates_restore(request: Request, work_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        repo = _current_repo(request)
        restore_candidate(repo, work_id, actor=actor)
        return RedirectResponse("/updates", status_code=303)

    # --- Aggregate + bias (section 12: bias shown before aggregate data) ---

    @app.get("/aggregate", response_class=HTMLResponse)
    def aggregate(request: Request) -> HTMLResponse:
        repo = _current_repo(request)
        result = aggregate_by_source(repo, expected_languages=expected_languages)
        return templates.TemplateResponse(request, "aggregate.html", _ctx("analysis", request, result=result))

    # --- Claims (section 12: status as a code, never a number) -------------

    @app.get("/claims", response_class=HTMLResponse)
    def claims_list(request: Request) -> HTMLResponse:
        repo = _current_repo(request)
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
        repo = _current_repo(request)
        assessment = repo.get_claim_assessment(claim_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="no such claim")
        history = repo.claim_history(claim_id)
        provenance = claim_provenance(repo, assessment)
        return templates.TemplateResponse(
            request, "claim_detail.html", _ctx("claims", request, assessment=assessment, history=history, provenance=provenance)
        )

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
        request: Request,
        claim_id: str = Form(...),
        claim_text: str = Form(...),
        actor: str = Form("researcher"),
        supporting: str = Form(""),
        contradicting: str = Form(""),
        negating: str = Form(""),
        run_independence: bool = Form(False),
    ) -> RedirectResponse:
        repo = _current_repo(request)
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

    # --- Trace / Research Audit Trail (section 12: decision-level trace
    # one interaction away) --------------------------------------------------

    @app.get("/trace", response_class=HTMLResponse)
    def trace(request: Request, task: str | None = None) -> HTMLResponse:
        repo = _current_repo(request)
        summary = trace_summary(repo.events, task)
        decisions = trace_decisions(repo.events, task)
        raw = trace_raw(repo.events, task) if task else []
        narrative = audit_narrative(repo.events, task)
        return templates.TemplateResponse(
            request,
            "trace.html",
            _ctx("trace", request, task=task, summary=summary, decisions=decisions, raw=raw, narrative=narrative),
        )

    @app.get("/trace/export", response_class=Response)
    def trace_export(request: Request, task: str | None = None) -> Response:
        repo = _current_repo(request)
        narrative = audit_narrative(repo.events, task)
        lines = [f"{e.ts}\t{e.type}\t{e.text}" for e in narrative]
        return Response("\n".join(lines) + "\n", media_type="text/plain")

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

    # --- Content pages (SEO -- real crawlable content, not just app chrome).
    # Registered from one table instead of a route-pair per page -- eleven
    # pages (three from the v2 pass, eight added after it: the doc review's
    # remaining keyword pages, a documentation index, a blog with a real
    # inaugural post, and a marketing landing page now that accounts exist
    # to give "sign up" somewhere real to send a first-time visitor). -------

    CONTENT_PAGES: list[tuple[str, str]] = [
        ("how-it-works", "how_it_works.html"),
        ("about", "about.html"),
        ("evidence-based-research", "evidence_based_research.html"),
        ("digital-humanities-research", "digital_humanities_research.html"),
        ("research-assistant", "research_assistant_overview.html"),
        ("claims-and-evidence", "claims_and_evidence.html"),
        ("digital-humanities-ai", "digital_humanities_ai.html"),
        ("historical-document-research", "historical_document_research.html"),
        ("documentation", "documentation.html"),
        ("blog", "blog.html"),
        ("welcome", "welcome.html"),
    ]

    def _content_page(request: Request, template_name: str, lang: str | None) -> HTMLResponse:
        return templates.TemplateResponse(request, template_name, _ctx("", request, lang=lang))

    def _register_content_page(slug: str, template_name: str) -> None:
        async def page(request: Request) -> HTMLResponse:
            return _content_page(request, template_name, lang=None)

        async def page_lang(request: Request, lang: str) -> HTMLResponse:
            lang = _valid_lang(lang)
            resp = _content_page(request, template_name, lang=lang)
            resp.set_cookie(LANGUAGE_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="lax")
            return resp

        app.add_api_route(f"/{slug}", page, methods=["GET"], response_class=HTMLResponse)
        app.add_api_route(f"/{{lang}}/{slug}", page_lang, methods=["GET"], response_class=HTMLResponse)

    for _slug, _template_name in CONTENT_PAGES:
        _register_content_page(_slug, _template_name)

    # --- Onboarding (stateless -- no accounts to save progress against;
    # step tracked entirely via ?step=N, see start.html) --------------------

    @app.get("/start", response_class=HTMLResponse)
    def start(request: Request, step: int = 1, topic: str = "", action: str = "") -> HTMLResponse:
        repo = _current_repo(request)
        projection = repo.projection()
        return templates.TemplateResponse(
            request,
            "start.html",
            _ctx(
                "",
                request,
                step=step,
                topic=topic,
                action=action,
                n_sources=len(projection.active_item_ids()),
                n_claims=len(projection.claims),
            ),
        )

    # --- Research & Teaching assistant (LLM-backed, section 10's boundary:
    # the model only ever proposes -- see dhra.llm/research_assistant/
    # teaching/peer_review). Split into two routes/nav sections (v2): -------

    def _assistant_page(request: Request, lang: str | None) -> HTMLResponse:
        repo = _current_repo(request)
        return templates.TemplateResponse(
            request,
            "assistant.html",
            _ctx(
                "research_assistant",
                request,
                lang=lang,
                llm_configured=_llm_client_or_none() is not None,
                research_drafts=list_drafts(repo, kinds=RESEARCH_DRAFT_KINDS),
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

    @app.get("/teaching", response_class=HTMLResponse)
    def teaching(request: Request) -> HTMLResponse:
        repo = _current_repo(request)
        return templates.TemplateResponse(
            request,
            "teaching.html",
            _ctx(
                "teaching",
                request,
                llm_configured=_llm_client_or_none() is not None,
                websearch_configured=_websearch_client_or_none() is not None,
                teaching_drafts=list_drafts(repo, kinds=TEACHING_DRAFT_KINDS),
            ),
        )

    def _require_llm() -> LLMClient:
        client = _llm_client_or_none()
        if client is None:
            raise HTTPException(status_code=503, detail="No LLM backend configured -- set DHRA_GLM_BASE_URL and DHRA_GLM_API_KEY.")
        return client

    @app.post("/assistant/research-questions")
    def assistant_research_questions(request: Request, context_query: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        repo = _current_repo(request)
        client = _require_llm()
        try:
            suggest_research_questions(repo, client, context_query=context_query, actor=actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/disconfirm")
    def assistant_disconfirm(request: Request, claim_text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        repo = _current_repo(request)
        client = _require_llm()
        try:
            propose_and_run_disconfirmation(repo, client, claim_text=claim_text, actor=actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/peer-review")
    def assistant_peer_review(request: Request, paper_text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        repo = _current_repo(request)
        client = _require_llm()
        try:
            review_paper(repo, client, paper_text=paper_text, actor=actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/teaching/exam-questions")
    def teaching_exam_questions(request: Request, source_text: str = Form(...), n_questions: int = Form(5), actor: str = Form(...)) -> RedirectResponse:
        repo = _current_repo(request)
        client = _require_llm()
        try:
            draft_exam_questions(repo, client, source_text=source_text, n_questions=n_questions, actor=actor)
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/teaching", status_code=303)

    @app.post("/teaching/rubric")
    def teaching_rubric(request: Request, paper_text: str = Form(...), rubric_text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        repo = _current_repo(request)
        client = _require_llm()
        try:
            assess_paper_against_rubric(repo, client, paper_text=paper_text, rubric_text=rubric_text, actor=actor)
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/teaching", status_code=303)

    @app.post("/teaching/reading-list")
    def teaching_reading_list(request: Request, course_topic: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        repo = _current_repo(request)
        client = _require_llm()
        try:
            draft_reading_list(repo, client, course_topic=course_topic, actor=actor, websearch_client=_websearch_client_or_none())
        except LLMError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return RedirectResponse("/teaching", status_code=303)

    return app
