"""Simple redaction helpers for logs and diagnostics."""

from __future__ import annotations

import re

_URL_USERINFO_RE = re.compile(r"([a-z][a-z0-9+.-]*://)([^@/]+)@", re.IGNORECASE)
_QUERY_SECRET_RE = re.compile(
    r"(?i)(token|secret|password|api_key|apikey|access_token|refresh_token)=([^&\s]+)"
)
_BEARER_RE = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._~-]+)")


def redact_secrets(text: str) -> str:
    """Redact common secret patterns from a log string."""
    if not text:
        return text
    redacted = _URL_USERINFO_RE.sub(r"\1***@", text)
    redacted = _QUERY_SECRET_RE.sub(r"\1=***", redacted)
    redacted = _BEARER_RE.sub(r"\1***", redacted)
    return redacted
