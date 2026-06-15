from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models.report import CausalAnalysis, LangGraphAnalysisResult, LoopEvent
from app.models.trace import NormalizedTrace, RunStatus, StepType, TraceStep


class CausalTracer:
    """
    Deterministic backward causal tracer.

    Design goals:
    - Zero LLM calls.
    - Lightweight heuristics only.
    - Stable and testable outputs.
    """

    def trace_root_cause(self, trace: NormalizedTrace, analysis_results: dict[str, Any] | None = None) -> CausalAnalysis:
        analysis_results = analysis_results or {}

        # Guard: successful runs do not emit causal traces.
        if trace.metadata.status == RunStatus.SUCCESS:
            return CausalAnalysis()

        loops: list[LoopEvent] = analysis_results.get("loops") or []
        langgraph_analysis: LangGraphAnalysisResult | None = analysis_results.get("langgraph_analysis")

        failure_step = self._identify_failure_step(trace)
        failure_step_index = failure_step.index if failure_step else None

        failure_path = self._failure_path(trace, failure_step_index)
        root_cause = self._root_cause_node(
            trace=trace,
            failure_step=failure_step,
            failure_path=failure_path,
            loops=loops,
            langgraph_analysis=langgraph_analysis,
        )

        node_metrics = self._aggregate_node_metrics(trace)

        return CausalAnalysis(
            root_cause_node=root_cause,
            failure_path=failure_path,
            node_metrics=node_metrics,
        )

    @staticmethod
    def _identify_failure_step(trace: NormalizedTrace) -> TraceStep | None:
        """
        Best-effort: find the last step that contains an explicit failure signal.
        """

        for step in reversed(trace.steps):
            if CausalTracer._step_has_exception(step):
                return step
        return trace.steps[-1] if trace.steps else None

    @staticmethod
    def _step_has_exception(step: TraceStep) -> bool:
        """
        Deterministic detection of failures from tool output / content.
        """

        def has_error_payload(value: Any) -> bool:
            if value is None:
                return False
            if isinstance(value, dict):
                for k in ("error", "exception", "traceback"):
                    if k in value and value.get(k):
                        return True
                status = str(value.get("status", "")).lower()
                if status in ("failure", "failed", "error"):
                    return True
                if value.get("ok") is False:
                    return True
                # Some parsers wrap tool output under {"content": <payload>}
                if "content" in value:
                    return has_error_payload(value.get("content"))
                return False
            if isinstance(value, str):
                text = value.lower()
                return any(token in text for token in ("traceback", "exception", "validationerror", "error:"))
            return False

        if step.type in (StepType.TOOL_RESULT, StepType.TOOL_CALL):
            if has_error_payload(step.tool_output):
                return True
            if has_error_payload(step.tool_input):
                return True

        return has_error_payload(step.content)

    @staticmethod
    def _failure_path(trace: NormalizedTrace, failure_step_index: int | None) -> list[str]:
        """
        Sequential list of node transitions leading up to the failure.
        """

        transitions = [
            s
            for s in trace.steps
            if s.type == StepType.STATE_TRANSITION and s.state_from and s.state_to
        ]

        if transitions:
            # Only include transitions up to the failure step when a failure step exists.
            relevant = (
                [t for t in transitions if failure_step_index is None or t.index <= failure_step_index]
                if transitions
                else []
            )
            if not relevant:
                return []
            seq = [relevant[0].state_from] + [t.state_to for t in relevant]
            return [s for s in seq if s]

        # Fallback: use inferred node_name sequence (stable, compressed).
        seq: list[str] = []
        for s in trace.steps:
            if failure_step_index is not None and s.index > failure_step_index:
                break
            if not s.node_name:
                continue
            if not seq or seq[-1] != s.node_name:
                seq.append(s.node_name)
        return seq

    def _root_cause_node(
        self,
        *,
        trace: NormalizedTrace,
        failure_step: TraceStep | None,
        failure_path: list[str],
        loops: list[LoopEvent],
        langgraph_analysis: LangGraphAnalysisResult | None,
    ) -> str | None:
        # 1) Infinite loop heuristic: prefer structural loop root when loops exist.
        loop_root = self._loop_root_cause(trace, loops, langgraph_analysis)
        if loop_root:
            return loop_root

        # 2) Validation -> empty payload shift.
        if failure_step and self._is_validation_failure(failure_step):
            prev_result = self._previous_tool_result(trace, failure_step.index)
            if prev_result and self._is_empty_payload(prev_result.tool_output):
                return self._step_node(prev_result) or (failure_path[-2] if len(failure_path) >= 2 else None)

        # 3) Default: failing node.
        if failure_step:
            return self._step_node(failure_step) or (failure_path[-1] if failure_path else None)
        return failure_path[-1] if failure_path else None

    @staticmethod
    def _loop_root_cause(
        trace: NormalizedTrace,
        loops: list[LoopEvent],
        langgraph_analysis: LangGraphAnalysisResult | None,
    ) -> str | None:
        # LangGraph state loops: use earliest transition's `state_from` as the branching root.
        if langgraph_analysis and langgraph_analysis.state_loops:
            earliest_idx = min((min(l.step_indices) for l in langgraph_analysis.state_loops if l.step_indices), default=None)
            if earliest_idx is not None:
                step = next((s for s in trace.steps if s.index == earliest_idx and s.type == StepType.STATE_TRANSITION), None)
                if step and step.state_from:
                    return step.state_from
                if step and step.state_to:
                    return step.state_to

        # Generic tool loops: find the first occurrence and take the nearest preceding transition's `state_from`.
        if loops:
            first_loop_step = min((min(e.step_indices) for e in loops if e.step_indices), default=None)
            if first_loop_step is None:
                return None

            prev_transition = None
            for s in trace.steps:
                if s.type == StepType.STATE_TRANSITION and s.index <= first_loop_step:
                    prev_transition = s
            if prev_transition and prev_transition.state_from:
                return prev_transition.state_from

            # Fallback: use node_name at loop start.
            loop_step = next((s for s in trace.steps if s.index == first_loop_step), None)
            return loop_step.node_name if loop_step else None

        return None

    @staticmethod
    def _is_validation_failure(step: TraceStep) -> bool:
        blob = ""
        if isinstance(step.content, str):
            blob += step.content
        if isinstance(step.tool_output, dict):
            blob += " " + str(step.tool_output)
        blob = blob.lower()
        return any(token in blob for token in ("validationerror", "validation error", "pydantic", "schema"))

    @staticmethod
    def _is_empty_payload(payload: Any) -> bool:
        if payload is None:
            return True
        if isinstance(payload, dict):
            if not payload:
                return True
            if "content" in payload:
                return CausalTracer._is_empty_payload(payload.get("content"))
            return False
        if isinstance(payload, str):
            return payload.strip() in ("", "null", "none", "{}", "[]")
        return False

    @staticmethod
    def _previous_step(trace: NormalizedTrace, index: int) -> TraceStep | None:
        prev: TraceStep | None = None
        for s in trace.steps:
            if s.index >= index:
                break
            prev = s
        return prev

    @staticmethod
    def _previous_tool_result(trace: NormalizedTrace, index: int) -> TraceStep | None:
        prev: TraceStep | None = None
        for s in trace.steps:
            if s.index >= index:
                break
            if s.type == StepType.TOOL_RESULT:
                prev = s
        return prev

    @staticmethod
    def _step_node(step: TraceStep) -> str | None:
        if step.node_name:
            return step.node_name
        if step.type == StepType.STATE_TRANSITION and step.state_to:
            return step.state_to
        return None

    @staticmethod
    def _aggregate_node_metrics(trace: NormalizedTrace) -> dict[str, dict[str, float]]:
        duration_by_node: dict[str, float] = defaultdict(float)
        cost_by_node: dict[str, float] = defaultdict(float)

        for step in trace.steps:
            node = step.node_name
            if not node:
                continue
            cost_by_node[node] += float(step.cost_usd or 0.0)
            if step.duration_ms is not None:
                duration_by_node[node] += float(step.duration_ms)

        node_metrics: dict[str, dict[str, float]] = {}
        for node in sorted(set(duration_by_node) | set(cost_by_node)):
            node_metrics[node] = {
                "duration_ms": round(duration_by_node.get(node, 0.0), 2),
                "cost_usd": round(cost_by_node.get(node, 0.0), 6),
            }
        return node_metrics
