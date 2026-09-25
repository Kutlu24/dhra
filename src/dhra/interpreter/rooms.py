"""In-memory room state only - no database. A room is a live call: it
exists only while people are in it, nothing about it needs to survive a
process restart or be looked up later, so persisting it would be pure
overhead (unlike fundraising-assistant/job-suche, which track real
records across sessions).
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from fastapi import WebSocket


def new_room_id() -> str:
    return secrets.token_hex(3)  # 6 hex chars - short enough to read aloud/type, ~16M possible codes


@dataclass
class Participant:
    websocket: WebSocket
    language: str


@dataclass
class Room:
    room_id: str
    participants: dict[int, Participant] = field(default_factory=dict)

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

    def create(self) -> Room:
        room_id = new_room_id()
        while room_id in self._rooms:
            room_id = new_room_id()
        room = Room(room_id=room_id)
        self._rooms[room_id] = room
        return room

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get(room_id)

    def get_or_create(self, room_id: str) -> Room:
        return self._rooms.setdefault(room_id, Room(room_id=room_id))

    def drop_if_empty(self, room_id: str) -> None:
        room = self._rooms.get(room_id)
        if room is not None and not room.participants:
            del self._rooms[room_id]


registry = RoomRegistry()
