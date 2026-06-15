from app.models.report import HallucinationResult, Issue, IssueCategory, IssueSeverity
from app.models.trace import NormalizedTrace


class HallucinationDetector:
    def analyze(self, trace: NormalizedTrace) -> tuple[HallucinationResult, list[Issue]]:
        issues: list[Issue] = []
        available = trace.available_tool_names

        if not available:
            return (
                HallucinationResult(
                    hallucinated_tools=[],
                    affected_steps=[],
                    detected=False,
                ),
                issues,
            )

        called_tools: dict[str, list[int]] = {}
        for step in trace.tool_calls:
            name = step.tool_name or "unknown"
            called_tools.setdefault(name, []).append(step.index)

        hallucinated = [name for name in called_tools if name not in available]
        affected: list[int] = []
        for name in hallucinated:
            affected.extend(called_tools[name])

        result = HallucinationResult(
            hallucinated_tools=hallucinated,
            affected_steps=affected,
            detected=len(hallucinated) > 0,
        )

        if hallucinated:
            issues.append(
                Issue(
                    category=IssueCategory.HALLUCINATION,
                    severity=IssueSeverity.CRITICAL,
                    title="Hallucinated tool usage detected",
                    description=(
                        f"Agent attempted to call tools not in the registry: "
                        f"{', '.join(hallucinated)}. "
                        f"Available tools: {', '.join(sorted(available))}."
                    ),
                    affected_steps=affected,
                )
            )

        return result, issues
