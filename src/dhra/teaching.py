"""Teaching support -- DHRA_BUILD_SPEC.md section 6 (Phase 4) names this
as a deliverable but never elaborates what it means (OPEN_QUESTIONS.md
#18). Scope confirmed with the researcher (2026-09-18): exam question
drafting from course material, and a first-pass rubric assessment of
student work -- never a grade, always flagged points for the instructor
to review themselves.

Both are PREPARE-class drafts (dhra.drafting): the model proposes, the
instructor reads and approves/rejects/edits before anything is used for
real. Neither function grades on its own authority -- section 15's
"misconduct detection on student work" anti-requirement is a harder
line than this (that's plagiarism/cheating detection, not rubric
feedback), but the same caution applies: this is a draft for a human to
weigh, not an automated verdict.
"""

from __future__ import annotations

from dhra.drafting import create_draft
from dhra.llm import LLMClient, log_and_complete
from dhra.repo import DHRARepo

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
