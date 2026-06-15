"""
Deterministic trace sanitization and safety guardrails.

No LLM calls. Regex-only PII/secret scrubbing and structural validation.
"""

from __future__ import annotations

import json
import re
from typing import Any

# --- Size limits ---
MAX_TRACE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_AGGREGATE_STRING_BYTES = 50 * 1024 * 1024  # 50 MB in-memory string budget
MAX_JSON_DEPTH = 50
MAX_STEPS = 5_000
MAX_STRING_LENGTH = 512_000

REDACTED = "[REDACTED_SECRET]"

# OpenAI-style API keys, Bearer tokens, common DB connection strings
SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(
        r"(?:postgres|postgresql|mysql|mongodb(?:\+srv)?)://[^\s\"']+",
        re.IGNORECASE,
    ),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"(?:api[_-]?key|secret|token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE),
]


class TraceSecurityError(ValueError):
    """Raised when a trace violates structural safety constraints."""


class TracePayloadTooLargeError(TraceSecurityError):
    """Raised when raw upload exceeds MAX_TRACE_BYTES."""


class TraceAggregateMemoryError(TraceSecurityError):
    """Raised when expanded in-memory string allocations exceed the aggregate limit."""


def enforce_size_limit(content: bytes) -> None:
    if len(content) > MAX_TRACE_BYTES:
        raise TracePayloadTooLargeError(
            f"Trace payload exceeds {MAX_TRACE_BYTES // (1024 * 1024)} MB limit "
            f"({len(content)} bytes)"
        )


def scrub_secrets(text: str) -> str:
    if not text:
        return text
    scrubbed = text
    for pattern in SECRET_PATTERNS:
        scrubbed = pattern.sub(REDACTED, scrubbed)
    return scrubbed


def _json_depth(value: Any, current: int = 0) -> int:
    if current > MAX_JSON_DEPTH:
        return current
    if isinstance(value, dict):
        if not value:
            return current + 1
        return max(_json_depth(v, current + 1) for v in value.values())
    if isinstance(value, list):
        if not value:
            return current + 1
        return max(_json_depth(item, current + 1) for item in value)
    return current + 1


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise TraceSecurityError(
                f"Trace string field exceeds {MAX_STRING_LENGTH} character limit"
            )
        return scrub_secrets(value)
    if isinstance(value, dict):
        return {k: _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    return value


def _aggregate_string_bytes(value: Any) -> int:
    """Sum UTF-8 byte lengths of all string leaves to bound JSON expansion attacks."""
    total = 0
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                total += len(key.encode("utf-8"))
            total += _aggregate_string_bytes(item)
        return total
    if isinstance(value, list):
        for item in value:
            total += _aggregate_string_bytes(item)
        return total
    return total


def validate_and_secure_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Unified ingest gate: serialized size cap, aggregate string budget,
    structural validation, and regex secret scrubbing.
    """
    if not isinstance(payload, dict):
        raise TraceSecurityError("Trace payload must be a JSON object")

    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    serialized_bytes = len(serialized.encode("utf-8"))
    if serialized_bytes > MAX_TRACE_BYTES:
        raise TracePayloadTooLargeError(
            f"Trace payload exceeds {MAX_TRACE_BYTES // (1024 * 1024)} MB limit "
            f"({serialized_bytes} bytes)"
        )

    aggregate_bytes = _aggregate_string_bytes(payload)
    if aggregate_bytes > MAX_AGGREGATE_STRING_BYTES:
        raise TraceAggregateMemoryError(
            f"Trace aggregate string memory ({aggregate_bytes} bytes) exceeds "
            f"{MAX_AGGREGATE_STRING_BYTES // (1024 * 1024)} MB limit"
        )

    return sanitize_trace_payload(payload)


def _count_steps(raw: dict[str, Any]) -> int:
    if isinstance(raw.get("steps"), list):
        return len(raw["steps"])
    if isinstance(raw.get("messages"), list):
        return len(raw["messages"])
    if isinstance(raw.get("tasks"), list):
        return len(raw["tasks"])
    if isinstance(raw.get("events"), list):
        return len(raw["events"])
    if isinstance(raw.get("runs"), list):
        return len(raw["runs"])
    return 0


def validate_trace_structure(raw: dict[str, Any]) -> None:
    if not isinstance(raw, dict):
        raise TraceSecurityError("Trace payload must be a JSON object")

    depth = _json_depth(raw)
    if depth > MAX_JSON_DEPTH:
        raise TraceSecurityError(
            f"Trace JSON nesting depth ({depth}) exceeds limit of {MAX_JSON_DEPTH}"
        )

    step_count = _count_steps(raw)
    if step_count > MAX_STEPS:
        raise TraceSecurityError(
            f"Trace step count ({step_count}) exceeds limit of {MAX_STEPS}"
        )


def sanitize_trace_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Validate structure, scrub secrets from all string fields, return safe copy.
    Called at the entry point of analysis before parsing.
    """
    validate_trace_structure(raw)
    return _scrub_value(raw)


def sanitize_raw_json_bytes(content: bytes) -> dict[str, Any]:
    """Full ingest pipeline: raw byte cap → parse → unified security gate."""
    enforce_size_limit(content)
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as e:
        raise TraceSecurityError(f"Invalid JSON: {e}") from e

    return validate_and_secure_payload(raw)
