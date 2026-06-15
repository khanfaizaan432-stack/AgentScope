from app.models.report import Issue, IssueCategory, IssueSeverity, ToolAnalysisResult, ToolUsageStats
from app.models.trace import NormalizedTrace


class ToolAnalyzer:
    INEFFICIENCY_THRESHOLD = 0.5

    def analyze(self, trace: NormalizedTrace) -> tuple[ToolAnalysisResult, list[Issue]]:
        issues: list[Issue] = []
        tool_calls = trace.tool_calls
        total = len(tool_calls)

        counts: dict[str, int] = {}
        for step in tool_calls:
            name = step.tool_name or "unknown"
            counts[name] = counts.get(name, 0) + 1

        per_tool: list[ToolUsageStats] = []
        for name, count in sorted(counts.items(), key=lambda x: -x[1]):
            per_tool.append(
                ToolUsageStats(
                    tool_name=name,
                    call_count=count,
                    percentage=round(count / total * 100, 1) if total > 0 else 0,
                )
            )

        most_used = per_tool[0].tool_name if per_tool else None
        least_used = per_tool[-1].tool_name if per_tool else None

        called_names = set(counts.keys())
        available_names = trace.available_tool_names
        unused = list(available_names - called_names) if available_names else []

        result = ToolAnalysisResult(
            total_calls=total,
            unique_tools=len(counts),
            per_tool=per_tool,
            most_used=most_used,
            least_used=least_used,
            unused_tools=unused,
        )

        if most_used and total > 0:
            top_pct = counts[most_used] / total
            if top_pct > self.INEFFICIENCY_THRESHOLD and counts[most_used] >= 3:
                issues.append(
                    Issue(
                        category=IssueCategory.TOOL,
                        severity=IssueSeverity.MEDIUM,
                        title=f"Tool usage inefficiency: {most_used}",
                        description=(
                            f"{most_used} accounts for {top_pct:.0%} of all tool calls "
                            f"({counts[most_used]}/{total}). Consider caching or deduplication."
                        ),
                        metric_value=top_pct,
                    )
                )

        if unused:
            issues.append(
                Issue(
                    category=IssueCategory.TOOL,
                    severity=IssueSeverity.LOW,
                    title="Unused tools in registry",
                    description=f"Tools declared but never called: {', '.join(unused)}",
                )
            )

        return result, issues
