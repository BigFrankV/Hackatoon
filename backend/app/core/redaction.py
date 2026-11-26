from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_SENSITIVE_PARTS = (
    "password",
    "token",
    "secret",
    "ticket",
    "apikey",
    "authorization",
    "cookie",
    "credential",
)
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+\S+")


def _is_sensitive_key(key: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return any(part in normalized for part in _SENSITIVE_PARTS)


def _redact_url(value: str) -> str:
    if not value.startswith(("http://", "https://")):
        return _BEARER_PATTERN.sub("Bearer [REDACTED]", value)

    parts = urlsplit(value)
    query = [
        (key, "[REDACTED]" if _is_sensitive_key(key) else item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
    ]
    host = parts.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, urlencode(query), parts.fragment))


def redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _is_sensitive_key(key) else redact_secrets(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    if isinstance(value, str):
        return _redact_url(value)
    return value
