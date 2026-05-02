"""
Security primitives: input sanitisation and log scrubbing.

Scope (explicit non-goals)
--------------------------
This module is NOT responsible for authentication, session tokens, or
transport-level security. Those live in ``core/`` and ``routes/user``.

What lives here:
  * ``sanitize_text`` — strip HTML / dangerous control characters from user
    free-text before it hits a downstream LLM prompt or database record.
  * ``sanitize_prompt`` — tighter variant for LLM prompts: collapses repeated
    punctuation that some models treat as jailbreak seeds, caps length.
  * ``scrub_log_record`` — redacts API keys / bearer tokens / emails from
    arbitrary log values so structlog output never leaks secrets.

All helpers are pure functions (no I/O) to keep them hot-path friendly.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping

# Keys (case-insensitive contains match) whose values should never appear in
# logs. Covers common third-party naming patterns.
_SENSITIVE_KEY_PATTERNS = (
    "password", "passwd", "pwd",
    "secret", "token", "apikey", "api_key",
    "authorization", "auth",
    "cookie", "session",
    "private_key", "privatekey",
)

# Redaction mask — short but recognisable in logs.
_MASK = "***redacted***"

# Email regex — deliberately permissive (RFC-compliant regex is a PITA and we
# only need "looks like an email").
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Bearer / JWT-ish tokens in free-text log lines.
_BEARER_RE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE)
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")

# HTML-ish tags. We opt for a deny-all strip rather than a sanitising parser
# because downstream consumers (LLMs, journals) don't need markup.
_HTML_RE = re.compile(r"<[^>]+>")

# Control characters except common whitespace (\t \n \r).
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_text(text: Any, *, max_length: int = 4000) -> str:
    """Return a cleaned string safe to persist or echo back to the user.

    * Coerces ``None`` / non-strings to empty string / ``str(x)`` respectively.
    * Strips HTML tags and control chars.
    * Trims to ``max_length`` so an attacker cannot wedge enormous blobs into
      a database column via an unvalidated field.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    cleaned = _HTML_RE.sub("", text)
    cleaned = _CTRL_RE.sub("", cleaned)
    cleaned = cleaned.strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def sanitize_prompt(text: Any, *, max_length: int = 2000) -> str:
    """Stricter variant intended for LLM prompt construction.

    Collapses runs of 4+ identical punctuation chars (``!!!!!`` / ``????``) to
    a single occurrence. Some OSS models exhibit prompt-injection-like
    behaviour when fed such sequences. We also kill NUL bytes defensively.
    """
    cleaned = sanitize_text(text, max_length=max_length)
    cleaned = re.sub(r"([!?.]){4,}", r"\1", cleaned)
    cleaned = cleaned.replace("\x00", "")
    return cleaned


def _looks_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(p in lowered for p in _SENSITIVE_KEY_PATTERNS)


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        v = _BEARER_RE.sub(f"Bearer {_MASK}", value)
        v = _JWT_RE.sub(_MASK, v)
        v = _EMAIL_RE.sub(_MASK, v)
        return v
    return value


def scrub_log_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``record`` with sensitive keys / patterns redacted.

    Suitable for use as a structlog processor — or call manually before logging
    user-supplied payloads::

        logger.info("request_received", **scrub_log_record(body))
    """
    out: Dict[str, Any] = {}
    for key, value in record.items():
        if _looks_sensitive_key(str(key)):
            out[key] = _MASK
            continue
        if isinstance(value, Mapping):
            out[key] = scrub_log_record(value)
        elif isinstance(value, (list, tuple)):
            out[key] = [
                scrub_log_record(v) if isinstance(v, Mapping) else _scrub_value(v)
                for v in value
            ]
        else:
            out[key] = _scrub_value(value)
    return out


def structlog_scrubber(_logger: Any, _method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """structlog processor form of ``scrub_log_record``."""
    return scrub_log_record(event_dict)
