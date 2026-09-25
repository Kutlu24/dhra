"""Speech-to-text and text-to-speech, both free/keyless:

- STT: faster-whisper - runs the open-source Whisper model locally (CPU),
  no API key, no per-use cost. First call downloads the model weights to
  a local cache (~500MB for "small", see config.WHISPER_MODEL_SIZE).
- TTS: edge-tts - wraps Microsoft Edge's free text-to-speech web service.
  No account/key needed, but it does call out over the network (not a
  local model) - if that service is ever unreachable, TTS degrades; STT
  still works fully offline.

Both replaced an earlier OpenAI-based version - see README for why.
"""
from __future__ import annotations

import asyncio
import tempfile
import threading
from pathlib import Path

import edge_tts
from faster_whisper import WhisperModel

from .config import settings


class SpeechError(Exception):
    """A real backend failure (bad audio, model load error, edge-tts
    network failure). Callers are expected to catch this and degrade
    (e.g. skip the TTS button, or show "transcription failed" for one
    utterance) rather than crash the room for every participant."""


_model: WhisperModel | None = None

# Whisper inference is what actually pushed a free-tier 512MB instance over
# its memory limit in production (confirmed via Render's own OOM event, not
# a guess) when two transcriptions landed at the same time - each inference
# allocates its own activation buffers on top of the model weights already
# in memory. Serializing to one inference at a time keeps peak memory
# bounded to "one utterance's worth" regardless of how many participants
# talk in quick succession; the cost is a queued participant waits a couple
# of extra seconds rather than the whole process crashing.
_transcribe_semaphore = threading.Semaphore(1)


def _get_model() -> WhisperModel:
    # Loaded once per process, not per request - construction loads the
    # model weights into memory, which is the slow part.
    global _model
    if _model is None:
        _model = WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_bytes: bytes, filename: str, language_hint: str = "") -> str:
    """language_hint is the speaker's declared room language (ISO-639-1,
    e.g. "tr") - passed through as a hint, not a hard constraint: it
    measurably improves accuracy/latency when known, but Whisper still
    auto-detects fine without it."""
    suffix = Path(filename).suffix or ".webm"
    try:
        with _transcribe_semaphore, tempfile.NamedTemporaryFile(suffix=suffix) as f:
            f.write(audio_bytes)
            f.flush()
            # vad_filter=True: the press-and-hold interaction (README) means
            # every clip carries a beat of dead air at the start (time
            # between pressing the button and starting to speak) and the
            # end (time between finishing and releasing) - faster-whisper
            # bundles a Silero VAD filter that trims non-speech audio
            # before transcription, for free (no extra dependency, no API
            # call). Verified against real short clips with leading/
            # trailing silence: transcription still succeeds and drops the
            # silent padding instead of feeding it to the model.
            segments, _info = _get_model().transcribe(f.name, language=language_hint or None, vad_filter=True)
            return " ".join(segment.text.strip() for segment in segments).strip()
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(str(exc)) from exc


# One representative neural voice per language - edge-tts offers several
# per language, this is just a reasonable default for each, not meant to
# be exhaustive (see `edge-tts --list-voices` for the full catalogue).
_VOICE_FOR_LANGUAGE = {
    "en": "en-US-AriaNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "ar": "ar-EG-SalmaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "tr": "tr-TR-EmelNeural",
}


def synthesize(text: str, language_code: str = "") -> bytes:
    voice = _VOICE_FOR_LANGUAGE.get(language_code, "en-US-AriaNeural")
    try:
        return asyncio.run(_synthesize_async(text, voice))
    except Exception as exc:  # noqa: BLE001
        raise SpeechError(str(exc)) from exc


async def _synthesize_async(text: str, voice: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)
