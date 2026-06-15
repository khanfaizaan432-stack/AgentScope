"""Tests for the unified security ingest gate on API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.utils.security import MAX_TRACE_BYTES


def _minimal_compare_payload(extra: dict | None = None) -> dict:
    base = {
        "steps": [{"index": 0, "type": "thought", "content": "ok"}],
        "metadata": {"run_id": "gate-test", "status": "success"},
    }
    if extra:
        base.update(extra)
    return base


def test_compare_rejects_oversized_serialized_payload() -> None:
    """Serialized JSON over 5 MB must be rejected before analysis."""
    huge_content = "x" * (MAX_TRACE_BYTES + 1)
    client = TestClient(app)
    response = client.post(
        "/api/v1/compare",
        json={
            "run_a": _minimal_compare_payload({"steps": [{"index": 0, "type": "thought", "content": huge_content}]}),
            "run_b": _minimal_compare_payload(),
        },
    )
    assert response.status_code in (400, 413)


def test_compare_rejects_nested_json_expansion_attack() -> None:
    """Deeply nested payloads with large string leaves must be rejected at the ingest gate."""
    chunk = "A" * (512 * 1024)
    nested: dict = _minimal_compare_payload()
    current = nested
    for _ in range(12):
        child = {"steps": [{"index": 0, "type": "thought", "content": chunk}]}
        current["nested"] = child
        current = child

    client = TestClient(app)
    response = client.post(
        "/api/v1/compare",
        json={"run_a": nested, "run_b": _minimal_compare_payload()},
    )
    assert response.status_code in (400, 413)


def test_analyze_json_rejects_oversized_payload() -> None:
    huge_content = "x" * (MAX_TRACE_BYTES + 1)
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze/json",
        json=_minimal_compare_payload({"steps": [{"index": 0, "type": "thought", "content": huge_content}]}),
    )
    assert response.status_code in (400, 413)
