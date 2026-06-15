from __future__ import annotations

from dataclasses import dataclass

from app.models.report import (
    CostAnalysisResult,
    ExecutiveSummary,
    HallucinationResult,
    HealthReport,
    HealthVerdict,
    LangGraphAnalysisResult,
    LoopEvent,
    Recommendation,
    RedundancyResult,
    ToolAnalysisResult,
)
from app.models.trace import NormalizedTrace, RunStatus


@dataclass(frozen=True)
class SummarySignals:
    """
    Compact metrics used for deterministic verdicting + summary generation.
    """

    status: str
    hallucination_count: int
    loop_count: int
    redundancy_score: float
    tool_inefficiency: float
    cost_concentration: float


class ExecutiveSummaryGenerator:
    """
    Deterministic executive summary generation.

    Rules:
    - No LLM calls.
    - Only derived from already-produced analysis outputs.
    - Stable ordering and phrasing for testability.
    """

    def generate(
        self,
        *,
        trace: NormalizedTrace,
        health: HealthReport,
        recommendations: list[Recommendation],
        loops: list[LoopEvent],
        tool_analysis: ToolAnalysisResult,
        cost_analysis: CostAnalysisResult,
        redundancy: RedundancyResult,
        hallucination: HallucinationResult,
        langgraph_analysis: LangGraphAnalysisResult | None = None,
    ) -> ExecutiveSummary:
        signals = self._signals(
            trace=trace,
            loops=loops,
            tool_analysis=tool_analysis,
            cost_analysis=cost_analysis,
            redundancy=redundancy,
            hallucination=hallucination,
        )

        langgraph_loop_count = len(langgraph_analysis.state_loops) if langgraph_analysis else 0
        points = self._score_points(
            signals=signals,
            langgraph_loop_count=langgraph_loop_count,
            total_cost_usd=float(cost_analysis.total_cost_usd),
        )
        verdict = self._verdict_from_points(points)

        overview = self._overview(trace=trace, tool_analysis=tool_analysis)
        key_findings = self._key_findings(
            trace=trace,
            signals=signals,
            loops=loops,
            tool_analysis=tool_analysis,
            cost_analysis=cost_analysis,
            redundancy=redundancy,
            hallucination=hallucination,
            langgraph_analysis=langgraph_analysis,
        )
        priority_actions = self._priority_actions(
            recommendations=recommendations,
            signals=signals,
            loops=loops,
            tool_analysis=tool_analysis,
            cost_analysis=cost_analysis,
            redundancy=redundancy,
            hallucination=hallucination,
            langgraph_analysis=langgraph_analysis,
        )

        return ExecutiveSummary(
            overview=overview,
            key_findings=key_findings,
            priority_actions=priority_actions,
            health_verdict=verdict,
        )

    @staticmethod
    def _normalize_redundancy_ratio(score: float) -> float:
        """
        The codebase's redundancy analyzer reports a percentage (0..100).
        Accept either 0..1 ratios or 0..100 percentages and return a 0..1 ratio.
        """

        if score <= 1.0:
            return max(0.0, min(1.0, score))
        return max(0.0, min(1.0, score / 100.0))

    @classmethod
    def _score_points(
        cls,
        *,
        signals: SummarySignals,
        langgraph_loop_count: int,
        total_cost_usd: float,
    ) -> int:
        """
        Strict deterministic scoring (lower is better).

        Base: 0
        - Status failure: +3
        - Hallucinations: +3 per occurrence
        - Loops (generic + LangGraph state loops): +2 per occurrence
        - High redundancy (>0.7): +2
        - High cost (>$0.05): +1
        """

        points = 0

        if signals.status != RunStatus.SUCCESS.value:
            points += 3

        points += int(signals.hallucination_count) * 3
        points += (int(signals.loop_count) + int(langgraph_loop_count)) * 2

        redundancy_ratio = cls._normalize_redundancy_ratio(float(signals.redundancy_score))
        if redundancy_ratio > 0.7:
            points += 2

        if float(total_cost_usd) > 0.05:
            points += 1

        return points

    @staticmethod
    def _verdict_from_points(points: int) -> HealthVerdict:
        if points <= 1:
            return HealthVerdict.EXCELLENT
        if points <= 3:
            return HealthVerdict.GOOD
        if points <= 6:
            return HealthVerdict.FAIR
        if points <= 9:
            return HealthVerdict.POOR
        return HealthVerdict.CRITICAL

    @staticmethod
    def _signals(
        *,
        trace: NormalizedTrace,
        loops: list[LoopEvent],
        tool_analysis: ToolAnalysisResult,
        cost_analysis: CostAnalysisResult,
        redundancy: RedundancyResult,
        hallucination: HallucinationResult,
    ) -> SummarySignals:
        tool_inefficiency = 0.0
        if tool_analysis.total_calls > 0 and tool_analysis.most_used:
            top = next((t for t in tool_analysis.per_tool if t.tool_name == tool_analysis.most_used), None)
            if top:
                tool_inefficiency = float(top.percentage) / 100.0

        cost_concentration = 0.0
        if cost_analysis.most_expensive_step:
            cost_concentration = float(cost_analysis.most_expensive_step.percentage) / 100.0

        status = trace.metadata.status.value if hasattr(trace.metadata.status, "value") else str(trace.metadata.status)

        return SummarySignals(
            status=status,
            # Count occurrences (tool call steps), not unique tool names.
            hallucination_count=len(hallucination.affected_steps) if hallucination.detected else 0,
            loop_count=len(loops),
            redundancy_score=float(redundancy.redundancy_score),
            tool_inefficiency=tool_inefficiency,
            cost_concentration=cost_concentration,
        )

    @staticmethod
    def _overview(*, trace: NormalizedTrace, tool_analysis: ToolAnalysisResult) -> str:
        total_steps = len(trace.steps)
        unique_tools = tool_analysis.unique_tools
        return f"Agent executed {total_steps} steps across {unique_tools} tools."

    # NOTE: health verdict is now fully derived from _score_points() to keep it stable and testable.

    @staticmethod
    def _key_findings(
        *,
        trace: NormalizedTrace,
        signals: SummarySignals,
        loops: list[LoopEvent],
        tool_analysis: ToolAnalysisResult,
        cost_analysis: CostAnalysisResult,
        redundancy: RedundancyResult,
        hallucination: HallucinationResult,
        langgraph_analysis: LangGraphAnalysisResult | None,
    ) -> list[str]:
        findings: list[str] = []

        # 1) Status
        if signals.status != RunStatus.SUCCESS.value:
            findings.append(f"Run ended with status: {signals.status}")

        # 2) Hallucinations
        if hallucination.detected and hallucination.hallucinated_tools:
            tools = ", ".join(sorted(set(hallucination.hallucinated_tools))[:5])
            findings.append(f"Detected {signals.hallucination_count} hallucinated tool call(s): {tools}")

        # 3) Loop findings (generic tool loops)
        if loops:
            worst = max(loops, key=lambda l: l.consecutive_count)
            if worst.tool_name:
                findings.append(
                    f"Observed tool loop: {worst.tool_name} repeated {worst.consecutive_count} times"
                )
            else:
                findings.append(f"Observed {signals.loop_count} loop pattern(s)")

        # 4) LangGraph state loops
        if langgraph_analysis and langgraph_analysis.state_loops:
            top = max(langgraph_analysis.state_loops, key=lambda l: l.repetitions)
            seq = " → ".join(top.repeated_states)
            findings.append(
                f"LangGraph state loop detected (cycle {top.cycle_length}, x{top.repetitions}): {seq}"
            )

        # 5) Redundancy
        if redundancy.total_thoughts > 0:
            findings.append(
                f"Reasoning redundancy reached {signals.redundancy_score:.0f}% "
                f"({redundancy.redundant_thought_count}/{redundancy.total_thoughts} thoughts)"
            )

        # 6) Tool dominance
        if tool_analysis.total_calls > 0 and tool_analysis.most_used:
            top = next((t for t in tool_analysis.per_tool if t.tool_name == tool_analysis.most_used), None)
            if top and top.percentage >= 60:
                findings.append(f"Tool usage dominated by {top.tool_name} ({top.percentage:.0f}%)")

        # 7) Cost concentration
        if cost_analysis.total_cost_usd > 0 and cost_analysis.most_expensive_step:
            top_step = cost_analysis.most_expensive_step
            if top_step.percentage >= 50:
                findings.append(
                    f"Cost concentrated in step {top_step.step_index} ({top_step.percentage:.0f}% of total cost)"
                )

        # Stable output size
        return findings[:5]

    @staticmethod
    def _priority_actions(
        *,
        recommendations: list[Recommendation],
        signals: SummarySignals,
        loops: list[LoopEvent],
        tool_analysis: ToolAnalysisResult,
        cost_analysis: CostAnalysisResult,
        redundancy: RedundancyResult,
        hallucination: HallucinationResult,
        langgraph_analysis: LangGraphAnalysisResult | None,
    ) -> list[str]:
        # Prefer existing deterministic recommendation engine output.
        severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        ordered = sorted(recommendations, key=lambda r: severity_rank.get(r.severity.value, 99))

        actions: list[str] = []
        seen: set[str] = set()
        for rec in ordered:
            text = rec.recommendation.strip()
            if text and text not in seen:
                actions.append(text)
                seen.add(text)
            if len(actions) >= 3:
                return actions

        # Fallbacks when no recommendation is produced.
        if hallucination.detected and hallucination.hallucinated_tools:
            actions.append("Add tool registry validation")
        if loops:
            actions.append("Implement loop guards")
        if langgraph_analysis and langgraph_analysis.state_loops:
            actions.append("Add LangGraph state loop guards")
        if redundancy.redundancy_score >= 50:
            actions.append("Deduplicate planning steps and tighten reasoning to reduce redundancy")
        if cost_analysis.most_expensive_step and cost_analysis.most_expensive_step.percentage >= 50:
            actions.append("Reduce prompt/context size for the most expensive steps to lower cost concentration")
        if tool_analysis.total_calls > 0 and tool_analysis.most_used:
            top = next((t for t in tool_analysis.per_tool if t.tool_name == tool_analysis.most_used), None)
            if top and top.percentage >= 60:
                actions.append(f"Cache/reuse results to reduce repeated {top.tool_name} calls")
        if signals.status != RunStatus.SUCCESS.value:
            actions.append("Improve failure handling and stop conditions to avoid non-successful runs")

        # Deduplicate and cap.
        out: list[str] = []
        for a in actions:
            if a not in seen:
                out.append(a)
                seen.add(a)
            if len(out) >= 3:
                break
        return out
