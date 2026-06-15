import json
from pathlib import Path

import pytest

from app.services.analysis_service import AnalysisService

SAMPLE_PATH = Path(__file__).resolve().parent.parent.parent / "samples" / "sample_trace.json"


@pytest.fixture
def sample_trace() -> dict:
    with open(SAMPLE_PATH) as f:
        return json.load(f)


@pytest.fixture
def service() -> AnalysisService:
    return AnalysisService()


def test_sample_analysis_produces_report(service, sample_trace):
    report = service.analyze_raw(sample_trace)
    assert 0 <= report.health.score <= 100
    assert report.metadata["run_id"] == "run-2024-001"
    assert report.metadata["total_steps"] == 19


def test_loop_detection(service, sample_trace):
    report = service.analyze_raw(sample_trace)
    assert len(report.loops) >= 1
    assert any(e.tool_name == "Search" for e in report.loops)


def test_hallucination_detection(service, sample_trace):
    report = service.analyze_raw(sample_trace)
    assert report.hallucination.detected
    assert "DatabaseLookup" in report.hallucination.hallucinated_tools


def test_tool_analysis(service, sample_trace):
    report = service.analyze_raw(sample_trace)
    assert report.tool_analysis.total_calls >= 5
    assert report.tool_analysis.most_used == "Search"


def test_redundancy_detection(service, sample_trace):
    report = service.analyze_raw(sample_trace)
    assert report.redundancy.redundancy_score > 0
    assert len(report.redundancy.redundant_pairs) >= 1


def test_cost_analysis(service, sample_trace):
    report = service.analyze_raw(sample_trace)
    assert report.cost_analysis.total_tokens > 0
    assert report.cost_analysis.total_cost_usd > 0
