from typing import Any

from fastapi import HTTPException

from app.analyzers.cost_analyzer import CostAnalyzer
from app.analyzers.hallucination_detector import HallucinationDetector
from app.analyzers.langgraph_analyzer import LangGraphAnalyzer
from app.analyzers.loop_detector import LoopDetector
from app.analyzers.recommendation_engine import RecommendationEngine
from app.analyzers.redundancy_analyzer import RedundancyAnalyzer
from app.analyzers.tool_analyzer import ToolAnalyzer
from app.models.report import AnalysisReport, Issue
from app.models.trace import NormalizedTrace
from app.parsers import detect_and_parse
from app.scoring.health_score import GraphBuilder, HealthScorer
from app.services.executive_summary import ExecutiveSummaryGenerator
from app.services.causal_tracer import CausalTracer
from app.utils.security import (
    TracePayloadTooLargeError,
    TraceSecurityError,
    sanitize_trace_payload,
)


class AnalysisService:
    def __init__(self) -> None:
        self.loop_detector = LoopDetector()
        self.tool_analyzer = ToolAnalyzer()
        self.cost_analyzer = CostAnalyzer()
        self.redundancy_analyzer = RedundancyAnalyzer()
        self.hallucination_detector = HallucinationDetector()
        self.langgraph_analyzer = LangGraphAnalyzer()
        self.health_scorer = HealthScorer()
        self.graph_builder = GraphBuilder()
        self.recommendation_engine = RecommendationEngine()
        self.summary_generator = ExecutiveSummaryGenerator()
        self.causal_tracer = CausalTracer()

    def analyze_raw(self, raw: dict[str, Any]) -> AnalysisReport:
        try:
            sanitized = sanitize_trace_payload(raw)
        except TracePayloadTooLargeError as e:
            raise HTTPException(status_code=413, detail=str(e)) from e
        except TraceSecurityError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        trace = detect_and_parse(sanitized)
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

        langgraph_analysis = None
        if trace.metadata.framework == "langgraph":
            langgraph_analysis, langgraph_issues = self.langgraph_analyzer.analyze(trace)
            all_issues.extend(langgraph_issues)

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

        executive_summary = self.summary_generator.generate(
            trace=trace,
            health=health,
            recommendations=recommendations,
            loops=loops,
            tool_analysis=tool_result,
            cost_analysis=cost_result,
            redundancy=redundancy_result,
            hallucination=hallucination_result,
            langgraph_analysis=langgraph_analysis,
        )

        causal_analysis = self.causal_tracer.trace_root_cause(
            trace,
            {
                "loops": loops,
                "langgraph_analysis": langgraph_analysis,
            },
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
            executive_summary=executive_summary,
            causal_analysis=causal_analysis,
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
            langgraph_analysis=langgraph_analysis,
        )
