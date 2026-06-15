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


class LangGraphStateLoop(BaseModel):
    cycle_length: int
    repeated_states: list[str]
    repetitions: int
    step_indices: list[int] = Field(default_factory=list)
    severity: IssueSeverity = IssueSeverity.MEDIUM


class LangGraphBranchAnalysis(BaseModel):
    branch_count: int
    max_branch_depth: int
    dead_end_branches: int
    successful_branches: int
    summary: str


class LangGraphNodeBottleneck(BaseModel):
    most_expensive_node: str | None = None
    most_expensive_cost_usd: float = 0.0
    slowest_node: str | None = None
    slowest_duration_ms: float | None = None
    most_frequent_node: str | None = None
    most_frequent_count: int = 0


class LangGraphAnalysisResult(BaseModel):
    state_loops: list[LangGraphStateLoop] = Field(default_factory=list)
    branches: LangGraphBranchAnalysis | None = None
    bottlenecks: LangGraphNodeBottleneck | None = None


class HealthVerdict(str, Enum):
    EXCELLENT = "Excellent"
    GOOD = "Good"
    FAIR = "Fair"
    POOR = "Poor"
    CRITICAL = "Critical"


class ExecutiveSummary(BaseModel):
    overview: str
    key_findings: list[str] = Field(default_factory=list)
    priority_actions: list[str] = Field(default_factory=list)
    health_verdict: HealthVerdict


class CausalAnalysis(BaseModel):
    """
    Deterministic causal tracing output for failure analysis and visual analytics.
    """

    root_cause_node: str | None = None
    failure_path: list[str] = Field(default_factory=list)
    node_metrics: dict[str, dict[str, float]] = Field(default_factory=dict)


class HealthReport(BaseModel):
    score: int
    grade: str
    factors: dict[str, float]
    strengths: list[str]
    summary: str


class AnalysisReport(BaseModel):
    metadata: dict[str, Any]
    executive_summary: ExecutiveSummary
    causal_analysis: CausalAnalysis = Field(default_factory=CausalAnalysis)
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
    langgraph_analysis: LangGraphAnalysisResult | None = None
