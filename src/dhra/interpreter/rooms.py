"""In-memory room state only - no database. A room is a live call: it
exists only while people are in it, nothing about it needs to survive a
process restart or be looked up later, so persisting it would be pure
overhead (unlike fundraising-assistant/job-suche, which track real
records across sessions).
"""
from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass, field

from fastapi import WebSocket


MAX_ROOMS = 200            # process-wide: rooms are in memory, so cap them
MAX_PARTICIPANTS = 50      # per room
UNJOINED_ROOM_TTL = 600.0  # seconds a created-but-never-joined room is kept
ROOM_ID_RE = re.compile(r"^[0-9a-f]{6,16}$")


class RoomLimitError(Exception):
    pass


def valid_room_id(room_id: str) -> bool:
    return bool(ROOM_ID_RE.match(room_id))


def new_room_id() -> str:
    # 10 hex chars (~1e12 codes): still typeable, no longer guessable by
    # trying codes. (Legacy 6-char codes remain valid input.)
    return secrets.token_hex(5)


@dataclass
class Participant:
    websocket: WebSocket
    language: str


@dataclass
class Room:
    room_id: str
    participants: dict[int, Participant] = field(default_factory=dict)
    created_at: float = field(default_factory=time.monotonic)

    def other_languages(self, exclude_ws: WebSocket) -> set[str]:
        return {p.language for ws_id, p in self.participants.items() if p.websocket is not exclude_ws}

    def all_languages(self) -> set[str]:
        return {p.language for p in self.participants.values()}

    async def broadcast(self, message: dict) -> None:
        dead: list[int] = []
        for ws_id, p in self.participants.items():
            try:
                await p.websocket.send_json(message)
            except Exception:  # noqa: BLE001 - a dead socket here shouldn't break delivery to everyone else
                dead.append(ws_id)
        for ws_id in dead:
            self.participants.pop(ws_id, None)


class RoomRegistry:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def _purge_stale(self) -> None:
        cutoff = time.monotonic() - UNJOINED_ROOM_TTL
        for rid in [rid for rid, r in self._rooms.items() if not r.participants and r.created_at < cutoff]:
            del self._rooms[rid]

    def _check_capacity(self) -> None:
        self._purge_stale()
        if len(self._rooms) >= MAX_ROOMS:
            raise RoomLimitError("Too many active rooms; try again later.")

    def create(self) -> Room:
        self._check_capacity()
        room_id = new_room_id()
        while room_id in self._rooms:
            room_id = new_room_id()
        room = Room(room_id=room_id)
        self._rooms[room_id] = room
        return room

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def get_or_create(self, room_id: str) -> Room:
        room = self._rooms.get(room_id)
        if room is None:
            self._check_capacity()
            room = self._rooms[room_id] = Room(room_id=room_id)
        return room

    def drop_if_empty(self, room_id: str) -> None:
        room = self._rooms.get(room_id)
        if room is not None and not room.participants:
            del self._rooms[room_id]


registry = RoomRegistry()
