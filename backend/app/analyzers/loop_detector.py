import networkx as nx

from app.models.report import Issue, IssueCategory, IssueSeverity, LoopEvent
from app.models.trace import NormalizedTrace, StepType


class LoopDetector:
    CONSECUTIVE_THRESHOLD = 3

    def analyze(self, trace: NormalizedTrace) -> tuple[list[LoopEvent], list[Issue]]:
        events: list[LoopEvent] = []
        issues: list[Issue] = []

        consecutive = self._detect_consecutive(trace)
        events.extend(consecutive)

        cyclic = self._detect_cyclic_states(trace)
        events.extend(cyclic)

        for event in events:
            severity = event.severity
            if event.consecutive_count >= 5:
                severity = IssueSeverity.CRITICAL
            elif event.consecutive_count >= 3:
                severity = IssueSeverity.HIGH

            title = (
                f"Potential infinite loop: {event.tool_name or 'state cycle'}"
                if event.pattern_type == "consecutive"
                else f"Cyclic workflow pattern detected"
            )
            issues.append(
                Issue(
                    category=IssueCategory.LOOP,
                    severity=severity,
                    title=title,
                    description=(
                        f"{event.consecutive_count} consecutive identical "
                        f"{'tool calls' if event.tool_name else 'state transitions'} "
                        f"detected at steps {event.step_indices}"
                    ),
                    affected_steps=event.step_indices,
                    metric_value=float(event.consecutive_count),
                )
            )

        return events, issues

    def _detect_consecutive(self, trace: NormalizedTrace) -> list[LoopEvent]:
        events: list[LoopEvent] = []
        tool_calls = trace.tool_calls
        if len(tool_calls) < self.CONSECUTIVE_THRESHOLD:
            return events

        current_name: str | None = None
        current_indices: list[int] = []

        for step in tool_calls:
            if step.tool_name == current_name:
                current_indices.append(step.index)
            else:
                if len(current_indices) >= self.CONSECUTIVE_THRESHOLD:
                    events.append(
                        LoopEvent(
                            tool_name=current_name,
                            consecutive_count=len(current_indices),
                            step_indices=current_indices.copy(),
                            pattern_type="consecutive",
                            severity=IssueSeverity.HIGH,
                        )
                    )
                current_name = step.tool_name
                current_indices = [step.index]

        if len(current_indices) >= self.CONSECUTIVE_THRESHOLD:
            events.append(
                LoopEvent(
                    tool_name=current_name,
                    consecutive_count=len(current_indices),
                    step_indices=current_indices.copy(),
                    pattern_type="consecutive",
                    severity=IssueSeverity.HIGH,
                )
            )

        return events

    def _detect_cyclic_states(self, trace: NormalizedTrace) -> list[LoopEvent]:
        events: list[LoopEvent] = []
        transitions = trace.state_transitions
        if len(transitions) < 2:
            return events

        G = nx.DiGraph()
        for step in transitions:
            if step.state_from and step.state_to:
                G.add_edge(step.state_from, step.state_to)

        try:
            cycles: list[list[str]] = []
            for cycle in nx.simple_cycles(G, length_bound=10):
                cycles.append(cycle)
                if len(cycles) >= 20:
                    break
        except nx.NetworkXError:
            return events

        for cycle in cycles:
            if len(cycle) >= 2:
                affected = [
                    s.index
                    for s in transitions
                    if s.state_from in cycle or s.state_to in cycle
                ]
                events.append(
                    LoopEvent(
                        tool_name=None,
                        consecutive_count=len(cycle),
                        step_indices=affected,
                        pattern_type="cyclic",
                        severity=IssueSeverity.MEDIUM,
                    )
                )

        return events

    def get_loop_step_indices(self, events: list[LoopEvent]) -> set[int]:
        indices: set[int] = set()
        for event in events:
            indices.update(event.step_indices)
        return indices
