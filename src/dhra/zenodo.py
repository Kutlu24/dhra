"""Zenodo acquisition -- DHRA_BUILD_SPEC.md section 9 (tool layer,
permissions, licence + rate-limit enforcement) applied to a real archive.

Zenodo (zenodo.org) chosen as the Phase 3 target: open REST API,
published rate limits, no auth needed for public records -- and already
used for real in the sibling `ottoman-manuscript-htr` project (the
OpenITI MAKHZAN corpus), so its API shape and licensing metadata are
already known-good in this environment.

This is the one module in the repo that makes real outbound network
calls. Every call goes through `RateLimiter.check()` first (hard
constraint, section 9.2) and identifies itself via `source.identify_as`
in the User-Agent (section 9.2: "identify in every request").
`acquire_from_zenodo` is `PermissionClass.ASK`: it will not touch the
network at all until a matching `approval.granted` event exists.
"""

from __future__ import annotations

import requests

from dhra.permissions import ActionSpec, PermissionClass, check_permission
from dhra.rate_limit import RateLimiter
from dhra.source_registry import SourceEntry

ZENODO_API_BASE = "https://zenodo.org/api"


class ZenodoAccessError(Exception):
    pass


def fetch_record_metadata(record_id: str, *, source: SourceEntry, limiter: RateLimiter, session: requests.Session | None = None, timeout: float = 30.0) -> dict:
    limiter.check(source)
    session = session or requests.Session()
    resp = session.get(
        f"{ZENODO_API_BASE}/records/{record_id}",
        headers={"User-Agent": source.identify_as},
        timeout=timeout,
    )
    if resp.status_code == 404:
        raise ZenodoAccessError(f"Zenodo record {record_id} not found (404)")
    resp.raise_for_status()
    return resp.json()


def download_file(file_entry: dict, *, source: SourceEntry, limiter: RateLimiter, session: requests.Session | None = None, timeout: float = 60.0) -> bytes:
    if source.bulk_download == "prohibited":
        raise ZenodoAccessError(f"{source.id}: bulk_download is prohibited by the source registry")
    limiter.check(source)
    session = session or requests.Session()
    url = file_entry["links"]["self"]
    resp = session.get(url, headers={"User-Agent": source.identify_as}, timeout=timeout)
    resp.raise_for_status()
    return resp.content


def acquire_from_zenodo(
    repo,
    *,
    record_id: str,
    filename: str | None,
    source: SourceEntry,
    limiter: RateLimiter,
    actor: str,
    task: str | None = None,
    session: requests.Session | None = None,
) -> str:
    """ASK-class tool (section 9.1): the acquisition specifics must be
    approved (`repo.grant_approval(tool="acquire_from_zenodo", ...)`)
    with the exact same summary this builds, before any network call
    happens. Records every licence constraint on the resulting Item
    (I11) -- access_basis from the registry's tdm_basis, licence_id and
    redistributable from Zenodo's own metadata, never assumed."""
    summary = f"Acquire Zenodo record {record_id}" + (f" file {filename!r}" if filename else " (metadata only)") + f" from {source.id}."
    spec = ActionSpec(
        tool="acquire_from_zenodo",
        summary=summary,
        details={"record_id": record_id, "filename": filename, "source_id": source.id},
    )
    check_permission(repo, PermissionClass.ASK, spec, actor=actor)

    metadata = fetch_record_metadata(record_id, source=source, limiter=limiter, session=session)
    licence_info = (metadata.get("metadata") or {}).get("license") or {}
    licence_id = licence_info.get("id")
    redistributable = source.redistribution == "permitted"

    if filename is None:
        data = repr(metadata).encode("utf-8")
        media_type = "application/json"
    else:
        files = (metadata.get("files") or [])
        matches = [f for f in files if f.get("key") == filename]
        if not matches:
            raise ZenodoAccessError(f"file {filename!r} not found in Zenodo record {record_id}")
        data = download_file(matches[0], source=source, limiter=limiter, session=session)
        media_type = matches[0].get("type", "application/octet-stream")

    item_id = repo.acquire_item(
        data,
        source_id=source.id,
        method="api",
        access_basis=source.tdm_basis,
        media_type=media_type,
        licence_id=licence_id,
        redistributable=redistributable,
        original_reference=f"https://zenodo.org/records/{record_id}",
        request={"record_id": record_id, "filename": filename},
        task=task,
    )

    return item_id
