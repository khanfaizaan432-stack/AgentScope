from __future__ import annotations

from fastapi.testclient import TestClient

from app.comparison.comparison_engine import ComparisonEngine
from app.comparison.comparison_models import ComparisonReport, MetricDelta
from app.main import app
from app.models.report import (
    AnalysisReport,
    CostAnalysisResult,
    ExecutiveSummary,
    HallucinationResult,
    HealthVerdict,
    HealthReport,
    LoopEvent,
    RedundancyPair,
    RedundancyResult,
    StepCost,
    ToolAnalysisResult,
    ToolUsageStats,
    WorkflowGraph,
)


def build_report(
    *,
    score: int = 72,
    total_cost: float = 10.0,
    total_tokens: int = 1000,
    loops: int = 2,
    redundancy: float = 35.0,
    hallucinations: int = 1,
    run_id: str = "run-a",
) -> AnalysisReport:
    step_cost = StepCost(
        step_index=0,
        stage="analysis",
        prompt_tokens=600,
        completion_tokens=400,
        cost_usd=total_cost,
        percentage=100.0,
    )
    loop_events = [
        LoopEvent(tool_name=f"tool-{i}", consecutive_count=3, step_indices=[i, i + 1, i + 2])
        for i in range(loops)
    ]
    redundant_pair = RedundancyPair(step_a=0, step_b=1, similarity=0.9, content_a="a", content_b="b")
    hallucinated_tools = [f"FakeTool{i}" for i in range(hallucinations)]

    return AnalysisReport(
        metadata={
            "run_id": run_id,
            "framework": "generic",
            "agent_name": "assistant",
            "status": "success",
            "total_steps": 5,
            "started_at": None,
            "completed_at": None,
        },
        executive_summary=ExecutiveSummary(
            overview="placeholder",
            key_findings=[],
            priority_actions=[],
            health_verdict=HealthVerdict.GOOD,
        ),
        health=HealthReport(score=score, grade="A", factors={}, strengths=["steady"], summary="healthy"),
        issues=[],
        recommendations=[],
        loops=loop_events,
        tool_analysis=ToolAnalysisResult(
            total_calls=6,
            unique_tools=2,
            per_tool=[ToolUsageStats(tool_name="search", call_count=4, percentage=66.7)],
            most_used="search",
            least_used="search",
            unused_tools=[],
        ),
        cost_analysis=CostAnalysisResult(
            total_prompt_tokens=600,
            total_completion_tokens=400,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            per_step=[step_cost],
            cost_by_stage={"analysis": total_cost},
            most_expensive_step=step_cost,
        ),
        redundancy=RedundancyResult(
            redundancy_score=redundancy,
            redundant_pairs=[redundant_pair] if redundancy > 0 else [],
            total_thoughts=4,
            redundant_thought_count=1 if redundancy > 0 else 0,
        ),
        hallucination=HallucinationResult(
            hallucinated_tools=hallucinated_tools,
            affected_steps=list(range(hallucinations)),
            detected=hallucinations > 0,
        ),
        timeline=[],
        timeline_edges=[],
        workflow_graph=WorkflowGraph(nodes=[], edges=[]),
    )


def compare(report_a: AnalysisReport, report_b: AnalysisReport) -> ComparisonReport:
    return ComparisonEngine().compare_reports(report_a, report_b)


def build_compare_payload(run: str) -> dict:
    return {
        "run": run,
        "steps": [{"type": "thought", "content": f"trace for {run}"}],
    }


def test_comparison_report_model_serializes() -> None:
    report = ComparisonReport(
        score_delta=MetricDelta(before=1, after=2, delta=1.0),
        cost_delta=MetricDelta(before=1, after=2, delta=1.0),
        loop_delta=MetricDelta(before=1, after=2, delta=1.0),
        redundancy_delta=MetricDelta(before=1, after=2, delta=1.0),
        hallucination_delta=MetricDelta(before=1, after=2, delta=1.0),
        regressions=[],
        improvements=[],
        verdict="Mixed Results",
    )

    dumped = report.model_dump()
    assert dumped["score_delta"]["delta"] == 1.0
    assert dumped["verdict"] == "Mixed Results"


def test_metric_delta_preserves_before_and_after() -> None:
    delta = MetricDelta(before=7, after=4, delta=-3.0)
    assert delta.before == 7
    assert delta.after == 4
    assert delta.delta == -3.0


def test_identical_reports_have_zero_deltas() -> None:
    report = build_report()
    comparison = compare(report, report.model_copy(deep=True))
    assert comparison.score_delta.delta == 0
    assert comparison.cost_delta.delta == 0
    assert comparison.loop_delta.delta == 0
    assert comparison.redundancy_delta.delta == 0
    assert comparison.hallucination_delta.delta == 0


def test_identical_reports_have_no_changes() -> None:
    comparison = compare(build_report(), build_report())
    assert comparison.improvements == []
    assert comparison.regressions == []
    assert comparison.verdict == "No Significant Change"


def test_score_improvement_is_positive() -> None:
    comparison = compare(build_report(score=60), build_report(score=72))
    assert comparison.score_delta.delta == 12


def test_score_regression_is_negative() -> None:
    comparison = compare(build_report(score=80), build_report(score=67))
    assert comparison.score_delta.delta == -13


def test_score_improvement_message_present() -> None:
    comparison = compare(build_report(score=60), build_report(score=72))
    assert any(message.startswith("Health score improved") for message in comparison.improvements)


def test_score_regression_message_present() -> None:
    comparison = compare(build_report(score=80), build_report(score=67))
    assert any(message.startswith("Health score declined") for message in comparison.regressions)


def test_cost_decrease_is_improvement() -> None:
    comparison = compare(build_report(total_cost=10.0), build_report(total_cost=7.5))
    assert comparison.cost_delta.delta == -2.5
    assert any("Cost reduced" in message for message in comparison.improvements)


def test_cost_increase_is_regression() -> None:
    comparison = compare(build_report(total_cost=10.0), build_report(total_cost=12.0))
    assert comparison.cost_delta.delta == 2.0
    assert any("Cost increased" in message for message in comparison.regressions)


def test_loop_count_decrease_is_improvement() -> None:
    comparison = compare(build_report(loops=5), build_report(loops=1))
    assert comparison.loop_delta.delta == -4
    assert any("Looping reduced" in message for message in comparison.improvements)


def test_loop_count_increase_is_regression() -> None:
    comparison = compare(build_report(loops=1), build_report(loops=4))
    assert comparison.loop_delta.delta == 3
    assert any("More loops detected" in message for message in comparison.regressions)


def test_redundancy_decrease_is_improvement() -> None:
    comparison = compare(build_report(redundancy=50.0), build_report(redundancy=18.0))
    assert comparison.redundancy_delta.delta == -32.0
    assert any("Redundancy reduced" in message for message in comparison.improvements)


def test_redundancy_increase_is_regression() -> None:
    comparison = compare(build_report(redundancy=18.0), build_report(redundancy=55.0))
    assert comparison.redundancy_delta.delta == 37.0
    assert any("Redundancy increased" in message for message in comparison.regressions)


def test_hallucination_resolution_is_improvement() -> None:
    comparison = compare(build_report(hallucinations=2), build_report(hallucinations=0))
    assert comparison.hallucination_delta.delta == -2
    assert any("Hallucinations eliminated" in message for message in comparison.improvements)


def test_new_hallucinations_are_regression() -> None:
    comparison = compare(build_report(hallucinations=0), build_report(hallucinations=3))
    assert comparison.hallucination_delta.delta == 3
    assert any("New hallucinated tools appeared" in message for message in comparison.regressions)


def test_tool_efficiency_improves_with_fewer_tokens() -> None:
    comparison = compare(build_report(total_tokens=2000), build_report(total_tokens=1200))
    assert any("Tool efficiency improved" in message for message in comparison.improvements)


def test_tool_efficiency_regresses_with_more_tokens() -> None:
    comparison = compare(build_report(total_tokens=1200), build_report(total_tokens=1800))
    assert any("Tool efficiency regressed" in message for message in comparison.regressions)


def test_major_improvement_verdict() -> None:
    comparison = compare(
        build_report(score=58, total_cost=11.0, loops=4, hallucinations=1),
        build_report(score=72, total_cost=8.0, loops=1, hallucinations=0),
    )
    assert comparison.verdict == "Major Improvement"


def test_regression_detected_verdict() -> None:
    comparison = compare(
        build_report(score=76, total_cost=9.0, loops=1, hallucinations=0),
        build_report(score=61, total_cost=13.0, loops=4, hallucinations=3),
    )
    assert comparison.verdict == "Regression Detected"


def test_mixed_results_verdict() -> None:
    comparison = compare(
        build_report(score=65, total_cost=10.0, loops=3, redundancy=25.0, hallucinations=1),
        build_report(score=74, total_cost=12.0, loops=2, redundancy=31.0, hallucinations=1),
    )
    assert comparison.verdict == "Mixed Results"


def test_health_score_delta_matches_difference() -> None:
    comparison = compare(build_report(score=61), build_report(score=73))
    assert comparison.score_delta.before == 61
    assert comparison.score_delta.after == 73
    assert comparison.score_delta.delta == 12


def test_cost_delta_uses_cost_not_tokens() -> None:
    comparison = compare(build_report(total_cost=9.5, total_tokens=2000), build_report(total_cost=7.0, total_tokens=1000))
    assert comparison.cost_delta.delta == -2.5


def test_loop_delta_counts_loop_events() -> None:
    comparison = compare(build_report(loops=2), build_report(loops=6))
    assert comparison.loop_delta.before == 2
    assert comparison.loop_delta.after == 6
    assert comparison.loop_delta.delta == 4


def test_hallucination_delta_counts_tools() -> None:
    comparison = compare(build_report(hallucinations=1), build_report(hallucinations=4))
    assert comparison.hallucination_delta.before == 1
    assert comparison.hallucination_delta.after == 4
    assert comparison.hallucination_delta.delta == 3


def test_improvement_list_includes_multiple_messages() -> None:
    comparison = compare(
        build_report(score=60, total_cost=10.0, loops=4, redundancy=40.0, hallucinations=1, total_tokens=1600),
        build_report(score=75, total_cost=7.5, loops=1, redundancy=20.0, hallucinations=0, total_tokens=1100),
    )
    assert len(comparison.improvements) >= 4


def test_regression_list_includes_multiple_messages() -> None:
    comparison = compare(
        build_report(score=78, total_cost=7.0, loops=1, redundancy=18.0, hallucinations=0, total_tokens=900),
        build_report(score=66, total_cost=10.5, loops=3, redundancy=34.0, hallucinations=2, total_tokens=1500),
    )
    assert len(comparison.regressions) >= 4


def test_api_compare_endpoint_returns_report(monkeypatch) -> None:
    report_a = build_report(score=60, total_cost=10.0, loops=3, hallucinations=1, run_id="a")
    report_b = build_report(score=72, total_cost=7.0, loops=1, hallucinations=0, run_id="b")

    class FakeService:
        def analyze_raw(self, raw: dict) -> AnalysisReport:
            return report_a if raw.get("run") == "a" else report_b

    from app import main as main_module

    monkeypatch.setattr(main_module, "service", FakeService())
    client = TestClient(app)

    response = client.post("/api/v1/compare", json={"run_a": build_compare_payload("a"), "run_b": build_compare_payload("b")})
    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "Major Improvement"
    assert payload["score_delta"]["delta"] == 12


def test_api_compare_endpoint_serializes_lists(monkeypatch) -> None:
    report_a = build_report(score=80, total_cost=8.0, loops=1, hallucinations=0, run_id="a")
    report_b = build_report(score=66, total_cost=12.0, loops=4, hallucinations=2, run_id="b")

    class FakeService:
        def analyze_raw(self, raw: dict) -> AnalysisReport:
            return report_a if raw.get("run") == "a" else report_b

    from app import main as main_module

    monkeypatch.setattr(main_module, "service", FakeService())
    client = TestClient(app)

    response = client.post("/api/v1/compare", json={"run_a": build_compare_payload("a"), "run_b": build_compare_payload("b")})
    payload = response.json()
    assert isinstance(payload["improvements"], list)
    assert isinstance(payload["regressions"], list)


def test_api_compare_endpoint_handles_mixed_results(monkeypatch) -> None:
    report_a = build_report(score=70, total_cost=10.0, loops=2, redundancy=20.0, hallucinations=1, run_id="a")
    report_b = build_report(score=76, total_cost=11.5, loops=1, redundancy=26.0, hallucinations=1, run_id="b")

    class FakeService:
        def analyze_raw(self, raw: dict) -> AnalysisReport:
            return report_a if raw.get("run") == "a" else report_b

    from app import main as main_module

    monkeypatch.setattr(main_module, "service", FakeService())
    client = TestClient(app)

    response = client.post("/api/v1/compare", json={"run_a": build_compare_payload("a"), "run_b": build_compare_payload("b")})
    assert response.status_code == 200
    assert response.json()["verdict"] == "Mixed Results"


def test_api_compare_endpoint_requires_both_runs() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/compare", json={"run_a": {"run": "a"}})
    assert response.status_code == 422


def test_api_compare_endpoint_rejects_empty_run_payloads() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/compare", json={"run_a": {}, "run_b": {}})
    assert response.status_code == 400
    assert "Run A must contain" in response.json()["detail"]


def test_api_compare_endpoint_rejects_empty_step_runs() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/compare", json={"run_a": {"steps": []}, "run_b": {"steps": []}})
    assert response.status_code == 400
    assert "Run A must contain" in response.json()["detail"]


def test_api_compare_endpoint_accepts_minimal_runs_without_metrics() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/compare",
        json={
            "run_a": {"metadata": {"run_id": "a"}, "steps": [{"type": "thought", "content": "hello"}]},
            "run_b": {"metadata": {"run_id": "b"}, "steps": [{"type": "thought", "content": "hello"}]},
        },
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["verdict"] == "No Significant Change"
    assert payload["cost_delta"]["delta"] == 0.0


def test_api_compare_endpoint_emits_hallucination_resolution(monkeypatch) -> None:
    report_a = build_report(hallucinations=2, run_id="a")
    report_b = build_report(hallucinations=0, run_id="b")

    class FakeService:
        def analyze_raw(self, raw: dict) -> AnalysisReport:
            return report_a if raw.get("run") == "a" else report_b

    from app import main as main_module

    monkeypatch.setattr(main_module, "service", FakeService())
    client = TestClient(app)

    response = client.post("/api/v1/compare", json={"run_a": build_compare_payload("a"), "run_b": build_compare_payload("b")})
    payload = response.json()
    assert any("Hallucinations eliminated" in item for item in payload["improvements"])


def test_openapi_compare_schema_references_comparison_report() -> None:
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()
    compare_operation = openapi["paths"]["/api/v1/compare"]["post"]
    analyze_operation = openapi["paths"]["/api/v1/analyze/json"]["post"]

    assert compare_operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("ComparisonRequest")
    assert compare_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("ComparisonReport")
    assert analyze_operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("AnalysisReport")
