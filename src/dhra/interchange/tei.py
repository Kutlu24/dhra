"""TEI export -- DHRA_BUILD_SPEC.md section 6 (Phase 3: "Zotero and TEI
interchange"). `dhra.transcribe.TeiTranscriber` already imports *from*
TEI; this is the other direction, completing the round trip.

Deliberately minimal TEI (title, source reference, licence, the
representation text) -- enough for a researcher to move a transcription
into a TEI-aware tool, not a full TEI encoding of every DHRA field.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from dhra.models import Assertion, Item, Representation


def _find(assertions: list[Assertion], predicate: str) -> str | None:
    for a in assertions:
        if a.predicate == predicate:
            return a.value
    return None


def to_tei(item: Item, representation: Representation, assertions: list[Assertion] | None = None) -> str:
    assertions = assertions or []
    title = _find(assertions, "title") or f"Untitled ({item.item_id})"
    author = _find(assertions, "creator")
    date_value = _find(assertions, "date")

    title_stmt = f"<title>{escape(title)}</title>"
    if author:
        title_stmt += f"\n      <author>{escape(author)}</author>"

    source_bibl = f'<bibl type="original_reference">{escape(item.acquisition.original_reference or "")}</bibl>'
    if item.acquisition.licence_id:
        source_bibl += f'\n      <bibl type="licence">{escape(item.acquisition.licence_id)}</bibl>'
    if date_value:
        source_bibl += f'\n      <date>{escape(date_value)}</date>'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
      {title_stmt}
      </titleStmt>
      <publicationStmt>
        <p>Exported from DHRA (Digital Humanities Research Assistant).</p>
      </publicationStmt>
      <sourceDesc>
      {source_bibl}
      </sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <p>{escape(representation.text)}</p>
    </body>
  </text>
</TEI>
"""
