from app.models.report import (
    GraphEdge,
    GraphNode,
    HealthReport,
    TimelineEdge,
    TimelineNode,
    WorkflowGraph,
)
from app.models.trace import NormalizedTrace, RunStatus, StepType


class HealthScorer:
    WEIGHTS = {
        "loop_penalty": 25,
        "redundancy_penalty": 20,
        "cost_penalty": 15,
        "tool_penalty": 15,
        "hallucination_penalty": 15,
        "completion_bonus": 10,
    }

    def score(
        self,
        trace: NormalizedTrace,
        loop_count: int,
        redundancy_score: float,
        cost_concentration: float,
        tool_inefficiency: float,
        hallucination_count: int,
    ) -> HealthReport:
        factors: dict[str, float] = {}

        loop_penalty = min(loop_count * 8, self.WEIGHTS["loop_penalty"])
        factors["loop_penalty"] = -loop_penalty

        redundancy_penalty = min(
            redundancy_score / 100 * self.WEIGHTS["redundancy_penalty"],
            self.WEIGHTS["redundancy_penalty"],
        )
        factors["redundancy_penalty"] = -round(redundancy_penalty, 1)

        cost_penalty = min(
            cost_concentration * self.WEIGHTS["cost_penalty"],
            self.WEIGHTS["cost_penalty"],
        )
        factors["cost_penalty"] = -round(cost_penalty, 1)

        tool_penalty = min(
            tool_inefficiency * self.WEIGHTS["tool_penalty"],
            self.WEIGHTS["tool_penalty"],
        )
        factors["tool_penalty"] = -round(tool_penalty, 1)

        hallucination_penalty = min(
            hallucination_count * 10,
            self.WEIGHTS["hallucination_penalty"],
        )
        factors["hallucination_penalty"] = -hallucination_penalty

        completion_bonus = 0.0
        if trace.metadata.status == RunStatus.SUCCESS:
            completion_bonus = self.WEIGHTS["completion_bonus"]
        factors["completion_bonus"] = completion_bonus

        raw_score = 100 + sum(factors.values())
        final_score = max(0, min(100, round(raw_score)))

        grade = self._grade(final_score)
        strengths = self._identify_strengths(
            trace, loop_count, redundancy_score, hallucination_count
        )
        summary = self._build_summary(final_score, loop_count, redundancy_score, hallucination_count)

        return HealthReport(
            score=final_score,
            grade=grade,
            factors=factors,
            strengths=strengths,
            summary=summary,
        )

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"

    @staticmethod
    def _identify_strengths(
        trace: NormalizedTrace,
        loop_count: int,
        redundancy_score: float,
        hallucination_count: int,
    ) -> list[str]:
        strengths: list[str] = []
        if trace.metadata.status == RunStatus.SUCCESS:
            strengths.append("Good task completion")
        if loop_count == 0:
            strengths.append("No infinite loops detected")
        if redundancy_score < 30:
            strengths.append("Efficient reasoning with low redundancy")
        if hallucination_count == 0:
            strengths.append("No hallucinated tools")
        if len(trace.tool_calls) > 0 and len(trace.tool_calls) <= 10:
            strengths.append("Reasonable tool call count")
        if not strengths:
            strengths.append("Trace successfully parsed and analyzed")
        return strengths

    @staticmethod
    def _build_summary(
        score: int, loop_count: int, redundancy_score: float, hallucination_count: int
    ) -> str:
        parts = [f"Agent health score: {score}/100."]
        if loop_count > 0:
            parts.append(f"{loop_count} loop pattern(s) detected.")
        if redundancy_score >= 50:
            parts.append(f"High reasoning redundancy ({redundancy_score:.0f}%).")
        if hallucination_count > 0:
            parts.append(f"{hallucination_count} hallucinated tool(s) found.")
        if score >= 80:
            parts.append("Overall agent performance is healthy.")
        elif score >= 60:
            parts.append("Agent performance has room for improvement.")
        else:
            parts.append("Agent performance needs significant optimization.")
        return " ".join(parts)


class GraphBuilder:
    def build_timeline(
        self, trace: NormalizedTrace, loop_indices: set[int]
    ) -> tuple[list[TimelineNode], list[TimelineEdge]]:
        nodes: list[TimelineNode] = []
        edges: list[TimelineEdge] = []

        for step in trace.steps:
            node_id = f"step-{step.index}"
            label = self._step_label(step)
            nodes.append(
                TimelineNode(
                    id=node_id,
                    step_index=step.index,
                    type=step.type.value,
                    label=label,
                    stage=step.stage.value,
                    is_loop=step.index in loop_indices,
                )
            )

        for i in range(len(nodes) - 1):
            edges.append(
                TimelineEdge(source=nodes[i].id, target=nodes[i + 1].id)
            )

        return nodes, edges

    def build_workflow_graph(
        self, trace: NormalizedTrace, loop_indices: set[int]
    ) -> WorkflowGraph:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_tools: dict[str, str] = {}

        for step in trace.steps:
            if step.type == StepType.THOUGHT:
                node_id = f"thought-{step.index}"
                nodes.append(
                    GraphNode(
                        id=node_id,
                        label=step.content[:60] + ("..." if len(step.content) > 60 else ""),
                        node_type="thought",
                        is_loop=step.index in loop_indices,
                        step_index=step.index,
                    )
                )
            elif step.type == StepType.TOOL_CALL:
                tool_name = step.tool_name or "unknown"
                node_id = f"tool-{step.index}"
                seen_tools[tool_name] = node_id
                nodes.append(
                    GraphNode(
                        id=node_id,
                        label=tool_name,
                        node_type="tool",
                        is_loop=step.index in loop_indices,
                        step_index=step.index,
                    )
                )

        prev_id: str | None = None
        for step in trace.steps:
            if step.type in (StepType.THOUGHT, StepType.TOOL_CALL):
                node_id = (
                    f"thought-{step.index}"
                    if step.type == StepType.THOUGHT
                    else f"tool-{step.index}"
                )
                if prev_id:
                    edges.append(
                        GraphEdge(
                            id=f"edge-{prev_id}-{node_id}",
                            source=prev_id,
                            target=node_id,
                            is_loop=step.index in loop_indices,
                        )
                    )
                prev_id = node_id

        return WorkflowGraph(nodes=nodes, edges=edges)

    @staticmethod
    def _step_label(step) -> str:
        if step.type == StepType.THOUGHT:
            text = step.content[:50]
            return text + ("..." if len(step.content) > 50 else "")
        if step.type == StepType.TOOL_CALL:
            return f"Call: {step.tool_name}"
        if step.type == StepType.TOOL_RESULT:
            return f"Result: {step.tool_name}"
        if step.type == StepType.STATE_TRANSITION:
            return f"{step.state_from} → {step.state_to}"
        return step.type.value
