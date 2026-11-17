"""Multilingual .pptx generation (dhra.presentation) -- offline, fake LLM."""

from __future__ import annotations

import io
import json

import pytest
from pptx import Presentation

from dhra.llm import LLMClient, LLMConfig
from dhra.presentation import LANGUAGES, PresentationError, make_presentation
from dhra.repo import DHRARepo

OUTLINE = {
    "title": "Tokat",
    "subtitle": "sub",
    "slides": [{"title": "Bridge", "bullets": ["repaired 1849", "after a storm"], "notes": "n", "sources": [1]}],
}


class _Resp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


class _Session:
    def __init__(self, content):
        self.content, self.calls = content, []

    def post(self, url, *, headers, json, timeout):
        self.calls.append(json)
        return _Resp(self.content)


def _client(content):
    s = _Session(content)
    return LLMClient(LLMConfig(base_url="https://x/v1", api_key="k", model="qwen"), session=s), s


@pytest.fixture
def repo(tmp_path):
    r = DHRARepo(tmp_path / "store")
    r.ingest_text("The bridge at Tokat was repaired in 1849 after a storm.", source_id="s")
    return r


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_every_language_builds_a_valid_deck(repo, lang):
    client, session = _client("```json\n" + json.dumps(OUTLINE, ensure_ascii=False) + "\n```")
    data = make_presentation(repo, client, topic="Tokat", lang=lang)
    prs = Presentation(io.BytesIO(data))
    assert len(prs.slides) == 3  # title + 1 content + 1 sources
    assert LANGUAGES[lang].name in session.calls[0]["messages"][0]["content"]
    sources_text = " ".join(sh.text_frame.text for sh in prs.slides[2].shapes if sh.has_text_frame)
    assert "The bridge at Tokat was repaired in 1849 after a storm." in sources_text  # whole sentence, verbatim, not just the matched word
    prompt = session.calls[0]["messages"][1]["content"]
    assert "The bridge at Tokat was repaired in 1849 after a storm." in prompt  # the model sees the sentence


def test_arabic_is_right_to_left(repo):
    client, _ = _client(json.dumps(OUTLINE))
    prs = Presentation(io.BytesIO(make_presentation(repo, client, topic="Tokat", lang="ar")))
    body = prs.slides[1].placeholders[1].text_frame.paragraphs[0]._p.pPr
    assert body.get("rtl") == "1"


def test_no_evidence_means_no_deck(repo):
    client, session = _client(json.dumps(OUTLINE))
    with pytest.raises(PresentationError):
        make_presentation(repo, client, topic="zzzunmatched", lang="en")
    assert session.calls == []  # the model is never asked without evidence


def test_garbage_model_output_is_a_clean_error(repo):
    client, _ = _client("sorry, I cannot")
    with pytest.raises(PresentationError):
        make_presentation(repo, client, topic="Tokat", lang="en")


def test_web_route_returns_a_pptx_download(repo, monkeypatch):
    from fastapi.testclient import TestClient

    from dhra.web.app import build_app

    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://x/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "k")
    monkeypatch.setenv("DHRA_GLM_MODEL", "qwen")
    monkeypatch.setattr(LLMClient, "complete", lambda self, messages, **kw: json.dumps(OUTLINE))
    c = TestClient(build_app(repo))
    assert "Presentation" in c.get("/presentation").text
    r = c.post("/presentation", data={"topic": "Tokat", "pres_lang": "zh", "n_slides": "3"})
    assert r.status_code == 200
    assert r.headers["content-disposition"].endswith('-zh.pptx"')
    assert len(Presentation(io.BytesIO(r.content)).slides) == 3
    assert c.post("/presentation", data={"topic": "zzzunmatched", "pres_lang": "en"}).status_code == 400


def test_overlong_topic_is_rejected_before_any_search_or_model_call(repo):
    client, session = _client(json.dumps(OUTLINE))
    with pytest.raises(PresentationError):
        make_presentation(repo, client, topic="Tokat " * 200, lang="en")
    assert session.calls == []
