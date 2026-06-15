from __future__ import annotations

from collections import Counter, defaultdict

from app.models.report import (
    Issue,
    IssueCategory,
    IssueSeverity,
    LangGraphAnalysisResult,
    LangGraphBranchAnalysis,
    LangGraphNodeBottleneck,
    LangGraphStateLoop,
)
from app.models.trace import NormalizedTrace, StepType, TraceStep


class LangGraphAnalyzer:
    """
    LangGraph-specific analysis that builds on the existing NormalizedTrace model.

    This analyzer is intentionally deterministic and rule-based.
    """

    MAX_CYCLE_LENGTH = 6
    MIN_REPETITIONS = 2

    def analyze(self, trace: NormalizedTrace) -> tuple[LangGraphAnalysisResult, list[Issue]]:
        issues: list[Issue] = []

        state_loops = self._detect_state_loops(trace)
        for loop in state_loops:
            issues.append(self._loop_issue(loop))

        branch_analysis = self._branch_analysis(trace)
        bottlenecks = self._bottleneck_analysis(trace)

        return (
            LangGraphAnalysisResult(
                state_loops=state_loops,
                branches=branch_analysis,
                bottlenecks=bottlenecks,
            ),
            issues,
        )

    def _detect_state_loops(self, trace: NormalizedTrace) -> list[LangGraphStateLoop]:
        transitions = [
            s
            for s in trace.steps
            if s.type == StepType.STATE_TRANSITION and s.state_from and s.state_to
        ]
        if len(transitions) < 4:
            return []

        # Work on an explicit state sequence so the reported repeated states match
        # patterns like: Planner → Search → Planner → Search (ABAB).
        state_sequence = [transitions[0].state_from or ""] + [t.state_to or "" for t in transitions]
        results: list[LangGraphStateLoop] = []
        n = len(state_sequence)
        cursor = 0

        while cursor < n:
            matched = False
            max_cycle_len = min(self.MAX_CYCLE_LENGTH, n - cursor)
            for cycle_len in range(2, max_cycle_len + 1):
                if cursor + cycle_len * 2 > n:
                    continue

                pattern = state_sequence[cursor : cursor + cycle_len]
                if len(set(pattern)) < 2:
                    continue

                next_window = state_sequence[cursor + cycle_len : cursor + cycle_len * 2]
                if next_window != pattern:
                    continue

                repetitions = 2
                next_pos = cursor + cycle_len * 2
                while next_pos + cycle_len <= n and state_sequence[next_pos : next_pos + cycle_len] == pattern:
                    repetitions += 1
                    next_pos += cycle_len

                end_transition_exclusive = min(max(0, next_pos - 1), len(transitions))
                affected_transition_indices = list(range(cursor, end_transition_exclusive))
                affected_step_indices = [transitions[i].index for i in affected_transition_indices]

                severity = IssueSeverity.MEDIUM
                if repetitions >= 4:
                    severity = IssueSeverity.HIGH
                if repetitions >= 6:
                    severity = IssueSeverity.CRITICAL

                results.append(
                    LangGraphStateLoop(
                        cycle_length=cycle_len,
                        repeated_states=pattern,
                        repetitions=repetitions,
                        step_indices=affected_step_indices,
                        severity=severity,
                    )
                )
                cursor = next_pos
                matched = True
                break

            if not matched:
                cursor += 1

        return results

    @staticmethod
    def _loop_issue(loop: LangGraphStateLoop) -> Issue:
        states = " → ".join(loop.repeated_states)
        title = f"LangGraph state loop detected (cycle length {loop.cycle_length})"
        description = (
            f"Repeated state sequence: {states}. "
            f"Repetitions: {loop.repetitions}. "
            f"Affected steps: {loop.step_indices}."
        )
        return Issue(
            category=IssueCategory.LOOP,
            severity=loop.severity,
            title=title,
            description=description,
            affected_steps=loop.step_indices,
            metric_value=float(loop.repetitions),
        )

    def _branch_analysis(self, trace: NormalizedTrace) -> LangGraphBranchAnalysis | None:
        transitions = [s for s in trace.steps if s.type == StepType.STATE_TRANSITION and s.state_from and s.state_to]
        if len(transitions) < 2:
            return None

        adjacency: dict[str, set[str]] = defaultdict(set)
        for t in transitions:
            adjacency[t.state_from or ""].add(t.state_to or "")

        branching_states = {state: next_states for state, next_states in adjacency.items() if len(next_states) > 1}
        explored_branches: set[tuple[str, str]] = set()
        for parent, children in branching_states.items():
            for child in children:
                explored_branches.add((parent, child))

        # Derive a conservative "depth" from the executed transition sequence.
        max_depth = 1
        current_depth = 1
        for i in range(1, len(transitions)):
            if transitions[i].state_from == transitions[i - 1].state_to:
                current_depth += 1
            else:
                current_depth = 1
            max_depth = max(max_depth, current_depth)

        # Define "successful branch option" as an explored branch edge (parent→child) that can reach
        # the final executed state in the explored adjacency graph.
        final_state = transitions[-1].state_to or ""

        def can_reach(start_state: str, target: str) -> bool:
            if start_state == target:
                return True
            stack = [start_state]
            visited: set[str] = set()
            while stack:
                cur = stack.pop()
                if cur in visited:
                    continue
                visited.add(cur)
                for nxt in adjacency.get(cur, set()):
                    if nxt == target:
                        return True
                    if nxt not in visited:
                        stack.append(nxt)
            return False

        successful = sum(1 for _p, child in explored_branches if can_reach(child, final_state))
        dead_end = max(0, len(explored_branches) - successful)

        summary = f"{len(explored_branches)} branches explored, {successful} successful"

        return LangGraphBranchAnalysis(
            branch_count=len(explored_branches),
            max_branch_depth=max_depth,
            dead_end_branches=dead_end,
            successful_branches=successful,
            summary=summary,
        )

    def _bottleneck_analysis(self, trace: NormalizedTrace) -> LangGraphNodeBottleneck | None:
        transitions = [s for s in trace.steps if s.type == StepType.STATE_TRANSITION and s.state_to]
        node_steps = [s for s in trace.steps if s.node_name]
        if not node_steps and not transitions:
            return None

        cost_by_node: dict[str, float] = defaultdict(float)
        duration_by_node: dict[str, float] = defaultdict(float)
        count_by_node: Counter[str] = Counter()

        for step in node_steps:
            node = step.node_name or "unknown"
            cost_by_node[node] += float(step.cost_usd or 0.0)
            if step.duration_ms is not None:
                duration_by_node[node] += float(step.duration_ms)

        # Count "node executions" based on state transitions when available.
        if transitions:
            for t in transitions:
                count_by_node[t.state_to or "unknown"] += 1
        else:
            for step in node_steps:
                count_by_node[step.node_name or "unknown"] += 1

        most_expensive_node = max(cost_by_node.items(), key=lambda kv: kv[1])[0] if cost_by_node else None
        most_expensive_cost = cost_by_node.get(most_expensive_node, 0.0) if most_expensive_node else 0.0

        slowest_node: str | None = None
        slowest_duration: float | None = None
        if duration_by_node:
            slowest_node = max(duration_by_node.items(), key=lambda kv: kv[1])[0]
            slowest_duration = duration_by_node.get(slowest_node)

        most_frequent_node = count_by_node.most_common(1)[0][0] if count_by_node else None
        most_frequent_count = count_by_node.get(most_frequent_node, 0) if most_frequent_node else 0

        return LangGraphNodeBottleneck(
            most_expensive_node=most_expensive_node,
            most_expensive_cost_usd=round(most_expensive_cost, 6),
            slowest_node=slowest_node,
            slowest_duration_ms=round(slowest_duration, 2) if slowest_duration is not None else None,
            most_frequent_node=most_frequent_node,
            most_frequent_count=most_frequent_count,
        )


def assign_node_context_from_transitions(steps: list[TraceStep]) -> list[TraceStep]:
    """
    Best-effort inference for LangGraph traces that only provide node transitions.

    We treat each STATE_TRANSITION's `state_to` as the current active node for subsequent steps
    until the next transition.
    """

    current: str | None = None
    for step in steps:
        if step.type == StepType.STATE_TRANSITION and step.state_to:
            current = step.state_to
            continue
        if current and step.node_name is None:
            step.node_name = current
    return steps
