from typing import Any

from pydantic import BaseModel, Field


class MetricDelta(BaseModel):
    before: float | int
    after: float | int
    delta: float


class ComparisonReport(BaseModel):
    score_delta: MetricDelta
    cost_delta: MetricDelta
    loop_delta: MetricDelta
    redundancy_delta: MetricDelta
    hallucination_delta: MetricDelta

    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)

    verdict: str


class ComparisonRequest(BaseModel):
    run_a: dict[str, Any]
    run_b: dict[str, Any]