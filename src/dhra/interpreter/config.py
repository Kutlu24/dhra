from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# The 8 languages requested for this project. Codes match what we pass to
# Whisper (ISO-639-1) and what GLM understands as plain language names -
# speech.py maps them separately to edge-tts's own voice-name format.
LANGUAGES: dict[str, str] = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "ar": "Arabic",
    "ru": "Russian",
    "zh": "Chinese",
    "tr": "Turkish",
}


class Settings(BaseSettings):
    # Speech-to-text: faster-whisper, runs locally (CPU), no API key, no
    # per-use cost - see speech.py/README for why this replaced OpenAI's
    # Whisper API. "small" is the minimum size that stays reasonably
    # accurate on non-Latin scripts (Arabic/Chinese/Russian) - "tiny"/"base"
    # degrade noticeably there even though they're faster. First use
    # downloads the model weights (~500MB for "small") to a local cache.
    whisper_model_size: str = "small"

    # ctranslate2 sizes its internal thread pool from the HOST's total
    # logical CPU count (std::thread::hardware_concurrency()), not from
    # any container CPU quota - if this process is running under a
    # Docker `cpus` limit smaller than the host's core count, leaving
    # this at 0 (auto) causes thread oversubscription against the CFS
    # quota, which is far slower than just "fewer cores" (real,
    # measured regression on the home-server deployment - see
    # home-server-infra/docs/DEPLOYMENT.md). Set to match that limit;
    # 0 keeps the old auto-detect behavior (fine on Render, which has
    # no such mismatch).
    whisper_cpu_threads: int = 0

    # Text translation only (cheap, text-in/text-out) - reuse GLM the same way
    # fundraising-assistant does: free-tier, and on a separate quota from
    # Gemini, so it doesn't compete with other projects' Gemini usage.
    translate_provider: str = "glm"  # "glm" | "gemini"
    glm_api_key: str | None = None
    glm_model: str = "glm-4.5-flash"
    glm_base_url: str = "https://api.z.ai/api/paas/v4/"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), extra="ignore"
    )


settings = Settings()
