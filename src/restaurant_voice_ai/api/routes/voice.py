"""Browser-compatible real-time voice WebSocket route."""

from importlib.util import find_spec
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from restaurant_voice_ai.auth.dependencies import require_permission
from restaurant_voice_ai.auth.models import AuthIdentity, Permission
from restaurant_voice_ai.auth.websocket import authenticate_websocket
from restaurant_voice_ai.conversation.dependencies import build_conversation_dependencies
from restaurant_voice_ai.conversation.service import ConversationService
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.db.dependencies import get_db_session
from restaurant_voice_ai.db.services.call_session_service import CallSessionService
from restaurant_voice_ai.observability.metrics import metrics
from restaurant_voice_ai.persistence.redis.factory import (
    get_conversation_memory,
    get_idempotency_store,
)
from restaurant_voice_ai.rag.dependencies import get_rag_service
from restaurant_voice_ai.telephony.twilio import (
    InvalidTwilioSignature,
    TwimlBuilder,
    public_webhook_url,
    validate_signature,
)
from restaurant_voice_ai.voice.dependencies import build_voice_service, get_session_manager
from restaurant_voice_ai.voice.websocket import handle_voice_websocket

router = APIRouter(prefix="/voice", tags=["Voice"])


async def _twilio_form(request: Request, settings: Settings, path: str) -> dict[str, str]:
    form = {key: str(value) for key, value in (await request.form()).items()}
    if (
        sum(len(key) + len(value) for key, value in form.items())
        > settings.twilio_webhook_max_chars
    ):
        raise HTTPException(status_code=413, detail="Webhook payload is too large")
    try:
        validate_signature(
            settings,
            public_webhook_url(settings, path),
            form,
            request.headers.get("X-Twilio-Signature"),
        )
    except (InvalidTwilioSignature, RuntimeError) as exc:
        raise HTTPException(status_code=403, detail="Invalid Twilio webhook signature") from exc
    return form


def _required(form: dict[str, str], key: str, max_length: int = 128) -> str:
    value = form.get(key, "").strip()
    if not value or len(value) > max_length:
        raise HTTPException(status_code=422, detail=f"Invalid {key}")
    return value


async def _conversation_for_twilio(
    request: Request, settings: Settings, session: AsyncSession
) -> ConversationService:
    override = getattr(request.app.state, "twilio_conversation_factory", None)
    if override is not None:
        return cast(ConversationService, override())
    return ConversationService(
        build_conversation_dependencies(
            settings,
            session,
            get_rag_service(request),
            get_conversation_memory(request),
            get_idempotency_store(request),
        )
    )


@router.post("/incoming", response_class=Response)
async def incoming_call(
    request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> Response:
    settings: Settings = request.app.state.settings
    form = await _twilio_form(request, settings, "/api/v1/voice/incoming")
    call_sid = _required(form, "CallSid")
    await CallSessionService(session).get_or_create(
        call_sid,
        form.get("From"),
        form.get("To"),
        form.get("Direction"),
        form.get("CallStatus", "in-progress"),
    )
    metrics.telephony_calls.labels(event="incoming").inc()
    prompt = "Welcome. I can help with restaurant information or reservations. How may I help?"
    return Response(TwimlBuilder(settings).gather(prompt), media_type="application/xml")


@router.post("/process-speech", response_class=Response)
async def process_twilio_speech(
    request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> Response:
    settings: Settings = request.app.state.settings
    form = await _twilio_form(request, settings, "/api/v1/voice/process-speech")
    call_sid = _required(form, "CallSid")
    calls = CallSessionService(session)
    call = await calls.get(call_sid)
    if call is None:
        raise HTTPException(status_code=404, detail="Call session not found")
    memory = get_conversation_memory(request)
    conversation_id = f"twilio-{call_sid}"[:64]
    snapshot = await memory.load(conversation_id)
    retries = int(snapshot.metadata.get("telephony_retry_count", 0)) if snapshot else 0
    speech = form.get("SpeechResult", "").strip()[: settings.voice_max_transcript_chars]
    try:
        confidence = float(form.get("Confidence", "0") or 0)
    except ValueError:
        confidence = 0
    builder = TwimlBuilder(settings)
    if not speech or confidence < settings.twilio_min_speech_confidence:
        metrics.telephony_speech.labels(outcome="retry").inc()
        retries += 1
        if snapshot is None:
            from restaurant_voice_ai.conversation.memory.models import ConversationSnapshot

            snapshot = ConversationSnapshot(conversation_id=conversation_id)
        snapshot.metadata["telephony_retry_count"] = retries
        await memory.save(snapshot)
        if retries >= settings.twilio_max_retries:
            await calls.mark_escalated(call_sid, "repeated_silence_or_low_confidence")
            metrics.telephony_escalations.labels(reason="low_confidence").inc()
            return Response(
                builder.transfer(
                    "Sorry, I am having trouble hearing you. Let me connect you to staff."
                ),
                media_type="application/xml",
            )
        prompt = (
            "Sorry, I didn't catch that. Could you repeat it?"
            if retries == 1
            else "Please say restaurant information, a reservation, or staff help."
        )
        return Response(builder.gather(prompt), media_type="application/xml")
    lowered = speech.casefold()
    if any(term in lowered for term in ("human", "staff member", "manager", "real person")):
        await calls.mark_escalated(call_sid, "caller_requested_human")
        metrics.telephony_escalations.labels(reason="caller_request").inc()
        return Response(
            builder.transfer("Certainly. I will connect you to a staff member."),
            media_type="application/xml",
        )
    if any(term in lowered for term in ("goodbye", "hang up", "end call")):
        return Response(
            builder.hangup("Thank you for calling. Goodbye."), media_type="application/xml"
        )
    try:
        conversation = await _conversation_for_twilio(request, settings, session)
        result = await conversation.process_message(
            speech,
            "en",
            conversation_id=conversation_id,
            metadata={"channel": "twilio", "call_sid": call_sid, "language": "en"},
        )
        metrics.telephony_speech.labels(outcome="processed").inc()
        prompt = result.response_text[:600] or "How else may I help?"
        if snapshot := await memory.load(conversation_id):
            snapshot.metadata["telephony_retry_count"] = 0
            await memory.save(snapshot)
        return Response(builder.gather(prompt), media_type="application/xml")
    except Exception as exc:
        await calls.update_status(call_sid, "failed", error=type(exc).__name__)
        return Response(
            builder.transfer(
                "Sorry, I cannot complete that right now. Let me connect you to staff."
            ),
            media_type="application/xml",
        )


@router.post("/status", response_class=Response)
async def twilio_status_callback(
    request: Request, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> Response:
    settings: Settings = request.app.state.settings
    form = await _twilio_form(request, settings, "/api/v1/voice/status")
    call_sid = _required(form, "CallSid")
    status_value = _required(form, "CallStatus", 24)
    allowed = {
        "queued",
        "ringing",
        "in-progress",
        "completed",
        "busy",
        "failed",
        "no-answer",
        "canceled",
    }
    if status_value not in allowed:
        raise HTTPException(status_code=422, detail="Invalid CallStatus")
    duration: int | None = None
    if form.get("CallDuration"):
        try:
            duration = max(0, int(form["CallDuration"]))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid CallDuration") from exc
    service = CallSessionService(session)
    call = await service.get(call_sid)
    if call is None:
        call = await service.get_or_create(
            call_sid,
            form.get("From"),
            form.get("To"),
            form.get("Direction"),
            status_value,
        )
    await service.update_status(
        call_sid, status_value, duration=duration, error=form.get("ErrorMessage")
    )
    metrics.telephony_calls.labels(event=status_value).inc()
    return Response(status_code=204)


@router.get("/status")
async def voice_status(
    request: Request,
    _: Annotated[AuthIdentity, Depends(require_permission(Permission.VIEW_ADMIN_HEALTH))],
) -> dict[str, object]:
    settings: Settings = request.app.state.settings
    manager = get_session_manager(
        settings.voice_max_sessions,
        settings.voice_session_idle_timeout_seconds,
        settings.voice_max_session_seconds,
    )
    return {
        "enabled": settings.voice_enabled,
        "stt_provider": settings.voice_stt_provider,
        "tts_provider": settings.voice_tts_provider,
        "google_speech_installed": find_spec("google.cloud.speech_v1") is not None,
        "google_tts_installed": find_spec("google.cloud.texttospeech") is not None,
        "active_sessions": await manager.active_count(),
    }


@router.websocket("/ws")
async def voice_websocket(
    websocket: WebSocket,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    conversation_id: Annotated[str | None, Query(min_length=8, max_length=64)] = None,
    language: Annotated[str | None, Query()] = None,
) -> None:
    settings: Settings = websocket.app.state.settings
    identity = authenticate_websocket(websocket, Permission.OPEN_VOICE_SESSION)
    if identity is None:
        await websocket.close(code=1008, reason="Authentication required")
        return
    if settings.rate_limit_enabled:
        result = await websocket.app.state.rate_limiter.check(
            f"voice:{identity.fingerprint}",
            settings.rate_limit_voice_connections_per_minute,
            60,
        )
        if not result.allowed:
            await websocket.close(code=1008, reason="Rate limit exceeded")
            return
    override = getattr(websocket.app.state, "voice_service_factory", None)
    if override is not None:
        service = override()
    else:
        rag_service = get_rag_service(websocket)
        conversation = ConversationService(
            build_conversation_dependencies(
                settings,
                session,
                rag_service,
                get_conversation_memory(websocket),
                get_idempotency_store(websocket),
            )
        )
        service = build_voice_service(settings, conversation)
    manager = get_session_manager(
        settings.voice_max_sessions,
        settings.voice_session_idle_timeout_seconds,
        settings.voice_max_session_seconds,
    )
    await handle_voice_websocket(
        websocket,
        settings,
        service,
        manager,
        conversation_id=conversation_id,
        requested_language=language,
        auth_identity=identity.fingerprint,
    )
