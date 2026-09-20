"""Teaching support -- DHRA_BUILD_SPEC.md section 6 (Phase 4) names this
as a deliverable but never elaborates what it means (OPEN_QUESTIONS.md
#18). Scope confirmed with the researcher (2026-09-18): exam question
drafting from course material, a first-pass rubric assessment of
student work, and reading-list/syllabus drafting -- never a grade,
always flagged points or suggestions for the instructor to check
themselves.

All three are PREPARE-class drafts (dhra.drafting): the model proposes,
the instructor reads and approves/rejects/edits before anything is used
for real. `assess_paper_against_rubric` doesn't grade on its own
authority -- section 15's "misconduct detection on student work"
anti-requirement is a harder line than this (that's plagiarism/cheating
detection, not rubric feedback), but the same caution applies.

`draft_reading_list` is the one function here that can let the model
speak from its own training knowledge (book chapters, articles it
recalls) rather than only real retrieved corpus excerpts -- every other
LLM-backed function in this repo (research_assistant, peer_review, the
other two here) only ever shows the model real evidence and treats its
output as commentary on that evidence. Recall-only is riskier: the
model can misremember or invent a citation that sounds plausible.

OPEN_QUESTIONS.md #28 (2026-09-20): when a `websearch_client`
(`dhra.websearch.WebSearchClient`, a real SearXNG instance the
researcher points at) is passed in, secondary-reading suggestions are
grounded in real, retrieved search results instead -- the model is told
to cite only titles/URLs actually present in those results, and the
raw result list is appended to the draft verbatim so a researcher can
check the model's summary against what was really retrieved, the same
"never trust the narrative alone" discipline as corpus locators
elsewhere in this repo. With no `websearch_client` (the default --
nothing self-hosts a search backend for this repo), the previous
recall-only behaviour is unchanged: suggestions land in their own
clearly-labelled, explicitly-unverified section (see
`_READING_LIST_SYSTEM_PROMPT`), and an instructor still has to check
every citation before it goes on a syllabus.
"""

from __future__ import annotations

from dhra.drafting import create_draft
from dhra.evidence import search as evidence_search
from dhra.llm import LLMClient, log_and_complete
from dhra.repo import DHRARepo
from dhra.websearch import WebSearchClient, WebSearchError, web_search

_EXAM_SYSTEM_PROMPT = (
    "You draft exam questions from course material for an instructor to review and edit. "
    "Base every question only on the material given. Vary question types (short answer, "
    "essay prompt, primary-source analysis). Number each question. Do not include answers "
    "unless asked."
)

_RUBRIC_SYSTEM_PROMPT = (
    "You are a first-pass reader helping an instructor grade student work against a rubric. "
    "You do NOT assign a grade or a numeric score. For each rubric criterion, quote the part "
    "of the student's text that addresses it (or note that it is missing/weak), and flag "
    "anything the instructor should look at closely. This is a draft for the instructor to "
    "review, not a verdict."
)


def draft_exam_questions(
    repo: DHRARepo,
    client: LLMClient,
    *,
    source_text: str,
    n_questions: int,
    actor: str,
    task: str | None = None,
) -> str:
    messages = [
        {"role": "system", "content": _EXAM_SYSTEM_PROMPT},
        {"role": "user", "content": f"Course material:\n{source_text}\n\nDraft {n_questions} exam questions."},
    ]
    draft_body = log_and_complete(client, repo, purpose="exam_question_drafting", messages=messages, task=task)
    return create_draft(repo, kind="exam_questions", text=draft_body, actor=actor, task=task)


def assess_paper_against_rubric(
    repo: DHRARepo,
    client: LLMClient,
    *,
    paper_text: str,
    rubric_text: str,
    actor: str,
    task: str | None = None,
) -> str:
    messages = [
        {"role": "system", "content": _RUBRIC_SYSTEM_PROMPT},
        {"role": "user", "content": f"Rubric:\n{rubric_text}\n\nStudent submission:\n{paper_text}\n\nGive a first-pass, per-criterion reading."},
    ]
    draft_body = log_and_complete(client, repo, purpose="rubric_first_pass", messages=messages, task=task)
    return create_draft(repo, kind="rubric_assessment", text=draft_body, actor=actor, task=task)


_READING_LIST_SYSTEM_PROMPT = (
    "You help an instructor draft a reading list / syllabus for a course, at the start of "
    "term. You will be given real excerpts already retrieved from the instructor's own "
    "primary-source corpus, and a course topic.\n\n"
    "Structure your response in exactly two sections, in this order:\n\n"
    "PRIMARY SOURCES FROM YOUR CORPUS:\n"
    "Suggest how the given excerpts could be used as primary-source readings. Reference only "
    "the excerpts you were given -- do not invent corpus items that were not shown to you.\n\n"
    "UNVERIFIED SUGGESTIONS (check before using -- not grounded in retrieved evidence):\n"
    "Suggest general secondary readings (book chapters, articles) that fit the course topic, "
    "drawing on your own training knowledge. You MUST use this exact heading, and you MUST "
    "treat every title, author and citation here as something that might be wrong, outdated, "
    "or invented -- say so explicitly. Never present this section as verified."
)

_READING_LIST_SYSTEM_PROMPT_GROUNDED = (
    "You help an instructor draft a reading list / syllabus for a course, at the start of "
    "term. You will be given real excerpts already retrieved from the instructor's own "
    "primary-source corpus, a course topic, and real web search results for that topic.\n\n"
    "Structure your response in exactly two sections, in this order:\n\n"
    "PRIMARY SOURCES FROM YOUR CORPUS:\n"
    "Suggest how the given excerpts could be used as primary-source readings. Reference only "
    "the excerpts you were given -- do not invent corpus items that were not shown to you.\n\n"
    "SECONDARY READINGS FROM WEB SEARCH:\n"
    "Suggest which of the given search results would make useful secondary readings, and why. "
    "Cite only titles and URLs that appear in the search results given below -- do not invent "
    "a title, author or URL that is not in that list. If none of the results are actually "
    "relevant to the course topic, say so plainly instead of forcing a fit."
)


def draft_reading_list(
    repo: DHRARepo,
    client: LLMClient,
    *,
    course_topic: str,
    actor: str,
    max_passages: int = 10,
    websearch_client: WebSearchClient | None = None,
    task: str | None = None,
) -> str:
    """Two-part draft: real corpus excerpts (grounded, like every other
    LLM-backed function here) plus, depending on `websearch_client`,
    either real retrieved web results (grounded) or model-recalled
    external suggestions (NOT grounded -- see the module docstring).
    Never raises on no corpus matches, unlike
    `suggest_research_questions`: a reading list should still be
    produced, just honestly noting the corpus had nothing relevant."""
    response = evidence_search(repo, course_topic, task=task)
    if response.evidence:
        excerpts = "\n".join(
            f"- [{p.locator.item_id}/{p.locator.rep_id}:{p.locator.start}-{p.locator.end}] \"{p.text}\""
            for p in response.evidence[:max_passages]
        )
    else:
        excerpts = "(no matching items found in the corpus for this topic)"

    web_results = []
    web_search_note = None
    if websearch_client is not None:
        try:
            web_results = web_search(repo, websearch_client, course_topic, task=task)
        except WebSearchError as exc:
            web_search_note = f"(web search failed: {exc} -- falling back to the model's own recall, unverified)"

    if web_results:
        results_block = "\n".join(f"- \"{r.title}\" {r.url} -- {r.snippet}" for r in web_results)
        messages = [
            {"role": "system", "content": _READING_LIST_SYSTEM_PROMPT_GROUNDED},
            {"role": "user", "content": f"Course topic: {course_topic}\n\nCorpus excerpts:\n{excerpts}\n\nWeb search results:\n{results_block}"},
        ]
    else:
        messages = [
            {"role": "system", "content": _READING_LIST_SYSTEM_PROMPT},
            {"role": "user", "content": f"Course topic: {course_topic}\n\nCorpus excerpts:\n{excerpts}"},
        ]

    body = log_and_complete(client, repo, purpose="reading_list_drafting", messages=messages, task=task)

    parts = [f"Reading list for: {course_topic}", f"(corpus version {repo.corpus_version().manifest_hash[:12]})"]
    if web_search_note:
        parts.append(web_search_note)
    parts.append("")
    parts.append(body)
    if web_results:
        parts.append("")
        parts.append("REAL WEB SEARCH RESULTS (as retrieved, for checking the summary above against):")
        parts.extend(f"- \"{r.title}\" {r.url}" for r in web_results)
    draft_text = "\n".join(parts)
    return create_draft(repo, kind="reading_list", text=draft_text, actor=actor, task=task)
