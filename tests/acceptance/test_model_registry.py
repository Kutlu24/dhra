"""Model registry (read-only view of the lab's models.yaml) + gateway seam.

Registry models cannot run yet (no gateway address/contract), so these
tests pin the behaviour that matters until then: the pickers appear only
when a registry is configured, and choosing a registry model fails loudly
instead of silently using a different engine.
"""

from __future__ import annotations

import pytest
import yaml
from fastapi.testclient import TestClient

from dhra.model_registry import load_registry, usable
from dhra.repo import DHRARepo
from dhra.web.app import build_app

REGISTRY = {
    "models": [
        {"id": "kraken-a", "engine": "kraken", "task": "htr", "level": "page", "enabled": True,
         "languages": ["de"], "scripts": ["Kurrent"], "centuries": [16, 19]},
        {"id": "old-v1", "engine": "vllm", "task": "htr", "enabled": False},
        {"id": "apertus-x", "engine": "vllm", "task": "htr", "enabled": True,
         "description": "Apertus, general multimodal instruction model (not HTR-tuned)"},
        {"broken": "no id"},
    ]
}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture
def registry_file(tmp_path):
    (tmp_path / "reg").mkdir()
    path = tmp_path / "reg" / "models.yaml"
    path.write_text(yaml.safe_dump(REGISTRY), encoding="utf-8")
    (tmp_path / "reg" / "trained").mkdir()
    (tmp_path / "reg" / "trained" / "kraken-b.yaml").write_text(
        yaml.safe_dump({"id": "kraken-b", "engine": "kraken", "task": "htr", "enabled": True}), encoding="utf-8")
    return path


@pytest.fixture
def client(tmp_path, registry_file, monkeypatch):
    monkeypatch.setenv("DHRA_MODELS_REGISTRY", str(registry_file))
    monkeypatch.delenv("DHRA_ATR_GATEWAY_URL", raising=False)
    return TestClient(build_app(DHRARepo(tmp_path / "store")))


def test_load_registry_merges_trained_and_skips_broken(registry_file):
    ids = [e.id for e in load_registry(registry_file)]
    assert ids == ["apertus-x", "kraken-a", "kraken-b", "old-v1"]


def test_kinds_and_enabled_filtering(registry_file):
    entries = load_registry(registry_file)
    assert [e.id for e in usable(entries, "htr")] == ["kraken-a", "kraken-b"]
    assert [e.id for e in usable(entries, "llm")] == ["apertus-x"]


def test_pickers_render_only_with_registry(client, tmp_path, monkeypatch):
    assert "kraken-a" in client.get("/ingest").text
    assert "apertus-x" in client.get("/chat").text
    assert "old-v1" not in client.get("/ingest").text
    monkeypatch.delenv("DHRA_MODELS_REGISTRY")
    plain = TestClient(build_app(DHRARepo(tmp_path / "store2")))
    assert 'name="model_id"' not in plain.get("/ingest").text
    assert 'name="llm_model_id"' not in plain.get("/chat").text


def test_image_with_registry_model_fails_loudly_without_gateway(client):
    resp = client.post("/ingest", data={"source_id": "s", "model_id": "kraken-a"},
                       files={"file": ("p.png", PNG, "image/png")})
    assert resp.status_code == 503
    assert "gateway" in resp.json()["detail"].lower()


def test_unknown_or_disabled_model_rejected(client):
    for bad in ("nope", "old-v1", "apertus-x"):
        resp = client.post("/ingest", data={"source_id": "s", "model_id": bad},
                           files={"file": ("p.png", PNG, "image/png")})
        assert resp.status_code == 400


def test_chat_with_registry_model_degrades_to_evidence_only_with_reason(client):
    resp = client.post("/chat", data={"message": "hello", "llm_model_id": "apertus-x"})
    assert resp.status_code == 200
    assert "gateway is not configured" in resp.text
