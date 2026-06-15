from __future__ import annotations

from app.services.analysis_service import AnalysisService


def test_success_trace_has_empty_causal_analysis() -> None:
    raw = {
        "metadata": {"run_id": "causal-ok", "framework": "generic", "status": "success"},
        "steps": [{"index": 0, "type": "thought", "content": "hello", "node_name": "Planner"}],
    }

    report = AnalysisService().analyze_raw(raw)
    causal = report.causal_analysis
    assert causal.root_cause_node is None
    assert causal.failure_path == []


def test_terminal_tool_exception_maps_backward_sequence() -> None:
    # Use LangGraph minimal export so we have deterministic node transitions.
    raw = {
        "metadata": {"run_id": "causal-ex", "framework": "langgraph", "status": "failure"},
        "events": [
            {"type": "state_transition", "from": "__start__", "to": "Planner"},
            {"type": "state_transition", "from": "Planner", "to": "ToolNode"},
            {"type": "tool_start", "tool_name": "DoThing", "arguments": {}, "node": "ToolNode"},
            {"type": "tool_end", "tool_name": "DoThing", "output": {"error": "Boom"}, "node": "ToolNode"},
        ],
    }

    report = AnalysisService().analyze_raw(raw)
    causal = report.causal_analysis
    assert causal.failure_path[-1] == "ToolNode"
    assert causal.root_cause_node == "ToolNode"
    assert "ToolNode" in causal.node_metrics


def test_validation_failure_shifts_blame_to_previous_empty_payload_node() -> None:
    raw = {
        "metadata": {"run_id": "causal-val", "framework": "langgraph", "status": "failure"},
        "events": [
            {"type": "state_transition", "from": "__start__", "to": "Fetcher"},
            {"type": "tool_start", "tool_name": "Fetch", "arguments": {}, "node": "Fetcher"},
            {"type": "tool_end", "tool_name": "Fetch", "output": {}, "node": "Fetcher"},
            {"type": "state_transition", "from": "Fetcher", "to": "Validator"},
            {"type": "tool_start", "tool_name": "Validate", "arguments": {}, "node": "Validator"},
            {"type": "tool_end", "tool_name": "Validate", "output": {"error": "ValidationError: missing field"}, "node": "Validator"},
        ],
    }

    report = AnalysisService().analyze_raw(raw)
    causal = report.causal_analysis
    assert causal.root_cause_node == "Fetcher"
    assert causal.failure_path[-1] == "Validator"

