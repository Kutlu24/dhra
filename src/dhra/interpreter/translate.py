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


# omniroute routes GLM in ~6s and Gemini takes ~20s; a 5s cap made every
# provider time out and left translation permanently failing.
_TIMEOUT = 30.0


class TranslationError(Exception):
    """A real backend failure from whichever provider is configured -
    callers degrade to showing the original text rather than crashing the
    room, same reasoning as fundraising-assistant's DraftingError."""


def _call_glm(system_prompt: str, text: str) -> str:
    client = OpenAI(api_key=settings.glm_api_key, base_url=settings.glm_base_url, timeout=_TIMEOUT, max_retries=1)
    response = client.chat.completions.create(
        model=settings.glm_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
    )
    return (response.choices[0].message.content or "").strip()


def _call_gemini(system_prompt: str, text: str) -> str:
    client = OpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=_TIMEOUT,
        max_retries=1,
    )
    response = client.chat.completions.create(
        model=settings.gemini_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
    )
    return (response.choices[0].message.content or "").strip()


def _call_groq(system_prompt: str, text: str) -> str:
    client = OpenAI(api_key=settings.groq_api_key, base_url="https://api.groq.com/openai/v1", timeout=_TIMEOUT, max_retries=1)
    response = client.chat.completions.create(
        model=settings.groq_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
    )
    return (response.choices[0].message.content or "").strip()


def _call_anthropic(system_prompt: str, text: str) -> str:
    client = OpenAI(api_key=settings.anthropic_api_key, base_url="https://api.anthropic.com/v1", timeout=_TIMEOUT, max_retries=1)
    response = client.chat.completions.create(
        model=settings.anthropic_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
    )
    return (response.choices[0].message.content or "").strip()


_TRANSLATORS = {
    "glm": _call_glm,
    "gemini": _call_gemini,
    "groq": _call_groq,
    "anthropic": _call_anthropic,
}


def _translate_with_fallback(text: str, target_language: str) -> tuple[str, str]:
    """4-provider fallback chain; order set by settings.translate_provider (default 'auto': Groq if keyed, then GLM → Gemini → Claude API)"""
    import logging
    system_prompt = _SYSTEM_PROMPT.format(target_language=target_language)
    providers = [
        ("glm", _call_glm, settings.glm_api_key),
        ("gemini", _call_gemini, settings.gemini_api_key),
        ("groq", _call_groq, settings.groq_api_key),
        ("anthropic", _call_anthropic, settings.anthropic_api_key),
    ]
    # Primary first, the rest keep their order as fallbacks. "auto" prefers
    # Groq when it has a key (sub-second vs ~4-5s for GLM on a short
    # utterance - the difference between feeling simultaneous or not).
    primary = "groq" if settings.translate_provider == "auto" and settings.groq_api_key else settings.translate_provider
    providers.sort(key=lambda p: p[0] != primary)
    for name, func, key in providers:
        if not key:
            logging.warning(f"{name.upper()} translation skipped: no API key configured")
            continue
        try:
            translation = func(system_prompt, text)
            return translation, name
        except Exception as e:
            # Type + HTTP status only: provider error bodies can echo key fragments or the utterance text.
            status = getattr(e, "status_code", None)
            logging.warning(f"{name.upper()} translation failed ({type(e).__name__}, status={status}), trying next provider")
    raise TranslationError("All translation providers failed or not configured")


def translate(text: str, target_language_code: str) -> str:
    text = text.strip()
    if not text:
        return ""
    target_language = LANGUAGES.get(target_language_code, target_language_code)
    try:
        translation, provider_used = _translate_with_fallback(text, target_language)
        return translation
    except TranslationError as exc:
        raise exc from None
    except Exception as exc:  # noqa: BLE001 - any provider failure degrades the same way
        raise TranslationError(str(exc)) from exc
