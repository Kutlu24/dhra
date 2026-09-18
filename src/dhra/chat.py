"""Chat -- a conversational front end over the same evidence-first
discipline as everything else in this repo. Not a general-purpose
chatbot: every answer is grounded in a real `evidence.search()` call,
and there is no answer at all when there's no evidence, same rule
`response.py` already enforces structurally (I10) applied here too.

Deliberately stateless on the server: a public demo deployment can have
multiple concurrent strangers using it, and there is no account system
(OPEN_QUESTIONS.md #21) to keep their conversations apart. Conversation
history round-trips through the caller (the web UI's hidden form field)
instead of living in server memory -- nobody's chat leaks into anyone
else's.
"""

from __future__ import annotations

from dataclasses import dataclass

from dhra.llm import LLMClient, LLMError, log_and_complete
from dhra.evidence import search as evidence_search
from dhra.models import Passage
from dhra.repo import DHRARepo

_CHAT_SYSTEM_PROMPT = (
    "You are answering a historian's question using ONLY the evidence excerpts given below, "
    "drawn from their own primary-source corpus. Cite the locator (in square brackets) for "
    "every claim you make. If the excerpts do not support an answer, say plainly that you "
    "don't know and do not guess -- never state anything as fact that is not directly "
    "supported by the excerpts you were given."
)


@dataclass(frozen=True)
class ChatTurnResult:
    evidence: tuple[Passage, ...]
    absence_note: str | None
    answer: str | None  # None when there was no evidence to answer from, or the LLM call itself failed
    llm_error: str | None = None  # set only when a call was attempted and the backend failed (rate limit, bad key, timeout, ...)


def answer(
    repo: DHRARepo,
    client: LLMClient | None,
    *,
    question: str,
    history: list[dict],
    max_passages: int = 8,
    task: str | None = None,
) -> ChatTurnResult:
    """`history`: prior turns as [{"role": "user"|"assistant", "text": ...}, ...] --
    supplied by the caller each time (see module docstring), not stored here.
    `client=None` returns evidence only, no generated answer -- same
    graceful "not configured" degradation as the rest of the web UI."""
    response = evidence_search(repo, question, task=task)
    if not response.evidence:
        return ChatTurnResult(evidence=(), absence_note=response.absence_note, answer=None)

    if client is None:
        return ChatTurnResult(evidence=response.evidence, absence_note=None, answer=None)

    excerpts = "\n".join(
        f"- [{p.locator.item_id}/{p.locator.rep_id}:{p.locator.start}-{p.locator.end}] \"{p.text}\""
        for p in response.evidence[:max_passages]
    )
    history_messages = [{"role": h["role"], "content": h["text"]} for h in history if h.get("role") in ("user", "assistant") and h.get("text")]
    messages = (
        [{"role": "system", "content": _CHAT_SYSTEM_PROMPT}]
        + history_messages
        + [{"role": "user", "content": f"Evidence:\n{excerpts}\n\nQuestion: {question}"}]
    )
    try:
        answer_text = log_and_complete(client, repo, purpose="chat_answer", messages=messages, task=task)
    except LLMError as exc:
        return ChatTurnResult(evidence=response.evidence, absence_note=None, answer=None, llm_error=str(exc))
    return ChatTurnResult(evidence=response.evidence, absence_note=None, answer=answer_text)
