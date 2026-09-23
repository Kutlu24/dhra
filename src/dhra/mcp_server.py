"""MCP server exposing the tool layer -- DHRA_BUILD_SPEC.md section 6
(Phase 3) and section 16 ("MCP: official SDK, both server ... and
client"). Built on the real `mcp` SDK (`mcp.server.mcpserver.MCPServer`,
the current name for what used to be `FastMCP` -- see
OPEN_QUESTIONS.md for the version note).

Each tool function catches its own known failure modes
(`ApprovalRequired`, `RateLimitExceeded`, `ZenodoAccessError`) and
returns a structured `{"status": ...}` dict rather than letting them
propagate as raw exceptions -- `MCPServer.call_tool` (used directly, not
through a live transport) does not itself catch tool exceptions into an
error result, so a caller (or a test) gets a clean, typed outcome either
way.
"""

from __future__ import annotations

from typing import Any

from dhra.evidence import search as evidence_search
from dhra.permissions import ApprovalRequired
from dhra.rate_limit import RateLimitExceeded, RateLimiter
from dhra.repo import DHRARepo
from dhra.source_registry import SourceEntry
from dhra.zenodo import ZenodoAccessError, acquire_from_zenodo


def _response_to_dict(response) -> dict[str, Any]:
    return {
        "evidence": [
            {
                "item_id": p.locator.item_id,
                "rep_id": p.locator.rep_id,
                "start": p.locator.start,
                "end": p.locator.end,
                "text": p.text,
                "score": p.score,
                "rationale": p.rationale,
            }
            for p in response.evidence
        ],
        "narrative": response.narrative,
        "absence_note": response.absence_note,
        "variant_expansion": list(response.variant_expansion),
        "corpus_version": response.corpus_version,
    }


def build_mcp_server(
    repo: DHRARepo,
    *,
    zenodo_source: SourceEntry | None = None,
    rate_limiter: RateLimiter | None = None,
    name: str = "dhra",
):
    from mcp.server.mcpserver import MCPServer

    server = MCPServer(name=name, description="Digital Humanities Research Assistant tool layer")
    limiter = rate_limiter or RateLimiter()

    @server.tool(name="search_evidence", description="Locator-bound, quality-qualified full-text search over the corpus (READ).")
    def search_evidence(query: str, variants: list[str] | None = None) -> dict[str, Any]:
        response = evidence_search(repo, query, variants=variants)
        return _response_to_dict(response)

    @server.tool(name="get_corpus_version", description="Current corpus version manifest and hash (READ).")
    def get_corpus_version() -> dict[str, Any]:
        version = repo.corpus_version()
        return {
            "seq": version.seq,
            "manifest_hash": version.manifest_hash,
            "item_count": len(version.item_ids),
        }

    @server.tool(name="request_zenodo_acquisition", description="Request acquiring a Zenodo record/file (ASK -- requires prior approval via grant_approval).")
    def request_zenodo_acquisition(record_id: str, filename: str | None, actor: str) -> dict[str, Any]:
        if zenodo_source is None:
            return {"status": "error", "message": "no Zenodo source configured for this server"}
        try:
            item_id = acquire_from_zenodo(
                repo,
                record_id=record_id,
                filename=filename,
                source=zenodo_source,
                limiter=limiter,
                actor=actor,
            )
            return {"status": "acquired", "item_id": item_id}
        except ApprovalRequired as e:
            return {"status": "approval_required", "tool": e.spec.tool, "summary": e.spec.summary, "details": e.spec.details}
        except RateLimitExceeded as e:
            return {"status": "rate_limited", "message": str(e)}
        except ZenodoAccessError as e:
            return {"status": "access_error", "message": str(e)}

    @server.tool(name="grant_approval", description="Approve a specific pending ASK-class action, scoped to its exact summary (never the whole session).")
    def grant_approval(tool: str, summary: str, actor: str) -> dict[str, Any]:
        repo.grant_approval(tool=tool, summary=summary, actor=actor)
        return {"status": "granted", "tool": tool, "summary": summary}

    @server.tool(name="deny_approval", description="Deny a specific pending ASK-class action, with a reason (logged either way, section 9.1).")
    def deny_approval(tool: str, summary: str, reason: str, actor: str) -> dict[str, Any]:
        repo.deny_approval(tool=tool, summary=summary, reason=reason, actor=actor)
        return {"status": "denied", "tool": tool, "summary": summary}

    return server
