from __future__ import annotations

from app.services.analysis_service import AnalysisService


def test_executive_summary_present_on_minimal_success_trace() -> None:
    raw = {
        "metadata": {"run_id": "sum-ok", "framework": "generic", "status": "success"},
        "steps": [{"index": 0, "type": "thought", "content": "hello"}],
    }

    service = AnalysisService()
    report = service.analyze_raw(raw)

    assert report.executive_summary.overview == "Agent executed 1 steps across 0 tools."
    assert report.executive_summary.health_verdict == "Excellent"
    assert isinstance(report.executive_summary.key_findings, list)
    assert isinstance(report.executive_summary.priority_actions, list)


def test_executive_summary_verdict_critical_with_hallucination_loop_redundancy() -> None:
    raw = {
        "metadata": {"run_id": "sum-bad", "framework": "generic", "status": "success"},
        "available_tools": [{"name": "Allowed", "description": "ok"}],
        "steps": [
            {"index": 0, "type": "tool_call", "tool_name": "NotAllowed", "tool_input": {}},
            {"index": 1, "type": "tool_call", "tool_name": "NotAllowed", "tool_input": {}},
            {"index": 2, "type": "tool_call", "tool_name": "NotAllowed", "tool_input": {}},
            {"index": 3, "type": "thought", "content": "repeat"},
            {"index": 4, "type": "thought", "content": "repeat"},
        ],
    }

    service = AnalysisService()
    report = service.analyze_raw(raw)

    summary = report.executive_summary
    assert summary.health_verdict == "Critical"
    assert any("hallucinated tool" in f.lower() for f in summary.key_findings)
    assert any("tool loop" in f.lower() or "loop pattern" in f.lower() for f in summary.key_findings)
    assert any("redundancy reached" in f.lower() for f in summary.key_findings)
    assert len(summary.priority_actions) > 0


def test_executive_summary_verdict_good_for_single_hallucination() -> None:
    raw = {
        "metadata": {"run_id": "sum-good", "framework": "generic", "status": "success"},
        "available_tools": [{"name": "Allowed", "description": "ok"}],
        "steps": [
            {"index": 0, "type": "tool_call", "tool_name": "NotAllowed", "tool_input": {}},
            {"index": 1, "type": "thought", "content": "ok"},
        ],
    }
    report = AnalysisService().analyze_raw(raw)
    assert report.executive_summary.health_verdict == "Good"


def test_executive_summary_verdict_fair_for_two_hallucinations() -> None:
    raw = {
        "metadata": {"run_id": "sum-fair", "framework": "generic", "status": "success"},
        "available_tools": [{"name": "Allowed", "description": "ok"}],
        "steps": [
            {"index": 0, "type": "tool_call", "tool_name": "NotAllowedA", "tool_input": {}},
            {"index": 1, "type": "tool_call", "tool_name": "NotAllowedB", "tool_input": {}},
        ],
    }
    report = AnalysisService().analyze_raw(raw)
    assert report.executive_summary.health_verdict == "Fair"


def test_executive_summary_verdict_poor_for_three_hallucinations_without_loop() -> None:
    # Use three distinct tool names to avoid triggering the consecutive-loop detector.
    raw = {
        "metadata": {"run_id": "sum-poor", "framework": "generic", "status": "success"},
        "available_tools": [{"name": "Allowed", "description": "ok"}],
        "steps": [
            {"index": 0, "type": "tool_call", "tool_name": "NotAllowedA", "tool_input": {}},
            {"index": 1, "type": "tool_call", "tool_name": "NotAllowedB", "tool_input": {}},
            {"index": 2, "type": "tool_call", "tool_name": "NotAllowedC", "tool_input": {}},
        ],
    }
    report = AnalysisService().analyze_raw(raw)
    assert report.executive_summary.health_verdict == "Poor"


def test_executive_summary_verdict_critical_when_cost_pushes_points_over_threshold() -> None:
    # 3 hallucinations = 9 points; cost > $0.05 adds +1 => 10 (Critical)
    raw = {
        "metadata": {"run_id": "sum-critical-cost", "framework": "generic", "status": "success"},
        "available_tools": [{"name": "Allowed", "description": "ok"}],
        "steps": [
            {"index": 0, "type": "tool_call", "tool_name": "NotAllowedA", "tool_input": {}, "cost_usd": 0.06},
            {"index": 1, "type": "tool_call", "tool_name": "NotAllowedB", "tool_input": {}},
            {"index": 2, "type": "tool_call", "tool_name": "NotAllowedC", "tool_input": {}},
        ],
    }
    report = AnalysisService().analyze_raw(raw)
    assert report.executive_summary.health_verdict == "Critical"


def test_executive_summary_verdict_good_for_failure_status() -> None:
    raw = {
        "metadata": {"run_id": "sum-fail", "framework": "generic", "status": "failure"},
        "steps": [{"index": 0, "type": "thought", "content": "oops"}],
    }
    report = AnalysisService().analyze_raw(raw)
    assert report.executive_summary.health_verdict == "Good"
