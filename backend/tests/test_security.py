import json

import pytest
from fastapi import HTTPException

from app.services.analysis_service import AnalysisService
from app.services.demo_data import get_chaotic_trace, get_excellent_trace
from app.utils.security import (
    REDACTED,
    TracePayloadTooLargeError,
    TraceSecurityError,
    enforce_size_limit,
    sanitize_trace_payload,
    scrub_secrets,
)


@pytest.fixture
def service() -> AnalysisService:
    return AnalysisService()


def test_scrub_openai_api_key():
    raw_key = "sk-1234567890abcdef1234567890abcdef1234567890abcdef"
    assert REDACTED in scrub_secrets(f"Authorization: {raw_key}")
    assert raw_key not in scrub_secrets(f"Authorization: {raw_key}")


def test_scrub_bearer_token():
    token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
    scrubbed = scrub_secrets(f"Header {token}")
    assert REDACTED in scrubbed
    assert "eyJhbGci" not in scrubbed


def test_scrub_database_connection_string():
    conn = "postgresql://admin:secret@db.internal:5432/prod"
    scrubbed = scrub_secrets(conn)
    assert REDACTED in scrubbed
    assert "postgresql://" not in scrubbed


def test_sanitize_trace_payload_redacts_nested_secrets():
    trace = {
        "metadata": {"run_id": "secret-run"},
        "steps": [
            {
                "index": 0,
                "type": "thought",
                "content": "key=sk-1234567890abcdef1234567890abcdef1234567890abcdef",
            }
        ],
    }
    sanitized = sanitize_trace_payload(trace)
    assert REDACTED in sanitized["steps"][0]["content"]
    assert "sk-1234567890abcdef" not in sanitized["steps"][0]["content"]


def test_analyze_raw_scrubs_before_parsing(service):
    trace = {
        "metadata": {"run_id": "redact-test", "framework": "generic", "status": "success"},
        "steps": [
            {
                "index": 0,
                "type": "thought",
                "content": "token sk-1234567890abcdef1234567890abcdef1234567890abcdef leaked",
            },
            {
                "index": 1,
                "type": "thought",
                "content": "done",
            },
        ],
    }
    report = service.analyze_raw(trace)
    assert report.metadata["run_id"] == "redact-test"
    sanitized = sanitize_trace_payload(trace)
    assert REDACTED in sanitized["steps"][0]["content"]
    assert "sk-1234567890abcdef" not in sanitized["steps"][0]["content"]


def test_enforce_size_limit_raises_413():
    oversized = b"x" * (5 * 1024 * 1024 + 1)
    with pytest.raises(TracePayloadTooLargeError):
        enforce_size_limit(oversized)


def test_excessive_json_depth_rejected():
    nested: dict = {"steps": [{"index": 0, "type": "thought", "content": "ok"}]}
    current = nested
    for _ in range(60):
        child = {"steps": [{"index": 0, "type": "thought", "content": "deep"}]}
        current["child"] = child
        current = child

    with pytest.raises(TraceSecurityError, match="nesting depth"):
        sanitize_trace_payload(nested)


def test_excessive_step_count_rejected():
    trace = {
        "steps": [{"index": i, "type": "thought", "content": "x"} for i in range(5001)],
    }
    with pytest.raises(TraceSecurityError, match="step count"):
        sanitize_trace_payload(trace)


def test_analysis_service_maps_security_errors_to_http(service):
    trace = {
        "steps": [{"index": i, "type": "thought", "content": "x"} for i in range(5001)],
    }
    with pytest.raises(HTTPException) as exc:
        service.analyze_raw(trace)
    assert exc.value.status_code == 400


def test_excellent_demo_trace_is_healthy(service):
    report = service.analyze_raw(get_excellent_trace())
    assert report.metadata["status"] == "success"
    assert report.health.score >= 85
    assert report.cost_analysis.total_cost_usd < 0.01
    assert len(report.loops) == 0


def test_chaotic_demo_trace_meets_playbook_contract(service):
    report = service.analyze_raw(get_chaotic_trace())
    assert report.metadata["status"] == "failure"
    assert len(report.loops) >= 1
    assert report.redundancy.redundancy_score >= 80.0
    assert report.cost_analysis.total_cost_usd > 0.05
    assert report.causal_analysis.root_cause_node is not None
    assert len(report.causal_analysis.node_metrics) >= 3
