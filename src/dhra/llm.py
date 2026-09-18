"""LLM-calling layer -- fills the gap flagged repeatedly across
OPEN_QUESTIONS.md (#7, #11, #14): every other module that needed a model
to propose something (candidate claim evidence, disconfirmation queries)
took it as a caller-supplied argument because nothing in this repo could
actually call a model. This is that missing piece.

Deliberately provider-neutral, not the Anthropic SDK: the researcher
chose GLM (OpenAI-compatible chat completions API), self-hostable on
university infrastructure -- a real, deliberate choice for this
integration, not a default. `LLMClient` is a small `requests`-based
client against that API shape; anything else OpenAI-compatible (a
different self-hosted model, a different vendor) works by changing
`base_url`/`model` only.

Section 10's boundary is enforced by what calls this module, not by
this module itself: `dhra.llm` only ever returns text. Nothing here
assigns epistemic status, resolves a contradiction, or decides an
exclusion -- every caller in `dhra.research_assistant`,
`dhra.teaching`, `dhra.peer_review` treats the model's output as a
*proposal* that deterministic code (search, assess_claim, a human
approval step) still has to verify or approve.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests


class LLMError(Exception):
    pass


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Reads DHRA_GLM_BASE_URL / DHRA_GLM_API_KEY / DHRA_GLM_MODEL.
        No vault/credential-store integration exists (OPEN_QUESTIONS.md
        #17's same gap for Zotero) -- an environment variable is the
        honest current answer, not a permanent one."""
        base_url = os.environ.get("DHRA_GLM_BASE_URL")
        api_key = os.environ.get("DHRA_GLM_API_KEY")
        model = os.environ.get("DHRA_GLM_MODEL", "glm-4.6")
        if not base_url or not api_key:
            raise LLMError(
                "DHRA_GLM_BASE_URL and DHRA_GLM_API_KEY must be set -- "
                "no LLM backend is configured by default (see OPEN_QUESTIONS.md)."
            )
        return cls(base_url=base_url.rstrip("/"), api_key=api_key, model=model)


class LLMClient:
    """OpenAI-compatible chat completions client (the shape GLM's real
    API uses, hosted or self-hosted -- verified against docs.z.ai before
    writing this, not assumed)."""

    def __init__(self, config: LLMConfig, *, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()

    def complete(self, messages: list[dict], *, temperature: float = 0.0, max_tokens: int = 1024) -> str:
        resp = self.session.post(
            f"{self.config.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=self.config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"unexpected response shape from LLM backend: {data!r}") from exc


def log_and_complete(client: LLMClient, repo, *, purpose: str, messages: list[dict], task: str | None = None, **kwargs) -> str:
    """The wrapper every caller in this repo should use instead of
    `client.complete` directly -- section 5.1: "every model.invoked event
    records model identity, version, purpose, prompt hash and
    parameters... this is what makes the disclosure in the methods
    statement honest." Skipping this wrapper is how that disclosure
    quietly stops being true."""
    import hashlib
    import json

    prompt_sha256 = hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    repo.log_model_invocation(model=client.config.model, purpose=purpose, prompt_sha256=prompt_sha256, parameters=kwargs, task=task)
    return client.complete(messages, **kwargs)
