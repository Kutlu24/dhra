"""Shared corpora with annotation threads -- DHRA_BUILD_SPEC.md section 6
(Phase 4).

"Shared" here means what local-first actually gives you for free: the
event log itself is the shared medium (section 16: "the system must run
fully on a researcher's laptop... institutional DH infrastructure is
rare, assume its absence") -- if two researchers point their own DHRA at
the same `store/` directory (e.g. a synced folder, or later a real
multi-writer backend), they already see each other's annotations,
because annotations are just events like everything else. No separate
account/permissions system is built (see OPEN_QUESTIONS.md) -- `actor`
is a free-text identifier, not an authenticated user.

Annotations attach to any target (`item`, `claim`, `assertion`, ...) by
id -- a thread is not a corpus mutation (I4 still applies: nothing here
deletes or alters the thing being annotated).
"""

from __future__ import annotations

from dataclasses import dataclass

from dhra.repo import DHRARepo
from dhra.ulid import new_ulid


@dataclass(frozen=True)
class Annotation:
    annotation_id: str
    target_type: str  # "item" | "claim" | "assertion" | ...
    target_id: str
    text: str
    actor: str
    ts: str
    resolved: bool


def add_annotation(repo: DHRARepo, *, target_type: str, target_id: str, text: str, actor: str, task: str | None = None) -> str:
    annotation_id = new_ulid()
    repo.events.append(
        "annotation.added",
        annotation_id=annotation_id,
        target_type=target_type,
        target_id=target_id,
        text=text,
        actor=actor,
        task=task,
    )
    return annotation_id


def resolve_annotation(repo: DHRARepo, *, annotation_id: str, actor: str, task: str | None = None) -> None:
    repo.events.append("annotation.resolved", annotation_id=annotation_id, actor=actor, task=task)


def annotations_for(repo: DHRARepo, *, target_type: str, target_id: str) -> list[Annotation]:
    by_id: dict[str, Annotation] = {}
    for event in repo.events.read_all():
        if event["type"] == "annotation.added" and event["target_type"] == target_type and event["target_id"] == target_id:
            by_id[event["annotation_id"]] = Annotation(
                annotation_id=event["annotation_id"],
                target_type=target_type,
                target_id=target_id,
                text=event["text"],
                actor=event["actor"],
                ts=event["ts"],
                resolved=False,
            )
        elif event["type"] == "annotation.resolved" and event["annotation_id"] in by_id:
            existing = by_id[event["annotation_id"]]
            by_id[event["annotation_id"]] = Annotation(
                annotation_id=existing.annotation_id,
                target_type=existing.target_type,
                target_id=existing.target_id,
                text=existing.text,
                actor=existing.actor,
                ts=existing.ts,
                resolved=True,
            )
    return sorted(by_id.values(), key=lambda a: a.ts)
