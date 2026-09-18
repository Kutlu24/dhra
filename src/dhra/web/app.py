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
from dhra.llm import LLMClient, LLMConfig, LLMError
from dhra.models import ExclusionReason, Locator
from dhra.peer_review import review_paper
from dhra.repo import DHRARepo
from dhra.research_assistant import suggest_research_questions
from dhra.status import Status
from dhra.teaching import assess_paper_against_rubric, draft_exam_questions, draft_reading_list
from dhra.trace import trace_decisions, trace_raw, trace_summary

RESEARCH_DRAFT_KINDS = ("research_questions", "peer_review")
TEACHING_DRAFT_KINDS = ("exam_questions", "rubric_assessment", "reading_list")

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

STATUS_MEANINGS = {
    Status.ATTESTED: "E1 -- explicitly stated in a source in the corpus.",
    Status.CORROBORATED: "E2 -- attested in >=2 sources that passed an independence check.",
    Status.INFERRED: "E3 -- follows from E1/E2 by a stated chain.",
    Status.CONTESTED: "E4 -- sources in the corpus disagree.",
    Status.SINGLE_WITNESS: "E5 -- one source, reliability unestablished.",
    Status.UNSUPPORTED: "E6 -- not found; scope of search stated. Not evidence of non-occurrence.",
    Status.NEGATIVE: "E7 -- a source positively asserts non-occurrence.",
    Status.OUT_OF_SCOPE: "E8 -- this corpus cannot in principle address this claim.",
}


def build_app(repo: DHRARepo, *, expected_languages: set[str] | None = None, demo_banner: str | None = None) -> FastAPI:
    app = FastAPI(title="DHRA", description="Digital Humanities Research Agent -- local evidence browser")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals["status_meaning"] = lambda s: STATUS_MEANINGS.get(Status(s), "")
    templates.env.globals["status_tone"] = lambda s: "warn" if Status(s) in (Status.CONTESTED, Status.UNSUPPORTED, Status.NEGATIVE) else "ok"
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def _ctx(active: str, **extra: Any) -> dict[str, Any]:
        return {
            "active": active,
            "corpus_version": repo.corpus_version().manifest_hash[:12],
            "demo_banner": demo_banner,
            **extra,
        }

    # --- Home / search (section 12: evidence above, narrative below) -------

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, q: str | None = None) -> HTMLResponse:
        response = None
        if q:
            response = evidence_search(repo, q)
        return templates.TemplateResponse(request, "search.html", _ctx("search", q=q or "", response=response))

    def _llm_client_or_none() -> LLMClient | None:
        try:
            return LLMClient(LLMConfig.from_env())
        except LLMError:
            return None

    # --- Chat (grounded: no evidence, no LLM call, no answer -- I10's
    # spirit, applied to a conversational surface). Stateless on the
    # server -- see dhra.chat's module docstring for why a public,
    # accountless demo deployment needs that. ------------------------------

    @app.get("/chat", response_class=HTMLResponse)
    def chat_get(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "chat.html", _ctx("chat", history=[], history_json="[]", llm_configured=_llm_client_or_none() is not None)
        )

    @app.post("/chat", response_class=HTMLResponse)
    def chat_post(request: Request, message: str = Form(...), history_json: str = Form("[]")) -> HTMLResponse:
        try:
            history = json.loads(history_json)
        except json.JSONDecodeError:
            history = []
        client = _llm_client_or_none()
        result = chat_answer(repo, client, question=message, history=history)

        evidence_dicts = [
            {
                "text": p.text,
                "locator": {"item_id": p.locator.item_id, "rep_id": p.locator.rep_id, "start": p.locator.start, "end": p.locator.end},
            }
            for p in result.evidence
        ]
        new_turns = [
            {"role": "user", "text": message},
            {"role": "assistant", "text": result.answer, "evidence": evidence_dicts, "absence_note": result.absence_note},
        ]
        updated_history = history + new_turns
        return templates.TemplateResponse(
            request,
            "chat.html",
            _ctx("chat", history=updated_history, history_json=json.dumps(updated_history), llm_configured=client is not None),
        )

    # --- Ingestion: manual_upload only (real network acquisition, e.g.
    # Zenodo, is ASK-gated and only reachable via dhra.mcp_server so far --
    # OPEN_QUESTIONS.md #23) ---------------------------------------------

    @app.get("/ingest", response_class=HTMLResponse)
    def ingest_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "ingest.html", _ctx("ingest"))

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
            _ctx("search", locator=locator, passage=passage, item=item, rep=rep, is_image=is_image, thread=thread),
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
        return templates.TemplateResponse(request, "exclusions.html", _ctx("exclusions", grouped=grouped))

    @app.post("/exclusions/{item_id}/restore")
    def restore(item_id: str, actor: str = Form("researcher")) -> RedirectResponse:
        repo.restore_item(item_id=item_id, actor=actor)
        return RedirectResponse("/exclusions", status_code=303)

    # --- Aggregate + bias (section 12: bias shown before aggregate data) ---

    @app.get("/aggregate", response_class=HTMLResponse)
    def aggregate(request: Request) -> HTMLResponse:
        result = aggregate_by_source(repo, expected_languages=expected_languages)
        return templates.TemplateResponse(request, "aggregate.html", _ctx("aggregate", result=result))

    # --- Claims (section 12: status as a code, never a number) -------------

    @app.get("/claims", response_class=HTMLResponse)
    def claims_list(request: Request) -> HTMLResponse:
        projection = repo.projection()
        claims = sorted(projection.claims.values(), key=lambda c: c.claim_id)
        return templates.TemplateResponse(request, "claims.html", _ctx("claims", claims=claims))

    @app.get("/claims/new", response_class=HTMLResponse)
    def claim_new(request: Request, item_id: str = "", rep_id: str = "", start: str = "", end: str = "") -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "claim_new.html",
            _ctx("claims", item_id=item_id, rep_id=rep_id, start=start, end=end),
        )

    @app.get("/claims/{claim_id}", response_class=HTMLResponse)
    def claim_detail(request: Request, claim_id: str) -> HTMLResponse:
        assessment = repo.get_claim_assessment(claim_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="no such claim")
        history = repo.claim_history(claim_id)
        return templates.TemplateResponse(request, "claim_detail.html", _ctx("claims", assessment=assessment, history=history))

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
            _ctx("trace", task=task, summary=summary, decisions=decisions, raw=raw),
        )

    @app.get("/tutorial", response_class=HTMLResponse)
    def tutorial(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "tutorial.html", _ctx("tutorial"))

    # --- Research & Teaching assistant (LLM-backed, section 10's boundary:
    # the model only ever proposes -- see dhra.llm/research_assistant/
    # teaching/peer_review) -------------------------------------------------

    @app.get("/assistant", response_class=HTMLResponse)
    def assistant(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "assistant.html",
            _ctx(
                "assistant",
                wide=True,
                llm_configured=_llm_client_or_none() is not None,
                research_drafts=list_drafts(repo, kinds=RESEARCH_DRAFT_KINDS),
                teaching_drafts=list_drafts(repo, kinds=TEACHING_DRAFT_KINDS),
            ),
        )

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
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/peer-review")
    def assistant_peer_review(paper_text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        try:
            review_paper(repo, client, paper_text=paper_text, actor=actor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/exam-questions")
    def assistant_exam_questions(source_text: str = Form(...), n_questions: int = Form(5), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        draft_exam_questions(repo, client, source_text=source_text, n_questions=n_questions, actor=actor)
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/rubric")
    def assistant_rubric(paper_text: str = Form(...), rubric_text: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        assess_paper_against_rubric(repo, client, paper_text=paper_text, rubric_text=rubric_text, actor=actor)
        return RedirectResponse("/assistant", status_code=303)

    @app.post("/assistant/reading-list")
    def assistant_reading_list(course_topic: str = Form(...), actor: str = Form(...)) -> RedirectResponse:
        client = _require_llm()
        draft_reading_list(repo, client, course_topic=course_topic, actor=actor)
        return RedirectResponse("/assistant", status_code=303)

    return app
