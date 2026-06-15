from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    LOOP = "loop"
    REDUNDANCY = "redundancy"
    COST = "cost"
    TOOL = "tool"
    HALLUCINATION = "hallucination"
    CONVERGENCE = "convergence"


class Issue(BaseModel):
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    affected_steps: list[int] = Field(default_factory=list)
    metric_value: float | None = None


class Recommendation(BaseModel):
    """A structured, actionable recommendation produced by the RecommendationEngine."""

    issue: str
    severity: IssueSeverity
    evidence: dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    category: str  # mirrors IssueCategory values for grouping


class LoopEvent(BaseModel):
    tool_name: str | None = None
    consecutive_count: int = 0
    step_indices: list[int] = Field(default_factory=list)
    pattern_type: str = "consecutive"
    severity: IssueSeverity = IssueSeverity.MEDIUM


class ToolUsageStats(BaseModel):
    tool_name: str
    call_count: int
    percentage: float


class ToolAnalysisResult(BaseModel):
    total_calls: int
    unique_tools: int
    per_tool: list[ToolUsageStats]
    most_used: str | None = None
    least_used: str | None = None
    unused_tools: list[str] = Field(default_factory=list)


class StepCost(BaseModel):
    step_index: int
    stage: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    percentage: float


class CostAnalysisResult(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost_usd: float
    per_step: list[StepCost]
    cost_by_stage: dict[str, float]
    most_expensive_step: StepCost | None = None


class RedundancyPair(BaseModel):
    step_a: int
    step_b: int
    similarity: float
    content_a: str
    content_b: str


class RedundancyResult(BaseModel):
    redundancy_score: float
    redundant_pairs: list[RedundancyPair]
    total_thoughts: int
    redundant_thought_count: int


class HallucinationResult(BaseModel):
    hallucinated_tools: list[str]
    affected_steps: list[int]
    detected: bool


class TimelineNode(BaseModel):
    id: str
    step_index: int
    type: str
    label: str
    stage: str
    is_loop: bool = False


class TimelineEdge(BaseModel):
    source: str
    target: str


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str
    is_loop: bool = False
    step_index: int | None = None


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    is_loop: bool = False


class WorkflowGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class HealthReport(BaseModel):
    score: int
    grade: str
    factors: dict[str, float]
    strengths: list[str]
    summary: str


class AnalysisReport(BaseModel):
    metadata: dict[str, Any]
    health: HealthReport
    issues: list[Issue]
    recommendations: list["Recommendation"] = Field(default_factory=list)
    loops: list[LoopEvent]
    tool_analysis: ToolAnalysisResult
    cost_analysis: CostAnalysisResult
    redundancy: RedundancyResult
    hallucination: HallucinationResult
    timeline: list[TimelineNode]
    timeline_edges: list[TimelineEdge]
    workflow_graph: WorkflowGraph
