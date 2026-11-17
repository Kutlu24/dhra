"""Multilingual presentation (.pptx) drafting from the corpus.

Same discipline as `dhra.chat`: the slides are built ONLY from real
`evidence.search()` excerpts (each with its locator), never from the
model's own recall. The model only structures and translates; the last
slide lists every excerpt, verbatim in its original language, with its
locator, so a reader can check any slide against the source (the
"never trust the narrative alone" rule used elsewhere in this repo).

The generated deck is an unreviewed AI draft and says so on its title
slide. The LLM backend is whatever `dhra.llm` was configured with, so a
university-hosted open model (e.g. Qwen behind an OpenAI-compatible
endpoint) works without any code change here.
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass

from dhra.evidence import search as evidence_search
from dhra.llm import LLMClient, LLMError, log_and_complete
from dhra.models import Passage
from dhra.repo import DHRARepo


@dataclass(frozen=True)
class Language:
    code: str
    name: str  # English name, used in the prompt
    native: str
    rtl: bool = False
    cjk: bool = False
    draft_note: str = ""  # title-slide disclaimer in that language
    sources_title: str = ""


LANGUAGES: dict[str, Language] = {
    l.code: l
    for l in [
        Language("tr", "Turkish", "Türkçe", draft_note="Yapay zekâ taslağıdır; kullanmadan önce kaynaklarla karşılaştırın.", sources_title="Kaynaklar"),
        Language("en", "English", "English", draft_note="AI-generated draft; check against the sources before use.", sources_title="Sources"),
        Language("de", "German", "Deutsch", draft_note="KI-Entwurf; vor der Verwendung mit den Quellen abgleichen.", sources_title="Quellen"),
        Language("fr", "French", "Français", draft_note="Brouillon généré par IA ; à vérifier avec les sources avant usage.", sources_title="Sources"),
        Language("ar", "Arabic", "العربية", rtl=True, draft_note="مسودة أنشأها الذكاء الاصطناعي؛ راجعها مع المصادر قبل الاستخدام.", sources_title="المصادر"),
        Language("ru", "Russian", "Русский", draft_note="Черновик, созданный ИИ; сверьте с источниками перед использованием.", sources_title="Источники"),
        Language("es", "Spanish", "Español", draft_note="Borrador generado por IA; contrástelo con las fuentes antes de usarlo.", sources_title="Fuentes"),
        Language("zh", "Simplified Chinese", "中文", cjk=True, draft_note="AI 生成的草稿；使用前请对照原始资料核实。", sources_title="资料来源"),
    ]
}

_SYSTEM_PROMPT = (
    "You prepare a slide presentation for a historian using ONLY the numbered evidence "
    "excerpts given, drawn from their own primary-source corpus. Never add facts that are "
    "not supported by an excerpt, and never invent quotations. Write ALL slide text "
    "(titles, bullets, speaker notes) in {language}, translating from the excerpts' "
    "language where needed. Keep proper names and technical terms accurate.\n\n"
    "Reply with a single JSON object and nothing else, in exactly this shape:\n"
    '{{"title": "...", "subtitle": "...", "slides": [{{"title": "...", "bullets": ["...", "..."], '
    '"notes": "...", "sources": [1, 2]}}]}}\n'
    "Produce {n} content slides, 3-5 short bullets each. \"sources\" lists the numbers of the "
    "excerpts that slide relies on. If the excerpts cannot support the topic, return "
    '{{"title": "", "subtitle": "", "slides": []}}.'
)


class PresentationError(Exception):
    pass


def _gather_evidence(repo: DHRARepo, topic: str, *, max_passages: int, task: str | None) -> list[Passage]:
    """Whole topic first; if that literal phrase finds nothing, fall back
    to its individual words so a natural-language topic still retrieves."""
    found: dict[tuple[str, str, int, int], Passage] = {}
    queries = [topic] + [w for w in re.findall(r"\w+", topic) if len(w) > 3 and w != topic]
    for q in queries:
        for p in evidence_search(repo, q, task=task).evidence:
            loc = p.locator
            found.setdefault((loc.item_id, loc.rep_id, loc.start, loc.end), p)
        if len(found) >= max_passages:
            break
    return list(found.values())[:max_passages]


def _parse_outline(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise PresentationError("the model did not return a slide outline (no JSON found)")
    try:
        data = json.loads(text[start : end + 1])
    except ValueError as exc:
        raise PresentationError(f"the model's slide outline was not valid JSON: {exc}") from exc
    slides = data.get("slides")
    if not isinstance(slides, list):
        raise PresentationError("the model's slide outline has no 'slides' list")
    clean = []
    for s in slides:
        if not isinstance(s, dict):
            continue
        bullets = [str(b) for b in (s.get("bullets") or []) if str(b).strip()]
        clean.append(
            {
                "title": str(s.get("title") or "").strip(),
                "bullets": bullets,
                "notes": str(s.get("notes") or "").strip(),
                "sources": [n for n in (s.get("sources") or []) if isinstance(n, int)],
            }
        )
    return {"title": str(data.get("title") or "").strip(), "subtitle": str(data.get("subtitle") or "").strip(), "slides": clean}


def generate_outline(
    repo: DHRARepo,
    client: LLMClient,
    *,
    topic: str,
    lang: str,
    n_slides: int = 6,
    max_passages: int = 10,
    task: str | None = None,
) -> tuple[dict, list[Passage]]:
    if lang not in LANGUAGES:
        raise PresentationError(f"unsupported language {lang!r}")
    n_slides = max(1, min(int(n_slides), 20))
    passages = _gather_evidence(repo, topic, max_passages=max_passages, task=task)
    if not passages:
        raise PresentationError("no matching evidence in the corpus for this topic -- nothing to build a presentation from")
    excerpts = "\n".join(
        f"[{i}] ({p.locator.item_id}/{p.locator.rep_id}:{p.locator.start}-{p.locator.end}) \"{p.text}\""
        for i, p in enumerate(passages, 1)
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT.format(language=LANGUAGES[lang].name, n=n_slides)},
        {"role": "user", "content": f"Topic: {topic}\n\nEvidence excerpts:\n{excerpts}"},
    ]
    try:
        raw = log_and_complete(client, repo, purpose="presentation_drafting", messages=messages, task=task, temperature=0.2, max_tokens=4096)
    except LLMError:
        raise
    outline = _parse_outline(raw)
    if not outline["slides"]:
        raise PresentationError("the evidence does not support a presentation on this topic")
    return outline, passages


def build_pptx(outline: dict, passages: list[Passage], *, lang: str, topic: str, corpus_version: str = "") -> bytes:
    from pptx import Presentation
    from pptx.oxml.ns import qn
    from pptx.util import Pt

    L = LANGUAGES[lang]
    prs = Presentation()
    prs.slide_width, prs.slide_height = 12192000, 6858000  # 16:9

    def style(par, size: int | None = None, bold: bool | None = None) -> None:
        pPr = par._p.get_or_add_pPr()
        if L.rtl:
            pPr.set("rtl", "1")
            pPr.set("algn", "r")
        for run in par.runs:
            if size:
                run.font.size = Pt(size)
            if bold is not None:
                run.font.bold = bold
            rPr = run._r.get_or_add_rPr()
            rPr.set("lang", {"zh": "zh-CN"}.get(lang, lang))
            if L.cjk:
                ea = rPr.makeelement(qn("a:ea"), {"typeface": "Microsoft YaHei"})
                rPr.append(ea)
            if L.rtl:
                cs = rPr.makeelement(qn("a:cs"), {"typeface": "Arial"})
                rPr.append(cs)

    def set_text(shape, text: str, size: int, bold: bool = False) -> None:
        # the default template is 4:3; re-fit the placeholder to the 16:9 slide
        shape.left, shape.width = 600000, 10992000
        tf = shape.text_frame
        tf.word_wrap = True
        tf.text = text
        for par in tf.paragraphs:
            style(par, size, bold)

    # title slide
    s = prs.slides.add_slide(prs.slide_layouts[0])
    set_text(s.shapes.title, outline["title"] or topic, 40, True)
    sub = s.placeholders[1]
    sub.left, sub.width = 600000, 10992000
    sub.text_frame.text = (outline["subtitle"] + "\n" if outline["subtitle"] else "") + L.draft_note
    sub.text_frame.word_wrap = True
    for par in sub.text_frame.paragraphs:
        style(par, 18)

    # content slides
    for slide in outline["slides"]:
        s = prs.slides.add_slide(prs.slide_layouts[1])
        set_text(s.shapes.title, slide["title"], 32, True)
        body = s.placeholders[1]
        body.left, body.top, body.width, body.height = 600000, 1700000, 10992000, 4500000
        tf = body.text_frame
        tf.word_wrap = True
        bullets = slide["bullets"] or [""]
        tf.text = bullets[0]
        for b in bullets[1:]:
            tf.add_paragraph().text = b
        for par in tf.paragraphs:
            style(par, 22)
        refs = [n for n in slide["sources"] if 1 <= n <= len(passages)]
        if refs:
            box = s.shapes.add_textbox(600000, 6250000, 10992000, 400000)
            box.text_frame.word_wrap = True
            box.text_frame.text = L.sources_title + ": " + ", ".join(f"[{n}]" for n in refs)
            for par in box.text_frame.paragraphs:
                style(par, 12)
        if slide["notes"]:
            s.notes_slide.notes_text_frame.text = slide["notes"]

    # sources slides: verbatim excerpts, original language, with locators
    per_slide = 4
    for k in range(0, len(passages), per_slide):
        s = prs.slides.add_slide(prs.slide_layouts[5])
        set_text(s.shapes.title, L.sources_title + (f" ({k // per_slide + 1})" if len(passages) > per_slide else ""), 30, True)
        box = s.shapes.add_textbox(600000, 1500000, 10992000, 5000000)
        tf = box.text_frame
        tf.word_wrap = True
        first = True
        for i, p in enumerate(passages[k : k + per_slide], k + 1):
            par = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            loc = p.locator
            text = p.text if len(p.text) <= 300 else p.text[:297] + "..."
            par.text = f"[{i}] {loc.item_id}/{loc.rep_id}:{loc.start}-{loc.end}  \"{text}\""
            # excerpts stay in their original language: left-aligned, default direction
            for run in par.runs:
                run.font.size = Pt(12)
        if corpus_version and k == 0:
            tf.add_paragraph().text = f"(corpus {corpus_version[:12]})"

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def make_presentation(
    repo: DHRARepo,
    client: LLMClient,
    *,
    topic: str,
    lang: str,
    n_slides: int = 6,
    task: str | None = None,
) -> bytes:
    outline, passages = generate_outline(repo, client, topic=topic, lang=lang, n_slides=n_slides, task=task)
    return build_pptx(outline, passages, lang=lang, topic=topic, corpus_version=repo.corpus_version().manifest_hash)
