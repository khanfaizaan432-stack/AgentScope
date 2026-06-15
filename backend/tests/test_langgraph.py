from __future__ import annotations

from app.parsers import detect_and_parse
from app.services.analysis_service import AnalysisService


def test_langgraph_autodetect_events() -> None:
    raw = {
        "events": [
            {"type": "state_transition", "from": "Planner", "to": "Search"},
            {"type": "state_transition", "from": "Search", "to": "Planner"},
            {"type": "state_transition", "from": "Planner", "to": "Search"},
            {"type": "state_transition", "from": "Search", "to": "Planner"},
            {"type": "tool_call", "name": "Search", "arguments": {"q": "hello"}},
            {"type": "tool_result", "name": "Search", "content": "ok"},
        ],
        "metadata": {"run_id": "lg-1", "status": "success"},
    }

    trace = detect_and_parse(raw)
    assert trace.metadata.framework == "langgraph"
    assert len(trace.state_transitions) >= 4


def test_langgraph_state_loop_detection_abab() -> None:
    raw = {
        "events": [
            {"type": "state_transition", "from": "Planner", "to": "Search"},
            {"type": "state_transition", "from": "Search", "to": "Planner"},
            {"type": "state_transition", "from": "Planner", "to": "Search"},
            {"type": "state_transition", "from": "Search", "to": "Planner"},
        ],
        "metadata": {"run_id": "lg-loop", "status": "success"},
    }

    service = AnalysisService()
    report = service.analyze_raw(raw)
    assert report.langgraph_analysis is not None
    assert len(report.langgraph_analysis.state_loops) >= 1
    loop = report.langgraph_analysis.state_loops[0]
    assert loop.cycle_length == 2
    assert loop.repetitions >= 2
    assert "Planner" in loop.repeated_states
    assert "Search" in loop.repeated_states


def test_langgraph_branch_analysis_summary_present() -> None:
    raw = {
        "metadata": {"run_id": "lg-branch", "status": "success"},
        "messages": [{"role": "assistant", "content": "hello"}],
        "node_transitions": [
            {"from": "A", "to": "B"},
            {"from": "B", "to": "C"},
            {"from": "B", "to": "D"},
            {"from": "D", "to": "E"},
        ],
    }

    service = AnalysisService()
    report = service.analyze_raw(raw)
    assert report.langgraph_analysis is not None
    assert report.langgraph_analysis.branches is not None
    assert "branches explored" in report.langgraph_analysis.branches.summary


def test_langsmith_export_runs_autodetect_and_parse() -> None:
    raw = {
        "runs": [
            {
                "id": "root",
                "trace_id": "root",
                "name": "graph",
                "run_type": "chain",
                "start_time": "2024-04-29T00:00:00.000000",
                "end_time": "2024-04-29T00:00:10.000000",
                "dotted_order": "20240429T000000000000Zroot",
                "status": "success",
            },
            {
                "id": "n1",
                "trace_id": "root",
                "parent_run_id": "root",
                "name": "Planner",
                "run_type": "chain",
                "start_time": "2024-04-29T00:00:01.000000",
                "end_time": "2024-04-29T00:00:02.000000",
                "dotted_order": "20240429T000000000000Zroot.20240429T000001000000Zn1",
                "status": "success",
            },
            {
                "id": "n2",
                "trace_id": "root",
                "parent_run_id": "root",
                "name": "Search",
                "run_type": "chain",
                "start_time": "2024-04-29T00:00:02.000000",
                "end_time": "2024-04-29T00:00:03.000000",
                "dotted_order": "20240429T000000000000Zroot.20240429T000002000000Zn2",
                "status": "success",
            },
            {
                "id": "n3",
                "trace_id": "root",
                "parent_run_id": "root",
                "name": "Planner",
                "run_type": "chain",
                "start_time": "2024-04-29T00:00:03.000000",
                "end_time": "2024-04-29T00:00:04.000000",
                "dotted_order": "20240429T000000000000Zroot.20240429T000003000000Zn3",
                "status": "success",
            },
            {
                "id": "n4",
                "trace_id": "root",
                "parent_run_id": "root",
                "name": "Search",
                "run_type": "chain",
                "start_time": "2024-04-29T00:00:04.000000",
                "end_time": "2024-04-29T00:00:05.000000",
                "dotted_order": "20240429T000000000000Zroot.20240429T000004000000Zn4",
                "status": "success",
            },
            {
                "id": "llm1",
                "trace_id": "root",
                "parent_run_id": "n1",
                "name": "llm",
                "run_type": "llm",
                "start_time": "2024-04-29T00:00:01.100000",
                "end_time": "2024-04-29T00:00:01.200000",
                "dotted_order": "20240429T000000000000Zroot.20240429T000001000000Zn1.20240429T000001100000Zllm1",
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_cost": 0.0001,
                "outputs": {"messages": [{"role": "assistant", "content": "Plan next step."}]},
                "status": "success",
            },
            {
                "id": "tool1",
                "trace_id": "root",
                "parent_run_id": "n2",
                "name": "Search",
                "run_type": "tool",
                "start_time": "2024-04-29T00:00:02.100000",
                "end_time": "2024-04-29T00:00:02.200000",
                "dotted_order": "20240429T000000000000Zroot.20240429T000002000000Zn2.20240429T000002100000Ztool1",
                "inputs": {"query": "hello"},
                "outputs": {"result": "ok"},
                "status": "success",
            },
        ]
    }

    trace = detect_and_parse(raw)
    assert trace.metadata.framework == "langgraph"
    assert len(trace.state_transitions) >= 4
    assert len(trace.tool_calls) >= 1

    service = AnalysisService()
    report = service.analyze_raw(raw)
    assert report.langgraph_analysis is not None
    assert len(report.langgraph_analysis.state_loops) >= 1
