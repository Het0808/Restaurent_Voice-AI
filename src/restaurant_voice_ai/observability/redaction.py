"""Central safe text redaction."""

import re
from urllib.parse import urlsplit, urlunsplit

PHONE = re.compile(r"(?<!\w)\+?\d[\d ()-]{6,}\d")


def mask_phone_numbers(value: str) -> str:
    return PHONE.sub(lambda match: "***" + re.sub(r"\D", "", match.group())[-4:], value)


def redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "[redacted]"
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return urlunsplit((parsed.scheme, host + port, parsed.path, "", ""))


def redact(value: object) -> object:
    if isinstance(value, str):
        lowered = value.casefold()
        if any(marker in lowered for marker in ("api_key=", "x-api-key", "authorization:")):
            return "[redacted]"
        return mask_phone_numbers(value)
    return value
