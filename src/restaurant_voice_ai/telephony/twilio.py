"""Bounded Twilio webhook validation and TwiML generation."""

from collections.abc import Mapping
from dataclasses import dataclass
from html import escape

from twilio.request_validator import RequestValidator  # type: ignore[import-untyped]

from restaurant_voice_ai.core.config import Settings


class InvalidTwilioSignature(ValueError):
    """Raised when a webhook cannot be authenticated."""


def public_webhook_url(settings: Settings, path: str) -> str:
    if not settings.public_base_url:
        raise RuntimeError("PUBLIC_BASE_URL is not configured")
    return f"{settings.public_base_url.rstrip('/')}{path}"


def validate_signature(
    settings: Settings, url: str, form: Mapping[str, str], signature: str | None
) -> None:
    if not settings.twilio_validate_signatures and settings.app_env in {"development", "test"}:
        return
    if settings.twilio_auth_token is None or not signature:
        raise InvalidTwilioSignature("Twilio webhook signature is missing or invalid")
    validator = RequestValidator(settings.twilio_auth_token.get_secret_value())
    if not validator.validate(url, dict(form), signature):
        raise InvalidTwilioSignature("Twilio webhook signature is missing or invalid")


@dataclass(frozen=True, slots=True)
class TwimlBuilder:
    settings: Settings

    def gather(self, prompt: str) -> str:
        action = public_webhook_url(self.settings, "/api/v1/voice/process-speech")
        status = public_webhook_url(self.settings, "/api/v1/voice/status")
        speech_timeout = escape(self.settings.twilio_speech_timeout)
        language = escape(self.settings.twilio_voice_language)
        voice = escape(self.settings.twilio_voice_name)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response><Gather input="speech" method="POST" action="'
            f'{escape(action, quote=True)}" speechTimeout="{speech_timeout}" '
            f'timeout="5" actionOnEmptyResult="true" language="{language}">'
            f'<Say voice="{voice}" language="{language}">{escape(prompt)}</Say>'
            f'</Gather><Redirect method="POST">{escape(status)}</Redirect></Response>'
        )

    def hangup(self, prompt: str) -> str:
        return self._response(f"{self._say(prompt)}<Hangup/>")

    def transfer(self, prompt: str) -> str:
        if not self.settings.twilio_staff_phone_number:
            return self.hangup("Sorry, a staff member is unavailable. Please call again shortly.")
        dial = escape(self.settings.twilio_staff_phone_number)
        return self._response(f"{self._say(prompt)}<Dial>{dial}</Dial>")

    def _say(self, prompt: str) -> str:
        return (
            f'<Say voice="{escape(self.settings.twilio_voice_name)}" '
            f'language="{escape(self.settings.twilio_voice_language)}">{escape(prompt)}</Say>'
        )

    @staticmethod
    def _response(body: str) -> str:
        return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'
