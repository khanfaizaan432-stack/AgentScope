"""
Recommendation Engine — Priority 1

Reads structured analysis results and emits actionable Recommendation objects.
Each generator handles one failure category and returns zero or more recommendations.
"""

from __future__ import annotations

from app.models.report import (
    CostAnalysisResult,
    HallucinationResult,
    IssueSeverity,
    LoopEvent,
    Recommendation,
    RedundancyResult,
    ToolAnalysisResult,
)


class LoopRecommendationGenerator:
    """Generates recommendations for detected tool-call or state-cycle loops."""

    def generate(self, loops: list[LoopEvent]) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        for event in loops:
            if event.pattern_type == "consecutive" and event.tool_name:
                severity = (
                    IssueSeverity.CRITICAL
                    if event.consecutive_count >= 5
                    else IssueSeverity.HIGH
                )
                recommendations.append(
                    Recommendation(
                        issue="Search Loop" if "search" in event.tool_name.lower() else "Tool Loop",
                        severity=severity,
                        evidence={
                            "tool": event.tool_name,
                            "consecutive_calls": event.consecutive_count,
                            "step_indices": event.step_indices,
                        },
                        recommendation=(
                            "Consider result caching or increasing retrieval quality before "
                            "re-querying. Add a loop-guard that halts re-invocation of the same "
                            "tool when prior results are already in context."
                        ),
                        category="loop",
                    )
                )
            elif event.pattern_type == "cyclic":
                recommendations.append(
                    Recommendation(
                        issue="Cyclic State Transition",
                        severity=IssueSeverity.MEDIUM,
                        evidence={
                            "cycle_length": event.consecutive_count,
                            "affected_steps": event.step_indices,
                        },
                        recommendation=(
                            "Introduce a visited-state guard or a maximum iteration count on "
                            "workflow nodes. Review the transition conditions that re-route "
                            "execution back to an earlier state."
                        ),
                        category="loop",
                    )
                )
        return recommendations


class HallucinationRecommendationGenerator:
    """Generates recommendations when the agent calls tools not in the registry."""

    def generate(self, hallucination: HallucinationResult) -> list[Recommendation]:
        if not hallucination.detected:
            return []
        return [
            Recommendation(
                issue="Hallucinated Tool Call",
                severity=IssueSeverity.CRITICAL,
                evidence={
                    "hallucinated_tools": hallucination.hallucinated_tools,
                    "affected_steps": hallucination.affected_steps,
                    "tool_count": len(hallucination.hallucinated_tools),
                },
                recommendation=(
                    "Inject the tool registry explicitly into the system prompt so the model "
                    "cannot invent tool names. Consider adding an output-validation layer that "
                    "rejects tool calls not present in the declared registry before execution."
                ),
                category="hallucination",
            )
        ]


class RedundancyRecommendationGenerator:
    """Generates recommendations for high reasoning redundancy."""

    HIGH_THRESHOLD = 50.0
    MEDIUM_THRESHOLD = 30.0

    def generate(self, redundancy: RedundancyResult) -> list[Recommendation]:
        score = redundancy.redundancy_score
        if score < self.MEDIUM_THRESHOLD:
            return []

        severity = IssueSeverity.HIGH if score >= self.HIGH_THRESHOLD else IssueSeverity.MEDIUM
        return [
            Recommendation(
                issue="Redundant Reasoning",
                severity=severity,
                evidence={
                    "redundancy_score_pct": score,
                    "redundant_thought_pairs": len(redundancy.redundant_pairs),
                    "redundant_steps": redundancy.redundant_thought_count,
                    "total_thoughts": redundancy.total_thoughts,
                },
                recommendation=(
                    "Shorten the planning prompt to discourage repetitive thought generation. "
                    "Add a deduplication step that collapses semantically identical reasoning "
                    "steps before passing context to the next LLM call."
                ),
                category="redundancy",
            )
        ]


class CostConcentrationRecommendationGenerator:
    """Generates recommendations when a single step or stage dominates token cost."""

    STEP_THRESHOLD_PCT = 40.0   # single step consuming >40% of total cost
    STAGE_THRESHOLD_PCT = 60.0  # single stage consuming >60% of total cost

    def generate(self, cost: CostAnalysisResult) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        if (
            cost.most_expensive_step
            and cost.most_expensive_step.percentage >= self.STEP_THRESHOLD_PCT
        ):
            step = cost.most_expensive_step
            recommendations.append(
                Recommendation(
                    issue="Cost Concentration",
                    severity=IssueSeverity.HIGH,
                    evidence={
                        "step_index": step.step_index,
                        "stage": step.stage,
                        "cost_usd": step.cost_usd,
                        "pct_of_total": step.percentage,
                        "prompt_tokens": step.prompt_tokens,
                        "completion_tokens": step.completion_tokens,
                    },
                    recommendation=(
                        f"Step {step.step_index} ({step.stage}) consumed "
                        f"{step.percentage:.0f}% of total run cost. "
                        "Reduce the input context size for this step by summarizing prior "
                        "conversation history. Consider splitting the task into smaller, "
                        "focused sub-agent calls."
                    ),
                    category="cost",
                )
            )

        # Check for stage-level concentration
        if cost.total_cost_usd > 0:
            dominant = max(cost.cost_by_stage.items(), key=lambda kv: kv[1])
            stage_pct = dominant[1] / cost.total_cost_usd * 100
            if stage_pct >= self.STAGE_THRESHOLD_PCT:
                recommendations.append(
                    Recommendation(
                        issue="Stage Cost Explosion",
                        severity=IssueSeverity.MEDIUM,
                        evidence={
                            "dominant_stage": dominant[0],
                            "stage_cost_usd": round(dominant[1], 6),
                            "pct_of_total": round(stage_pct, 1),
                        },
                        recommendation=(
                            f"The '{dominant[0]}' stage consumed {stage_pct:.0f}% of total cost. "
                            "Review what the agent is doing in this stage — look for repeated "
                            "context growth, unnecessary re-summarization, or large tool outputs "
                            "being passed back verbatim."
                        ),
                        category="cost",
                    )
                )

        return recommendations


class ToolInefficiencyRecommendationGenerator:
    """Generates recommendations for overuse of a single tool or unused tools."""

    OVERUSE_THRESHOLD = 0.60  # one tool = >60% of all calls
    MIN_CALLS_FOR_FLAG = 3

    def generate(self, tool_analysis: ToolAnalysisResult) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        if tool_analysis.total_calls == 0:
            return recommendations

        # Overuse — one tool dominates
        if tool_analysis.most_used:
            top = next(
                t for t in tool_analysis.per_tool if t.tool_name == tool_analysis.most_used
            )
            if (
                top.percentage / 100 >= self.OVERUSE_THRESHOLD
                and top.call_count >= self.MIN_CALLS_FOR_FLAG
            ):
                recommendations.append(
                    Recommendation(
                        issue="Tool Overuse",
                        severity=IssueSeverity.MEDIUM,
                        evidence={
                            "tool": top.tool_name,
                            "calls": top.call_count,
                            "pct_of_total_calls": top.percentage,
                            "total_calls": tool_analysis.total_calls,
                        },
                        recommendation=(
                            f"'{top.tool_name}' accounts for {top.percentage:.0f}% of all tool "
                            "calls. Introduce result caching keyed on input arguments. If repeated "
                            "queries are slightly different, improve the planning step to formulate "
                            "a single comprehensive query rather than iterating."
                        ),
                        category="tool",
                    )
                )

        # Unused tools in registry
        if tool_analysis.unused_tools:
            recommendations.append(
                Recommendation(
                    issue="Unused Tools in Registry",
                    severity=IssueSeverity.LOW,
                    evidence={
                        "unused_tools": tool_analysis.unused_tools,
                        "unused_count": len(tool_analysis.unused_tools),
                    },
                    recommendation=(
                        "Remove unused tools from the agent's tool registry to reduce prompt size "
                        "and lower the chance of hallucinated or confused tool selection. "
                        "Each extra tool description consumes tokens on every LLM call."
                    ),
                    category="tool",
                )
            )

        return recommendations


class RecommendationEngine:
    """
    Orchestrates all recommendation generators.
    Call `.generate()` with the full set of analysis results.
    Returns a deduplicated, severity-sorted list of Recommendation objects.
    """

    SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

    def __init__(self) -> None:
        self._loop = LoopRecommendationGenerator()
        self._hallucination = HallucinationRecommendationGenerator()
        self._redundancy = RedundancyRecommendationGenerator()
        self._cost = CostConcentrationRecommendationGenerator()
        self._tool = ToolInefficiencyRecommendationGenerator()

    def generate(
        self,
        loops: list[LoopEvent],
        hallucination: HallucinationResult,
        redundancy: RedundancyResult,
        cost: CostAnalysisResult,
        tool_analysis: ToolAnalysisResult,
    ) -> list[Recommendation]:
        all_recs: list[Recommendation] = []
        all_recs.extend(self._loop.generate(loops))
        all_recs.extend(self._hallucination.generate(hallucination))
        all_recs.extend(self._redundancy.generate(redundancy))
        all_recs.extend(self._cost.generate(cost))
        all_recs.extend(self._tool.generate(tool_analysis))

        all_recs.sort(
            key=lambda r: self.SEVERITY_ORDER.index(r.severity.value)
            if r.severity.value in self.SEVERITY_ORDER
            else len(self.SEVERITY_ORDER)
        )
        return all_recs
