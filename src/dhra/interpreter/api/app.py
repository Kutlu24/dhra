from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response

from .. import speech, translate
from ..config import LANGUAGES
from ..rooms import Participant, registry

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="Simultaneous Interpreter")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/languages")
def languages() -> dict:
    return LANGUAGES


@app.post("/rooms")
def create_room() -> dict:
    room = registry.create()
    return {"room_id": room.room_id}


@app.get("/rooms/{room_id}")
def get_room(room_id: str) -> dict:
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(404, "Room not found")
    return {"room_id": room.room_id, "participant_count": len(room.participants)}


@app.websocket("/ws/{room_id}")
async def room_socket(websocket: WebSocket, room_id: str) -> None:
    await websocket.accept()
    join_msg = await websocket.receive_json()
    language = join_msg.get("language")
    if language not in LANGUAGES:
        await websocket.close(code=4400, reason="Unknown language")
        return

    room = registry.get_or_create(room_id)
    room.participants[id(websocket)] = Participant(websocket=websocket, language=language)
    await room.broadcast({"type": "presence", "participant_count": len(room.participants)})

    try:
        while True:
            # No further client->server messages expected right now (audio
            # goes over the separate POST /rooms/{id}/speak below, not this
            # socket) - just block here so we notice a disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        room.participants.pop(id(websocket), None)
        await room.broadcast({"type": "presence", "participant_count": len(room.participants)})
        registry.drop_if_empty(room_id)


@app.post("/rooms/{room_id}/speak")
async def speak(room_id: str, audio: UploadFile, language: str = Form(...)) -> dict:
    room = registry.get(room_id)
    if room is None:
        raise HTTPException(404, "Room not found")
    if language not in LANGUAGES:
        raise HTTPException(400, "Unknown language")

    audio_bytes = await audio.read()
    try:
        # transcribe() is CPU-bound (local Whisper inference, no network
        # wait to hide it behind) - off the event loop so one room's
        # transcription doesn't stall every other room's broadcasts.
        original_text = await asyncio.to_thread(
            speech.transcribe, audio_bytes, audio.filename or "utterance.webm", language
        )
    except speech.SpeechError as exc:
        raise HTTPException(502, f"Transcription failed: {exc}") from exc

    if not original_text:
        return {"skipped": True}

    targets = room.all_languages() - {language}

    async def _translate_one(target: str) -> tuple[str, str, bool]:
        # translate.translate() makes a real, blocking network call - off
        # the event loop for the same reason transcribe() is above.
        # Previously this ran un-awaited sync code directly inside an
        # async handler: it blocked the ENTIRE process (every room, every
        # open WebSocket) for the duration of each translation call, not
        # just this request - the likely real cause behind both "very
        # slow" and the WebSocket disconnects (a blocked event loop can't
        # service other connections' sends/pings either). Running every
        # target in parallel via asyncio.gather (not a sequential loop)
        # also means N target languages no longer means N times the wait.
        try:
            return target, await asyncio.to_thread(translate.translate, original_text, target), True
        except translate.TranslationError:
            return target, original_text, False  # degrade to original rather than drop the utterance

    results = await asyncio.gather(*(_translate_one(t) for t in targets))
    translations: dict[str, str] = {}
    translation_failed: dict[str, bool] = {}
    for target, text, ok in results:
        translations[target] = text
        if not ok:
            translation_failed[target] = True

    await room.broadcast(
        {
            "type": "utterance",
            "speaker_language": language,
            "original_text": original_text,
            "translations": translations,
            "translation_failed": translation_failed,
        }
    )
    return {
        "skipped": False,
        "original_text": original_text,
        "translations": translations,
        "translation_failed": translation_failed,
    }


@app.post("/tts")
def tts(text: str = Form(...), language: str = Form("")) -> Response:
    if not text.strip():
        raise HTTPException(400, "Empty text")
    try:
        audio_bytes = speech.synthesize(text, language)
    except speech.SpeechError as exc:
        raise HTTPException(502, f"Speech synthesis failed: {exc}") from exc
    return Response(content=audio_bytes, media_type="audio/mpeg")
