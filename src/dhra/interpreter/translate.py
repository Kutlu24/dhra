"""Text-only translation of one transcribed utterance into every other
participant's language. Deliberately separate from speech.py (STT/TTS,
real OpenAI audio endpoints) - this is a plain chat-completion call, and
GLM/Gemini are just as capable at it as OpenAI while being free-tier, so
there is no reason to spend OpenAI budget on it.
"""
from __future__ import annotations

from openai import OpenAI

from .config import LANGUAGES, settings

_SYSTEM_PROMPT = """You are a real-time conversation interpreter. Translate the given sentence into {target_language}.

Rules:
- Output ONLY the translation - no quotes, no explanation, no repeating the original.
- This text comes from live speech-to-text of a spoken conversation: it may have disfluencies, false starts, or be an incomplete sentence. Translate the intended meaning naturally, as a human interpreter would - don't "fix" it into formal written prose.
- Keep the register of the original (casual stays casual, formal stays formal).
- If the given text is empty or clearly just noise, output nothing."""


class TranslationError(Exception):
    """A real backend failure from whichever provider is configured -
    callers degrade to showing the original text rather than crashing the
    room, same reasoning as fundraising-assistant's DraftingError."""


def _call_glm(system_prompt: str, text: str) -> str:
    client = OpenAI(api_key=settings.glm_api_key, base_url=settings.glm_base_url, timeout=20.0, max_retries=1)
    response = client.chat.completions.create(
        model=settings.glm_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
    )
    return (response.choices[0].message.content or "").strip()


def _call_gemini(system_prompt: str, text: str) -> str:
    client = OpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=20.0,
        max_retries=1,
    )
    response = client.chat.completions.create(
        model=settings.gemini_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
    )
    return (response.choices[0].message.content or "").strip()


_TRANSLATORS = {"glm": _call_glm, "gemini": _call_gemini}


def translate(text: str, target_language_code: str) -> str:
    text = text.strip()
    if not text:
        return ""
    target_language = LANGUAGES.get(target_language_code, target_language_code)
    system_prompt = _SYSTEM_PROMPT.format(target_language=target_language)
    call = _TRANSLATORS[settings.translate_provider]
    try:
        return call(system_prompt, text)
    except Exception as exc:  # noqa: BLE001 - any provider failure degrades the same way
        raise TranslationError(str(exc)) from exc
