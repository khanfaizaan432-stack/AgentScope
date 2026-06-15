from typing import Any

from app.analyzers.cost_analyzer import CostAnalyzer
from app.analyzers.hallucination_detector import HallucinationDetector
from app.analyzers.loop_detector import LoopDetector
from app.analyzers.recommendation_engine import RecommendationEngine
from app.analyzers.redundancy_analyzer import RedundancyAnalyzer
from app.analyzers.tool_analyzer import ToolAnalyzer
from app.models.report import AnalysisReport, Issue
from app.models.trace import NormalizedTrace
from app.parsers import detect_and_parse
from app.scoring.health_score import GraphBuilder, HealthScorer


class AnalysisService:
    def __init__(self) -> None:
        self.loop_detector = LoopDetector()
        self.tool_analyzer = ToolAnalyzer()
        self.cost_analyzer = CostAnalyzer()
        self.redundancy_analyzer = RedundancyAnalyzer()
        self.hallucination_detector = HallucinationDetector()
        self.health_scorer = HealthScorer()
        self.graph_builder = GraphBuilder()
        self.recommendation_engine = RecommendationEngine()

    def analyze_raw(self, raw: dict[str, Any]) -> AnalysisReport:
        trace = detect_and_parse(raw)
        return self.analyze(trace)

    def analyze(self, trace: NormalizedTrace) -> AnalysisReport:
        all_issues: list[Issue] = []

        loops, loop_issues = self.loop_detector.analyze(trace)
        all_issues.extend(loop_issues)
        loop_indices = self.loop_detector.get_loop_step_indices(loops)

        tool_result, tool_issues = self.tool_analyzer.analyze(trace)
        all_issues.extend(tool_issues)

        cost_result, cost_issues = self.cost_analyzer.analyze(trace)
        all_issues.extend(cost_issues)

        redundancy_result, redundancy_issues = self.redundancy_analyzer.analyze(trace)
        all_issues.extend(redundancy_issues)

        hallucination_result, hallucination_issues = self.hallucination_detector.analyze(trace)
        all_issues.extend(hallucination_issues)

        tool_inefficiency = 0.0
        if tool_result.total_calls > 0 and tool_result.most_used:
            top = next(t for t in tool_result.per_tool if t.tool_name == tool_result.most_used)
            tool_inefficiency = top.percentage / 100

        cost_concentration = 0.0
        if cost_result.most_expensive_step:
            cost_concentration = cost_result.most_expensive_step.percentage / 100

        health = self.health_scorer.score(
            trace=trace,
            loop_count=len(loops),
            redundancy_score=redundancy_result.redundancy_score,
            cost_concentration=cost_concentration,
            tool_inefficiency=tool_inefficiency,
            hallucination_count=len(hallucination_result.hallucinated_tools),
        )

        timeline_nodes, timeline_edges = self.graph_builder.build_timeline(trace, loop_indices)
        workflow_graph = self.graph_builder.build_workflow_graph(trace, loop_indices)

        all_issues.sort(key=lambda i: ["critical", "high", "medium", "low", "info"].index(i.severity.value))

        recommendations = self.recommendation_engine.generate(
            loops=loops,
            hallucination=hallucination_result,
            redundancy=redundancy_result,
            cost=cost_result,
            tool_analysis=tool_result,
        )

        return AnalysisReport(
            metadata={
                "run_id": trace.metadata.run_id,
                "framework": trace.metadata.framework,
                "agent_name": trace.metadata.agent_name,
                "status": trace.metadata.status.value,
                "total_steps": len(trace.steps),
                "started_at": trace.metadata.started_at,
                "completed_at": trace.metadata.completed_at,
            },
            health=health,
            issues=all_issues,
            recommendations=recommendations,
            loops=loops,
            tool_analysis=tool_result,
            cost_analysis=cost_result,
            redundancy=redundancy_result,
            hallucination=hallucination_result,
            timeline=timeline_nodes,
            timeline_edges=timeline_edges,
            workflow_graph=workflow_graph,
        )
