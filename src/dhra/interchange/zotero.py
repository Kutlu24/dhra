"""Zotero interchange -- DHRA_BUILD_SPEC.md section 6 (Phase 3).

Maps to/from Zotero's item JSON shape (the format Zotero's own API and
Better BibTeX use), not the Zotero API itself -- no OAuth/API key
wiring here, this is local, offline, real data-shape interchange. A
live sync integration is future work once there's a reason to hold
Zotero credentials (see OPEN_QUESTIONS.md).
"""

from __future__ import annotations

from dhra.models import Assertion, Item

_PREDICATE_TO_ZOTERO_FIELD = {
    "title": "title",
    "date": "date",
    "place": "place",
    "genre": "itemType",
    "language": "language",
}


def _find(assertions: list[Assertion], predicate: str) -> str | None:
    for a in assertions:
        if a.predicate == predicate:
            return a.value
    return None


def to_zotero_item(item: Item, assertions: list[Assertion] | None = None) -> dict:
    assertions = assertions or []
    creators = [
        {"creatorType": "author", "name": a.value}
        for a in assertions
        if a.predicate == "creator"
    ]
    zotero_item: dict = {
        "itemType": _find(assertions, "genre") or "document",
        "title": _find(assertions, "title") or f"Untitled ({item.item_id})",
        "creators": creators,
    }
    for predicate, field in _PREDICATE_TO_ZOTERO_FIELD.items():
        if predicate in ("title", "genre"):
            continue
        value = _find(assertions, predicate)
        if value:
            zotero_item[field] = value
    if item.acquisition.original_reference:
        zotero_item["url"] = item.acquisition.original_reference
    if item.acquisition.licence_id:
        zotero_item["rights"] = item.acquisition.licence_id
    zotero_item["extra"] = f"DHRA item_id: {item.item_id}"
    return zotero_item


def from_zotero_item(zotero_item: dict, *, asserted_by: str) -> list[dict]:
    """Returns plain dicts shaped for `DHRARepo.add_assertion(**d)`
    (minus `subject_item_id`, which the caller supplies) -- not
    Assertion objects directly, since an assertion needs an
    already-acquired item_id this function has no way to know."""
    out: list[dict] = []
    if zotero_item.get("title"):
        out.append(
            {
                "predicate": "title",
                "value": zotero_item["title"],
                "original_expression": zotero_item["title"],
                "asserted_by": asserted_by,
                "confidence": "stated",
            }
        )
    for creator in zotero_item.get("creators", []):
        name = creator.get("name") or " ".join(filter(None, [creator.get("firstName"), creator.get("lastName")]))
        if name:
            out.append(
                {
                    "predicate": "creator",
                    "value": name,
                    "original_expression": name,
                    "asserted_by": asserted_by,
                    "confidence": "stated",
                }
            )
    for field, predicate in {"date": "date", "place": "place", "language": "language"}.items():
        value = zotero_item.get(field)
        if value:
            out.append(
                {
                    "predicate": predicate,
                    "value": value,
                    "original_expression": value,
                    "asserted_by": asserted_by,
                    "confidence": "stated",
                }
            )
    return out
