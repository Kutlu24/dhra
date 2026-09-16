"""Core data model -- DHRA_BUILD_SPEC.md section 4.

Every entity is a frozen dataclass: nothing here is ever mutated in place.
State change happens only by appending a new event to the log
(see dhra.store.events) and folding it into a new value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


# --- 4.2 Core entities ------------------------------------------------------


@dataclass(frozen=True)
class Acquisition:
    source_id: str
    retrieved_at: datetime
    method: str  # "api" | "download" | "manual_upload" | "mcp"
    request: dict | None
    access_basis: str  # "public_domain" | "licensed" | "tdm_exception" | "permission" | "unknown"
    licence_id: str | None
    redistributable: bool | None  # None = unknown, and unknown is not permission
    original_reference: str | None  # shelfmark, URL, call number


@dataclass(frozen=True)
class Item:
    item_id: str  # ULID
    blob_sha256: str
    media_type: str
    byte_length: int
    acquisition: Acquisition


# --- 4.3 Representations -- the transformation chain ------------------------


@dataclass(frozen=True)
class Quality:
    mean_char_confidence: float | None = None  # 0..1
    per_span_confidence: tuple[tuple[int, int, float], ...] = ()
    script: str | None = None
    manually_corrected: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class Representation:
    rep_id: str
    item_id: str
    parent_rep_id: str | None  # None = derived directly from blob
    kind: str  # "transcription" | "translation" | "normalisation" | "segmentation"
    producer: str  # tool name
    producer_version: str  # REQUIRED -- pinned
    parameters: dict
    created_at: datetime
    text: str
    quality: Quality | None = None

    def __post_init__(self) -> None:
        if not self.producer_version:
            raise ValueError(
                f"Representation {self.rep_id}: producer_version is mandatory "
                "-- an unversioned transformation is not reproducible."
            )


# --- 4.4 Assertions -- metadata as testimony, not fact ----------------------


@dataclass(frozen=True)
class Locator:
    item_id: str
    rep_id: str  # WHICH representation -- a locator into a translation is not a locator into the source
    start: int
    end: int
    page: str | None = None
    iiif_region: str | None = None


@dataclass(frozen=True)
class Assertion:
    assertion_id: str
    subject_item_id: str
    predicate: str  # "title" | "creator" | "date" | "place" | "genre" | "language"
    value: str  # normalised value, for indexing
    original_expression: str  # exactly as it appeared in the source
    asserted_by: str  # "catalogue:BL" | "researcher" | "tool:date_parser@1.2"
    asserted_at: datetime
    confidence: str  # "stated" | "inferred" | "uncertain"
    evidence_locator: Locator | None = None


# --- 4.5 Dates ---------------------------------------------------------------


@dataclass(frozen=True)
class DateClaim:
    original_expression: str  # "12 Rebiulevvel 1265"
    calendar: str  # "gregorian"|"julian"|"hijri"|"rumi"|"regnal"|"french_republican"|"unknown"
    precision: str  # "day"|"month"|"year"|"decade"|"range"|"terminus_ante_quem"|...
    asserted_by: str
    converted_iso: str | None = None  # only if conversion is defensible
    conversion_method: str | None = None
    range_start: str | None = None
    range_end: str | None = None

    def __post_init__(self) -> None:
        if not self.original_expression:
            raise ValueError("DateClaim requires original_expression -- never store a bare ISO date.")
        if not self.calendar:
            raise ValueError("DateClaim requires calendar -- never store a bare ISO date.")


# --- 4.7 Exclusions ----------------------------------------------------------


class ExclusionReason(StrEnum):
    OUT_OF_DATE_RANGE = "out_of_date_range"
    WRONG_LANGUAGE = "wrong_language"
    DESCENT_CLUSTER_MEMBER = "descent_cluster_member"
    BELOW_RELEVANCE = "below_relevance_threshold"
    ACCESS_DENIED = "access_denied"
    FORMAT_UNREADABLE = "format_unreadable"
    BELOW_QUALITY = "below_quality_threshold"
    DATE_UNRESOLVED = "date_unresolved"
    RESEARCHER_EXCLUDED = "researcher_excluded"


@dataclass(frozen=True)
class Exclusion:
    item_id: str
    reason: ExclusionReason
    actor: str
    ts: datetime
    threshold: float | None = None
    observed: float | None = None
    reversible: bool = True


# --- 8.1 Resolved passage (needed for Locator.resolve, wired in store) ------


@dataclass(frozen=True)
class ResolvedPassage:
    item_id: str
    rep_id: str
    text: str
    page: str | None
    iiif_region: str | None


# --- 8.1 Locator-bound search result -----------------------------------------


@dataclass(frozen=True)
class Passage:
    """A search result. `rationale` must be stated in terms a researcher
    can dispute -- never an opaque score alone (section 8.1)."""

    locator: Locator
    text: str  # exact match to Locator.resolve().text -- verified by the response contract
    score: float
    rationale: str
