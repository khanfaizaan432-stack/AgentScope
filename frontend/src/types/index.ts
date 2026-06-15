export type IssueSeverity = "critical" | "high" | "medium" | "low" | "info";
export type IssueCategory = "loop" | "redundancy" | "cost" | "tool" | "hallucination" | "convergence";

export interface Recommendation {
  issue: string;
  severity: IssueSeverity;
  evidence: Record<string, unknown>;
  recommendation: string;
  category: string;
}

export interface Issue {
  category: IssueCategory;
  severity: IssueSeverity;
  title: string;
  description: string;
  affected_steps: number[];
  metric_value?: number;
}

export interface HealthReport {
  score: number;
  grade: string;
  factors: Record<string, number>;
  strengths: string[];
  summary: string;
}

export interface ToolUsageStats {
  tool_name: string;
  call_count: number;
  percentage: number;
}

export interface ToolAnalysisResult {
  total_calls: number;
  unique_tools: number;
  per_tool: ToolUsageStats[];
  most_used: string | null;
  least_used: string | null;
  unused_tools: string[];
}

export interface StepCost {
  step_index: number;
  stage: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  percentage: number;
}

export interface CostAnalysisResult {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
  per_step: StepCost[];
  cost_by_stage: Record<string, number>;
  most_expensive_step: StepCost | null;
}

export interface RedundancyPair {
  step_a: number;
  step_b: number;
  similarity: number;
  content_a: string;
  content_b: string;
}

export interface RedundancyResult {
  redundancy_score: number;
  redundant_pairs: RedundancyPair[];
  total_thoughts: number;
  redundant_thought_count: number;
}

export interface HallucinationResult {
  hallucinated_tools: string[];
  affected_steps: number[];
  detected: boolean;
}

export interface LoopEvent {
  tool_name: string | null;
  consecutive_count: number;
  step_indices: number[];
  pattern_type: string;
  severity: IssueSeverity;
}

export interface TimelineNode {
  id: string;
  step_index: number;
  type: string;
  label: string;
  stage: string;
  is_loop: boolean;
}

export interface TimelineEdge {
  source: string;
  target: string;
}

export interface GraphNode {
  id: string;
  label: string;
  node_type: string;
  is_loop: boolean;
  step_index: number | null;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  is_loop: boolean;
}

export interface WorkflowGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AnalysisReport {
  metadata: {
    run_id: string;
    framework: string;
    agent_name: string | null;
    status: string;
    total_steps: number;
    started_at: string | null;
    completed_at: string | null;
  };
  health: HealthReport;
  issues: Issue[];
  recommendations: Recommendation[];
  loops: LoopEvent[];
  tool_analysis: ToolAnalysisResult;
  cost_analysis: CostAnalysisResult;
  redundancy: RedundancyResult;
  hallucination: HallucinationResult;
  timeline: TimelineNode[];
  timeline_edges: TimelineEdge[];
  workflow_graph: WorkflowGraph;
}
