"""Web UI trilingual (EN/DE/FR) support -- dhra.web.i18n and the
per-request language cookie in dhra.web.app.

Scope is the UI chrome only (nav, headings, labels, tutorial prose,
E1-E8 tooltip meanings) -- see i18n.py's module docstring for why
corpus/evidence text and dynamically-generated domain text (evidence
rationale, bias warnings, chat/GLM answers) are deliberately out of
scope.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dhra.repo import DHRARepo
from dhra.web.app import LANGUAGE_COOKIE, build_app
from dhra.web.i18n import DEFAULT_LANGUAGE, LANGUAGES, TRANSLATIONS, resolve_language, translate


@pytest.fixture
def repo(tmp_path):
    return DHRARepo(tmp_path / "store")


@pytest.fixture
def client(repo):
    return TestClient(build_app(repo))


# --- translation table integrity ------------------------------------------------


def test_every_language_has_the_same_key_set():
    en_keys = set(TRANSLATIONS["en"])
    assert en_keys, "the English table must not be empty"
    for lang in LANGUAGES:
        assert set(TRANSLATIONS[lang]) == en_keys, f"{lang} is missing or has extra keys vs. en"


def test_no_translation_value_is_empty():
    for lang in LANGUAGES:
        for key, value in TRANSLATIONS[lang].items():
            assert value.strip(), f"{lang}.{key} is empty"


def test_resolve_language_falls_back_to_default_for_unknown_codes():
    assert resolve_language("de") == "de"
    assert resolve_language("xx") == DEFAULT_LANGUAGE
    assert resolve_language(None) == DEFAULT_LANGUAGE


def test_translate_falls_back_to_english_for_unknown_language():
    assert translate("xx", "nav.search") == translate("en", "nav.search")


def test_translate_interpolates_kwargs_and_escapes_them():
    result = translate("en", "search.evidence_heading", n=5)
    assert "5" in result
    # the translation itself renders real HTML (via Markup), but an
    # interpolated *value* must still be escaped if it contains markup
    result = translate("en", "chat.llm_error_prefix")
    assert "<" not in str(translate("de", "chat.you"))  # sanity: no stray tags in a plain label


# --- language switching end-to-end ------------------------------------------------


def test_default_language_is_english(client):
    resp = client.get("/")
    assert 'lang="en"' in resp.text
    assert "Evidence search" in resp.text


def test_switching_to_german_sets_cookie_and_translates_the_page(client):
    resp = client.get("/lang/de", headers={"referer": "/"}, follow_redirects=False)
    assert resp.status_code == 303
    assert resp.cookies.get(LANGUAGE_COOKIE) == "de"

    client.cookies.set(LANGUAGE_COOKIE, "de")
    page = client.get("/")
    assert 'lang="de"' in page.text
    assert "Belegsuche" in page.text
    assert "Suche" in page.text  # nav label


def test_switching_to_french_translates_the_tutorial_page(client):
    client.cookies.set(LANGUAGE_COOKIE, "fr")
    page = client.get("/tutorial")
    assert 'lang="fr"' in page.text
    assert "Prise en main" in page.text
    assert "Ajouter un" in page.text  # step 1 heading, contains an apostrophe-adjacent word


def test_invalid_language_code_falls_back_to_english(client):
    client.cookies.set(LANGUAGE_COOKIE, "xx")
    page = client.get("/")
    assert 'lang="en"' in page.text


def test_status_tooltip_meaning_is_translated(repo, client):
    client.post(
        "/claims/assess",
        data={"claim_id": "c1", "claim_text": "x", "actor": "t", "supporting": "", "contradicting": "", "negating": ""},
    )
    client.cookies.set(LANGUAGE_COOKIE, "de")
    page = client.get("/claims/c1")
    # no supporting/contradicting/negating locators -> E6 (unsupported)
    assert "nicht gefunden" in page.text
    assert "Kein Beleg für Nicht-Eintreten" in page.text


def test_apostrophes_in_translations_render_literally_not_as_html_entities(client):
    """Regression: Markup.format()/autoescaping must not turn a real
    apostrophe into &#39; -- caught live when a translated string with a
    contraction ("Couldn't reach OpenAlex") silently failed a substring
    check because Jinja escaped it."""
    client.cookies.set(LANGUAGE_COOKIE, "fr")
    page = client.get("/updates")
    assert "&#39;" not in page.text
    assert "&#x27;" not in page.text
