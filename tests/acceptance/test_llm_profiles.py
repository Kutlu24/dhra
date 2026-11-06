"""Selectable LLM profiles: GLM (DHRA_GLM_*) plus any number of OpenAI-
compatible models from DHRA_LLM_MODELS, chosen per browser."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from dhra.llm import LLMClient, load_profiles
from dhra.repo import DHRARepo
from dhra.web.app import build_app
from dhra.web.security import SecurityConfig

OLLAMA = {"id": "qwen3.5-4b", "label": "Qwen3.5 4B (local)", "base_url": "http://ollama:11434/v1/",
          "model": "qwen3.5-nothink", "api_key": "ollama", "timeout": 300}


# -- loading ----------------------------------------------------------------

def test_default_glm_comes_first_then_custom_profiles():
    env = {"DHRA_GLM_BASE_URL": "https://glm.example/v1/", "DHRA_GLM_API_KEY": "k1", "DHRA_GLM_MODEL": "glm-4.6",
           "DHRA_LLM_MODELS": json.dumps([OLLAMA])}
    ps = load_profiles(env)
    assert [p.id for p in ps] == ["default", "qwen3.5-4b"]
    assert ps[0].config.base_url == "https://glm.example/v1" and ps[1].config.base_url == "http://ollama:11434/v1"
    assert ps[1].config.timeout == 300 and ps[1].label == "Qwen3.5 4B (local)"


def test_no_glm_and_no_models_means_no_profiles():
    assert load_profiles({}) == []


def test_api_key_env_is_resolved_and_must_be_set():
    item = {**OLLAMA, "api_key": None, "api_key_env": "MY_KEY"}
    item.pop("api_key")
    assert load_profiles({"DHRA_LLM_MODELS": json.dumps([item]), "MY_KEY": "s3"})[0].config.api_key == "s3"
    with pytest.raises(ValueError):
        load_profiles({"DHRA_LLM_MODELS": json.dumps([item])})


@pytest.mark.parametrize("bad", [
    "not json", '{"a": 1}', '[1]', json.dumps([{**OLLAMA, "id": "Bad ID!"}]), json.dumps([{**OLLAMA, "id": "../x"}]),
    json.dumps([{k: v for k, v in OLLAMA.items() if k != "model"}]),
    json.dumps([{k: v for k, v in OLLAMA.items() if k != "base_url"}]),
    json.dumps([OLLAMA, OLLAMA]), json.dumps([{**OLLAMA, "timeout": "soon"}]),
])
def test_malformed_config_is_rejected(bad):
    with pytest.raises(ValueError):
        load_profiles({"DHRA_LLM_MODELS": bad})


def test_extra_body_fields_are_loaded_and_sent_but_cannot_override_core_fields():
    import requests

    item = {**OLLAMA, "extra": {"reasoning_effort": "none"}}
    cfg = load_profiles({"DHRA_LLM_MODELS": json.dumps([item])})[0].config
    assert cfg.extra == {"reasoning_effort": "none"}
    sent = {}

    class _R:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "hi"}}]}

    class _S(requests.Session):
        def post(self, url, **kw):
            sent.update(kw["json"]); return _R()

    assert LLMClient(cfg, session=_S()).complete([{"role": "user", "content": "x"}]) == "hi"
    assert sent["reasoning_effort"] == "none" and sent["model"] == "qwen3.5-nothink"
    for bad in ({"model": "evil"}, {"messages": []}, {"max_tokens": 1}, ["x"]):
        with pytest.raises(ValueError):
            load_profiles({"DHRA_LLM_MODELS": json.dumps([{**OLLAMA, "extra": bad}])})


def test_empty_answer_is_an_error_not_a_silent_blank():
    import requests
    from dhra.llm import LLMConfig, LLMError

    class _R:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "", "reasoning": "thinking..."}, "finish_reason": "length"}]}

    class _S(requests.Session):
        def post(self, url, **kw): return _R()

    with pytest.raises(LLMError, match="empty answer"):
        LLMClient(LLMConfig("http://x/v1", "k", "m"), session=_S()).complete([{"role": "user", "content": "x"}])


def test_app_refuses_to_start_with_malformed_models(tmp_path, monkeypatch):
    monkeypatch.setenv("DHRA_LLM_MODELS", "not json")
    with pytest.raises(ValueError):
        build_app(DHRARepo(tmp_path / "s"), security=SecurityConfig())


# -- web --------------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "glm-secret-key")
    monkeypatch.setenv("DHRA_GLM_MODEL", "glm-4.6")
    monkeypatch.setenv("DHRA_LLM_MODELS", json.dumps([OLLAMA]))
    monkeypatch.setattr(LLMClient, "complete", lambda self, messages, **kw: f"answer-from-{self.config.model}")
    c = TestClient(build_app(DHRARepo(tmp_path / "store"), security=SecurityConfig()))
    c.post("/ingest", data={"source_id": "s", "text": "the harbour burned in 1867"})
    return c


def _answer(c):
    return c.post("/chat", data={"message": "harbour"}).text


def test_selector_lists_labels_only_never_keys_or_urls(client):
    page = client.get("/").text
    assert 'id="llm-select"' in page and "Qwen3.5 4B (local)" in page and "glm-4.6" in page
    for secret in ("glm-secret-key", "ollama:11434", "glm.example", "qwen3.5-nothink"):
        assert secret not in page


def test_selector_hidden_with_a_single_model(tmp_path, monkeypatch):
    monkeypatch.setenv("DHRA_GLM_BASE_URL", "https://glm.example/v1")
    monkeypatch.setenv("DHRA_GLM_API_KEY", "k")
    monkeypatch.delenv("DHRA_LLM_MODELS", raising=False)
    c = TestClient(build_app(DHRARepo(tmp_path / "s"), security=SecurityConfig()))
    assert 'id="llm-select"' not in c.get("/").text


def test_default_model_used_until_one_is_picked_then_the_pick_is_used(client):
    c = client
    assert "answer-from-glm-4.6" in _answer(c)
    r = c.post("/llm/select", data={"profile": "qwen3.5-4b"}, follow_redirects=False)
    assert r.status_code == 303 and "dhra_llm=qwen3.5-4b" in r.headers["set-cookie"] and "httponly" in r.headers["set-cookie"].lower()
    assert "answer-from-qwen3.5-nothink" in _answer(c)
    page = c.get("/").text
    assert 'value="qwen3.5-4b" selected' in page
    c.post("/llm/select", data={"profile": "default"})
    assert "answer-from-glm-4.6" in _answer(c)


def test_unknown_profile_rejected_and_forged_cookie_falls_back(client):
    c = client
    assert c.post("/llm/select", data={"profile": "nope"}).status_code == 400
    c.cookies.set("dhra_llm", "../../etc/passwd")
    assert "answer-from-glm-4.6" in _answer(c)


def test_select_returns_to_the_same_site_page_and_is_csrf_protected(client):
    r = client.post("/llm/select", data={"profile": "default"}, headers={"Referer": "http://testserver/claims?x=1"}, follow_redirects=False)
    assert r.headers["location"] == "/claims?x=1"
    r = client.post("/llm/select", data={"profile": "default"}, follow_redirects=False)
    assert r.headers["location"] == "/"                      # no Referer -> home
    for hdr in ({"Origin": "https://evil.example"}, {"Referer": "https://evil.example/x"}):
        assert client.post("/llm/select", data={"profile": "default"}, headers=hdr, follow_redirects=False).status_code == 403


def test_the_model_actually_used_is_recorded_as_provenance(client, tmp_path):
    client.post("/llm/select", data={"profile": "qwen3.5-4b"})
    client.post("/assistant/research-questions", data={"context_query": "harbour", "actor": "tester"})
    log = (tmp_path / "store" / "events.jsonl").read_text()
    assert "qwen3.5-nothink" in log
