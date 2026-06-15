"""
Tests for the Recommendation Engine (Priority 1).
Covers each generator independently and the full integration via AnalysisService.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.analyzers.recommendation_engine import (
    CostConcentrationRecommendationGenerator,
    HallucinationRecommendationGenerator,
    LoopRecommendationGenerator,
    RecommendationEngine,
    RedundancyRecommendationGenerator,
    ToolInefficiencyRecommendationGenerator,
)
from app.models.report import (
    CostAnalysisResult,
    HallucinationResult,
    IssueSeverity,
    LoopEvent,
    RedundancyPair,
    RedundancyResult,
    StepCost,
    ToolAnalysisResult,
    ToolUsageStats,
)
from app.services.analysis_service import AnalysisService

SAMPLE_PATH = Path(__file__).resolve().parent.parent.parent / "samples" / "sample_trace.json"


@pytest.fixture
def sample_trace() -> dict:
    with open(SAMPLE_PATH) as f:
        return json.load(f)


@pytest.fixture
def service() -> AnalysisService:
    return AnalysisService()


# ---------------------------------------------------------------------------
# LoopRecommendationGenerator
# ---------------------------------------------------------------------------

class TestLoopRecommendationGenerator:
    gen = LoopRecommendationGenerator()

    def test_no_loops_returns_empty(self):
        assert self.gen.generate([]) == []

    def test_consecutive_loop_search_tool(self):
        event = LoopEvent(
            tool_name="search",
            consecutive_count=4,
            step_indices=[1, 2, 3, 4],
            pattern_type="consecutive",
            severity=IssueSeverity.HIGH,
        )
        recs = self.gen.generate([event])
        assert len(recs) == 1
        rec = recs[0]
        assert rec.issue == "Search Loop"
        assert rec.severity == IssueSeverity.HIGH
        assert rec.evidence["tool"] == "search"
        assert rec.evidence["consecutive_calls"] == 4
        assert rec.category == "loop"
        assert "cach" in rec.recommendation.lower()  # "caching" mentioned

    def test_critical_severity_at_five_consecutive(self):
        event = LoopEvent(
            tool_name="fetch",
            consecutive_count=5,
            step_indices=list(range(5)),
            pattern_type="consecutive",
            severity=IssueSeverity.HIGH,
        )
        recs = self.gen.generate([event])
        assert recs[0].severity == IssueSeverity.CRITICAL

    def test_generic_tool_loop_label(self):
        event = LoopEvent(
            tool_name="calculator",
            consecutive_count=3,
            step_indices=[0, 1, 2],
            pattern_type="consecutive",
            severity=IssueSeverity.HIGH,
        )
        recs = self.gen.generate([event])
        assert recs[0].issue == "Tool Loop"

    def test_cyclic_state_loop(self):
        event = LoopEvent(
            tool_name=None,
            consecutive_count=2,
            step_indices=[5, 8],
            pattern_type="cyclic",
            severity=IssueSeverity.MEDIUM,
        )
        recs = self.gen.generate([event])
        assert len(recs) == 1
        rec = recs[0]
        assert rec.issue == "Cyclic State Transition"
        assert rec.severity == IssueSeverity.MEDIUM
        assert "cycle_length" in rec.evidence

    def test_multiple_loops_produce_multiple_recommendations(self):
        events = [
            LoopEvent(tool_name="search", consecutive_count=4, step_indices=[1,2,3,4], pattern_type="consecutive", severity=IssueSeverity.HIGH),
            LoopEvent(tool_name="fetch", consecutive_count=3, step_indices=[5,6,7], pattern_type="consecutive", severity=IssueSeverity.HIGH),
        ]
        recs = self.gen.generate(events)
        assert len(recs) == 2


# ---------------------------------------------------------------------------
# HallucinationRecommendationGenerator
# ---------------------------------------------------------------------------

class TestHallucinationRecommendationGenerator:
    gen = HallucinationRecommendationGenerator()

    def test_no_hallucination_returns_empty(self):
        result = HallucinationResult(hallucinated_tools=[], affected_steps=[], detected=False)
        assert self.gen.generate(result) == []

    def test_hallucination_produces_critical_recommendation(self):
        result = HallucinationResult(
            hallucinated_tools=["DatabaseLookup", "FakeAPI"],
            affected_steps=[11, 15],
            detected=True,
        )
        recs = self.gen.generate(result)
        assert len(recs) == 1
        rec = recs[0]
        assert rec.issue == "Hallucinated Tool Call"
        assert rec.severity == IssueSeverity.CRITICAL
        assert rec.evidence["tool_count"] == 2
        assert "DatabaseLookup" in rec.evidence["hallucinated_tools"]
        assert rec.category == "hallucination"
        assert "registry" in rec.recommendation.lower()


# ---------------------------------------------------------------------------
# RedundancyRecommendationGenerator
# ---------------------------------------------------------------------------

class TestRedundancyRecommendationGenerator:
    gen = RedundancyRecommendationGenerator()

    def _make_result(self, score: float) -> RedundancyResult:
        pair = RedundancyPair(step_a=0, step_b=1, similarity=0.9, content_a="a", content_b="b")
        return RedundancyResult(
            redundancy_score=score,
            redundant_pairs=[pair] if score > 0 else [],
            total_thoughts=4,
            redundant_thought_count=2 if score > 0 else 0,
        )

    def test_low_redundancy_returns_empty(self):
        assert self.gen.generate(self._make_result(20.0)) == []

    def test_medium_redundancy_medium_severity(self):
        recs = self.gen.generate(self._make_result(40.0))
        assert len(recs) == 1
        assert recs[0].severity == IssueSeverity.MEDIUM

    def test_high_redundancy_high_severity(self):
        recs = self.gen.generate(self._make_result(75.0))
        assert len(recs) == 1
        assert recs[0].severity == IssueSeverity.HIGH

    def test_evidence_contains_score_and_pairs(self):
        recs = self.gen.generate(self._make_result(60.0))
        ev = recs[0].evidence
        assert "redundancy_score_pct" in ev
        assert "redundant_thought_pairs" in ev
        assert "total_thoughts" in ev


# ---------------------------------------------------------------------------
# CostConcentrationRecommendationGenerator
# ---------------------------------------------------------------------------

class TestCostConcentrationRecommendationGenerator:
    gen = CostConcentrationRecommendationGenerator()

    def _make_cost(self, pct: float, stage: str = "retrieval") -> CostAnalysisResult:
        step = StepCost(
            step_index=3,
            stage=stage,
            prompt_tokens=500,
            completion_tokens=100,
            cost_usd=pct / 100,
            percentage=pct,
        )
        return CostAnalysisResult(
            total_prompt_tokens=1000,
            total_completion_tokens=200,
            total_tokens=1200,
            total_cost_usd=1.0,
            per_step=[step],
            cost_by_stage={stage: pct / 100},
            most_expensive_step=step,
        )

    def test_low_concentration_returns_empty(self):
        assert self.gen.generate(self._make_cost(20.0)) == []

    def test_high_step_concentration_produces_recommendation(self):
        recs = self.gen.generate(self._make_cost(50.0))
        assert any(r.issue == "Cost Concentration" for r in recs)
        rec = next(r for r in recs if r.issue == "Cost Concentration")
        assert rec.severity == IssueSeverity.HIGH
        assert rec.evidence["step_index"] == 3
        assert rec.evidence["pct_of_total"] == 50.0

    def test_stage_explosion_produces_recommendation(self):
        recs = self.gen.generate(self._make_cost(70.0, stage="planning"))
        issues = {r.issue for r in recs}
        assert "Stage Cost Explosion" in issues or "Cost Concentration" in issues

    def test_zero_total_cost_safe(self):
        cost = CostAnalysisResult(
            total_prompt_tokens=0,
            total_completion_tokens=0,
            total_tokens=0,
            total_cost_usd=0.0,
            per_step=[],
            cost_by_stage={},
            most_expensive_step=None,
        )
        assert self.gen.generate(cost) == []


# ---------------------------------------------------------------------------
# ToolInefficiencyRecommendationGenerator
# ---------------------------------------------------------------------------

class TestToolInefficiencyRecommendationGenerator:
    gen = ToolInefficiencyRecommendationGenerator()

    def _make_tool(self, pct: float, unused: list[str] | None = None) -> ToolAnalysisResult:
        tool = ToolUsageStats(tool_name="search", call_count=int(pct / 10), percentage=pct)
        return ToolAnalysisResult(
            total_calls=10,
            unique_tools=2,
            per_tool=[tool],
            most_used="search",
            least_used="search",
            unused_tools=unused or [],
        )

    def test_low_overuse_no_flag(self):
        assert self.gen.generate(self._make_tool(40.0)) == []

    def test_high_overuse_flagged(self):
        recs = self.gen.generate(self._make_tool(70.0))
        assert any(r.issue == "Tool Overuse" for r in recs)
        rec = next(r for r in recs if r.issue == "Tool Overuse")
        assert rec.severity == IssueSeverity.MEDIUM
        assert rec.evidence["tool"] == "search"

    def test_unused_tools_flagged(self):
        recs = self.gen.generate(self._make_tool(20.0, unused=["WeatherAPI", "CalcTool"]))
        assert any(r.issue == "Unused Tools in Registry" for r in recs)
        rec = next(r for r in recs if r.issue == "Unused Tools in Registry")
        assert rec.severity == IssueSeverity.LOW
        assert "WeatherAPI" in rec.evidence["unused_tools"]

    def test_no_calls_returns_empty(self):
        result = ToolAnalysisResult(
            total_calls=0, unique_tools=0, per_tool=[], most_used=None, least_used=None, unused_tools=[]
        )
        assert self.gen.generate(result) == []


# ---------------------------------------------------------------------------
# RecommendationEngine — full integration via AnalysisService
# ---------------------------------------------------------------------------

class TestRecommendationEngineIntegration:
    def test_sample_trace_produces_recommendations(self, service, sample_trace):
        report = service.analyze_raw(sample_trace)
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) > 0

    def test_recommendations_have_required_fields(self, service, sample_trace):
        report = service.analyze_raw(sample_trace)
        for rec in report.recommendations:
            assert rec.issue, "issue must be non-empty"
            assert rec.severity in list(IssueSeverity)
            assert isinstance(rec.evidence, dict)
            assert rec.recommendation, "recommendation text must be non-empty"
            assert rec.category, "category must be non-empty"

    def test_sample_has_hallucination_recommendation(self, service, sample_trace):
        report = service.analyze_raw(sample_trace)
        issues = [r.issue for r in report.recommendations]
        assert "Hallucinated Tool Call" in issues

    def test_sample_has_loop_recommendation(self, service, sample_trace):
        report = service.analyze_raw(sample_trace)
        loop_recs = [r for r in report.recommendations if r.category == "loop"]
        assert len(loop_recs) >= 1

    def test_recommendations_sorted_by_severity(self, service, sample_trace):
        report = service.analyze_raw(sample_trace)
        severity_order = ["critical", "high", "medium", "low", "info"]
        indices = [severity_order.index(r.severity.value) for r in report.recommendations]
        assert indices == sorted(indices), "Recommendations must be sorted critical → info"

    def test_engine_severity_ordering_standalone(self):
        engine = RecommendationEngine()
        from app.models.report import LoopEvent, HallucinationResult, RedundancyResult, CostAnalysisResult, ToolAnalysisResult

        recs = engine.generate(
            loops=[LoopEvent(tool_name="search", consecutive_count=4, step_indices=[0,1,2,3], pattern_type="consecutive", severity=IssueSeverity.HIGH)],
            hallucination=HallucinationResult(hallucinated_tools=["Ghost"], affected_steps=[5], detected=True),
            redundancy=RedundancyResult(redundancy_score=0.0, redundant_pairs=[], total_thoughts=0, redundant_thought_count=0),
            cost=CostAnalysisResult(total_prompt_tokens=0, total_completion_tokens=0, total_tokens=0, total_cost_usd=0.0, per_step=[], cost_by_stage={}, most_expensive_step=None),
            tool_analysis=ToolAnalysisResult(total_calls=0, unique_tools=0, per_tool=[], most_used=None, least_used=None, unused_tools=[]),
        )
        severity_order = ["critical", "high", "medium", "low", "info"]
        indices = [severity_order.index(r.severity.value) for r in recs]
        assert indices == sorted(indices)
        # hallucination=CRITICAL must come before loop=HIGH
        categories = [r.category for r in recs]
        assert categories.index("hallucination") < categories.index("loop")
