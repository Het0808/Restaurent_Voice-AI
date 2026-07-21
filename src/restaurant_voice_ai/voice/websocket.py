"""Versioned WebSocket protocol handler for browser PCM sessions."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.observability.metrics import metrics
from restaurant_voice_ai.voice.audio import (
    UtteranceBuffer,
    VoiceProtocolError,
    chunk_audio,
    validate_audio_frame,
)
from restaurant_voice_ai.voice.models import (
    AudioFormat,
    AudioFrame,
    SessionStatus,
    VoiceSession,
    VoiceSessionRuntime,
)
from restaurant_voice_ai.voice.service import VoiceService, VoiceServiceError, VoiceTurnResult
from restaurant_voice_ai.voice.session_manager import SessionManager
from restaurant_voice_ai.voice.vad import EnergyVoiceActivityDetector

PROTOCOL_VERSION = "1.0"


class AudioStart(BaseModel):
    format: AudioFormat = AudioFormat.PCM_S16LE
    sample_rate: int = 16000
    channels: int = 1
    frame_duration_ms: int = 20


class SessionStart(BaseModel):
    type: str
    protocol_version: str
    language: str | None = None
    audio: AudioStart


async def send_json_safe(websocket: WebSocket, lock: asyncio.Lock, event: dict[str, Any]) -> None:
    async with lock:
        await websocket.send_json(event)


async def send_error(
    websocket: WebSocket,
    lock: asyncio.Lock,
    code: str,
    message: str,
    recoverable: bool = True,
) -> None:
    await send_json_safe(
        websocket,
        lock,
        {"type": "error", "code": code, "message": message, "recoverable": recoverable},
    )


async def handle_voice_websocket(
    websocket: WebSocket,
    settings: Settings,
    service: VoiceService,
    manager: SessionManager,
    *,
    conversation_id: str | None,
    requested_language: str | None,
    auth_identity: str = "anonymous",
) -> None:
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.voice_allowed_origins:
        await websocket.close(code=1008, reason="Origin is not allowed")
        return
    if not settings.voice_enabled:
        await websocket.close(code=1008, reason="Voice is disabled")
        return
    await websocket.accept()
    language = requested_language or settings.voice_default_language
    try:
        language = service.resolve_language(language)
    except VoiceServiceError:
        await websocket.close(code=1008, reason="Unsupported language")
        return
    session = VoiceSession(
        session_id=str(uuid.uuid4()),
        conversation_id=conversation_id or str(uuid.uuid4()),
        language=language,
        input_format=AudioFormat(settings.voice_input_format),
        input_sample_rate=settings.voice_input_sample_rate,
        output_format=AudioFormat(settings.voice_output_format),
        output_sample_rate=settings.voice_output_sample_rate,
        metadata={"auth_identity": auth_identity},
    )
    runtime = VoiceSessionRuntime(session, settings.voice_max_pending_frames)
    try:
        await manager.register(runtime)
        metrics.voice_sessions.labels("opened").inc()
        metrics.active_voice_sessions.inc()
    except ValueError:
        await send_error(
            websocket, asyncio.Lock(), "session_limit", "No voice session is available.", False
        )
        await websocket.close(code=1013)
        return
    send_lock = asyncio.Lock()
    vad = EnergyVoiceActivityDetector(settings.voice_energy_threshold)
    max_utterance_bytes = (
        settings.voice_input_sample_rate * 2 * settings.voice_max_utterance_seconds
    )
    buffer = UtteranceBuffer(
        max_utterance_bytes,
        settings.voice_pre_speech_buffer_ms // settings.voice_frame_duration_ms,
    )
    initialized = False
    turn_task: asyncio.Task[None] | None = None

    async def interrupt() -> None:
        nonlocal turn_task
        if turn_task is not None and not turn_task.done() and session.assistant_playing:
            turn_task.cancel()
            session.interruption_count += 1
            session.assistant_playing = False
            await send_json_safe(
                websocket,
                send_lock,
                {"type": "assistant.audio.end", "interrupted": True},
            )

    async def emit_turn(audio: bytes) -> None:
        try:
            result: VoiceTurnResult = await service.process_completed_utterance(runtime, audio)
            await send_json_safe(
                websocket,
                send_lock,
                {
                    "type": "transcript.final",
                    "text": result.transcript,
                    "language": result.language,
                },
            )
            response = result.response
            await send_json_safe(
                websocket,
                send_lock,
                {
                    "type": "assistant.text",
                    "text": response.response_text,
                    "intent": response.intent.value,
                    "response_type": response.response_type.value,
                    "turn_number": response.turn_number,
                    "confirmation_required": response.confirmation_required,
                },
            )
            if result.synthesis is None:
                await send_error(
                    websocket,
                    send_lock,
                    "tts_unavailable",
                    result.tts_error or "Audio unavailable.",
                )
                return
            session.assistant_playing = True
            await send_json_safe(
                websocket,
                send_lock,
                {
                    "type": "assistant.audio.start",
                    "audio": {
                        "format": result.synthesis.format.value,
                        "sample_rate": result.synthesis.sample_rate,
                        "channels": result.synthesis.channels,
                    },
                },
            )
            for chunk in chunk_audio(result.synthesis.audio, settings.voice_tts_chunk_bytes):
                async with send_lock:
                    await websocket.send_bytes(chunk)
                await asyncio.sleep(0)
            session.assistant_playing = False
            await send_json_safe(
                websocket, send_lock, {"type": "assistant.audio.end", "interrupted": False}
            )
        except asyncio.CancelledError:
            raise
        except VoiceServiceError as error:
            await send_error(websocket, send_lock, error.code, error.safe_message)
        except Exception:
            await send_error(websocket, send_lock, "internal_error", "The voice turn failed.")

    async def commit() -> None:
        nonlocal turn_task
        if buffer.speech_ms < settings.voice_min_speech_ms:
            await send_error(websocket, send_lock, "no_speech", "No speech was detected.")
            buffer.reset()
            return
        if turn_task is not None and not turn_task.done():
            await send_error(
                websocket, send_lock, "session_busy", "A voice turn is still processing."
            )
            buffer.reset()
            return
        audio = buffer.snapshot()
        buffer.reset()
        vad.reset()
        session.speech_state = "idle"
        await send_json_safe(websocket, send_lock, {"type": "speech.ended"})
        turn_task = asyncio.create_task(emit_turn(audio))

    try:
        while True:
            now = datetime.now(UTC)
            maximum_deadline = session.connected_at + timedelta(
                seconds=settings.voice_max_session_seconds
            )
            remaining_session = (maximum_deadline - now).total_seconds()
            if remaining_session <= 0:
                await send_json_safe(
                    websocket,
                    send_lock,
                    {"type": "session.ended", "reason": "maximum_duration"},
                )
                await websocket.close(code=1000)
                break
            message = await asyncio.wait_for(
                websocket.receive(),
                timeout=min(
                    settings.voice_session_idle_timeout_seconds,
                    remaining_session,
                ),
            )
            session.last_activity_at = datetime.now(UTC)
            if message.get("type") == "websocket.disconnect":
                break
            raw_bytes = message.get("bytes")
            if raw_bytes is not None:
                if not initialized:
                    await send_error(
                        websocket, send_lock, "session_not_started", "Start the session first."
                    )
                    continue
                try:
                    validate_audio_frame(
                        raw_bytes,
                        format=session.input_format,
                        max_bytes=settings.voice_max_frame_bytes,
                    )
                    frame = AudioFrame(
                        data=raw_bytes,
                        sample_rate=session.input_sample_rate,
                        duration_ms=settings.voice_frame_duration_ms,
                    )
                    result = vad.analyze(frame)
                    if result.speech_started:
                        if settings.voice_allow_barge_in:
                            await interrupt()
                        buffer.start_speech()
                        session.speech_state = "speaking"
                        await send_json_safe(websocket, send_lock, {"type": "speech.started"})
                    if session.speech_state == "speaking":
                        buffer.append(raw_bytes, frame.duration_ms, speech=result.is_speech)
                    else:
                        buffer.add_pre_speech(raw_bytes)
                    if (
                        buffer.speech_ms >= settings.voice_min_speech_ms
                        and buffer.silence_ms >= settings.voice_end_silence_ms
                    ):
                        await commit()
                except VoiceProtocolError as error:
                    await send_error(
                        websocket, send_lock, error.code, error.safe_message, error.recoverable
                    )
                continue
            text = message.get("text")
            if text is None or len(text.encode()) > settings.voice_max_json_bytes:
                await send_error(
                    websocket, send_lock, "invalid_message", "Invalid control message."
                )
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                await send_error(websocket, send_lock, "malformed_json", "Malformed JSON message.")
                continue
            event_type = data.get("type")
            if event_type == "session.start":
                try:
                    start = SessionStart.model_validate(data)
                    if start.protocol_version != PROTOCOL_VERSION:
                        raise VoiceProtocolError(
                            "unsupported_protocol", "Unsupported protocol version."
                        )
                    if start.audio.format is not AudioFormat.PCM_S16LE:
                        raise VoiceProtocolError(
                            "invalid_audio_format", "Only PCM audio is supported."
                        )
                    if (
                        start.audio.sample_rate != settings.voice_input_sample_rate
                        or start.audio.channels != 1
                    ):
                        raise VoiceProtocolError(
                            "unsupported_audio", "Unsupported audio configuration."
                        )
                    if start.language:
                        session.language = service.resolve_language(start.language)
                except (ValidationError, VoiceProtocolError, VoiceServiceError) as error:
                    code = getattr(error, "code", "invalid_session_start")
                    safe = getattr(error, "safe_message", "Invalid session configuration.")
                    await send_error(websocket, send_lock, code, safe)
                    continue
                initialized = True
                session.status = SessionStatus.READY
                await send_json_safe(
                    websocket,
                    send_lock,
                    {
                        "type": "session.ready",
                        "session_id": session.session_id,
                        "conversation_id": session.conversation_id,
                        "protocol_version": PROTOCOL_VERSION,
                        "request_id": str(uuid.uuid4()),
                        "input_audio": {
                            "format": "pcm_s16le",
                            "sample_rate": session.input_sample_rate,
                            "channels": 1,
                        },
                        "output_audio": {
                            "format": "pcm_s16le",
                            "sample_rate": session.output_sample_rate,
                            "channels": 1,
                        },
                    },
                )
            elif event_type == "audio.commit":
                await commit()
            elif event_type == "assistant.interrupt":
                await interrupt()
            elif event_type == "conversation.reset":
                await service.reset_conversation(session.conversation_id)
                await send_json_safe(websocket, send_lock, {"type": "conversation.reset"})
            elif event_type == "ping":
                await send_json_safe(websocket, send_lock, {"type": "pong"})
            elif event_type == "session.end":
                if turn_task is not None:
                    await turn_task
                await send_json_safe(
                    websocket, send_lock, {"type": "session.ended", "reason": "client_request"}
                )
                await websocket.close(code=1000)
                break
            else:
                await send_error(
                    websocket, send_lock, "unsupported_event", "Unsupported event type."
                )
    except TimeoutError:
        reason = (
            "maximum_duration"
            if datetime.now(UTC) - session.connected_at
            >= timedelta(seconds=settings.voice_max_session_seconds)
            else "idle_timeout"
        )
        await send_json_safe(websocket, send_lock, {"type": "session.ended", "reason": reason})
        await websocket.close(code=1000)
    except WebSocketDisconnect:
        pass
    finally:
        if turn_task is not None and not turn_task.done():
            turn_task.cancel()
        await manager.remove(session.session_id)
        metrics.voice_sessions.labels("closed").inc()
        metrics.active_voice_sessions.dec()
