from app.models.report import CostAnalysisResult, Issue, IssueCategory, IssueSeverity, StepCost
from app.models.trace import NormalizedTrace


class CostAnalyzer:
    EXPENSIVE_STEP_THRESHOLD = 0.25

    def analyze(self, trace: NormalizedTrace) -> tuple[CostAnalysisResult, list[Issue]]:
        issues: list[Issue] = []
        per_step: list[StepCost] = []
        cost_by_stage: dict[str, float] = {}

        total_prompt = 0
        total_completion = 0
        total_cost = 0.0

        for step in trace.steps:
            total_prompt += step.tokens.prompt
            total_completion += step.tokens.completion
            total_cost += step.cost_usd

            stage = step.stage.value
            cost_by_stage[stage] = cost_by_stage.get(stage, 0.0) + step.cost_usd

        for step in trace.steps:
            pct = (step.cost_usd / total_cost * 100) if total_cost > 0 else 0
            per_step.append(
                StepCost(
                    step_index=step.index,
                    stage=step.stage.value,
                    prompt_tokens=step.tokens.prompt,
                    completion_tokens=step.tokens.completion,
                    cost_usd=round(step.cost_usd, 6),
                    percentage=round(pct, 1),
                )
            )

        most_expensive = max(per_step, key=lambda s: s.cost_usd) if per_step else None

        result = CostAnalysisResult(
            total_prompt_tokens=total_prompt,
            total_completion_tokens=total_completion,
            total_tokens=total_prompt + total_completion,
            total_cost_usd=round(total_cost, 6),
            per_step=per_step,
            cost_by_stage={k: round(v, 6) for k, v in cost_by_stage.items()},
            most_expensive_step=most_expensive,
        )

        if most_expensive and most_expensive.percentage > self.EXPENSIVE_STEP_THRESHOLD * 100:
            issues.append(
                Issue(
                    category=IssueCategory.COST,
                    severity=IssueSeverity.MEDIUM,
                    title=f"Cost concentration at step {most_expensive.step_index}",
                    description=(
                        f"Step {most_expensive.step_index} ({most_expensive.stage}) "
                        f"consumed {most_expensive.percentage:.0f}% of total run cost."
                    ),
                    affected_steps=[most_expensive.step_index],
                    metric_value=most_expensive.percentage,
                )
            )

        planning_cost = cost_by_stage.get("planning", 0.0)
        if total_cost > 0 and planning_cost / total_cost > 0.4:
            issues.append(
                Issue(
                    category=IssueCategory.COST,
                    severity=IssueSeverity.LOW,
                    title="Cost concentration in planning phase",
                    description=(
                        f"Planning phase consumed {planning_cost / total_cost:.0%} "
                        f"of total token cost. Consider reducing redundant planning."
                    ),
                    metric_value=planning_cost / total_cost,
                )
            )

        return result, issues
