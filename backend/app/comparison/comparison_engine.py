from __future__ import annotations

from app.comparison.comparison_models import ComparisonReport, MetricDelta
from app.models.report import AnalysisReport


class ComparisonEngine:
    def compare_reports(self, report_a: AnalysisReport, report_b: AnalysisReport) -> ComparisonReport:
        score_delta = self._metric_delta(report_a.health.score, report_b.health.score)
        cost_delta = self._metric_delta(report_a.cost_analysis.total_cost_usd, report_b.cost_analysis.total_cost_usd)
        loop_delta = self._metric_delta(len(report_a.loops), len(report_b.loops))
        redundancy_delta = self._metric_delta(
            report_a.redundancy.redundancy_score,
            report_b.redundancy.redundancy_score,
        )
        hallucination_delta = self._metric_delta(
            len(report_a.hallucination.hallucinated_tools),
            len(report_b.hallucination.hallucinated_tools),
        )

        tokens_delta = report_b.cost_analysis.total_tokens - report_a.cost_analysis.total_tokens
        improvements: list[str] = []
        regressions: list[str] = []

        self._append_directional_message(
            improvements,
            regressions,
            "Looping reduced",
            "More loops detected",
            loop_delta.delta,
            lower_is_better=True,
            before=loop_delta.before,
            after=loop_delta.after,
        )
        self._append_percent_message(
            improvements,
            regressions,
            "Cost reduced",
            "Cost increased",
            cost_delta.delta,
            report_a.cost_analysis.total_cost_usd,
            report_b.cost_analysis.total_cost_usd,
            label="estimated cost",
        )
        self._append_directional_message(
            improvements,
            regressions,
            "Redundancy reduced",
            "Redundancy increased",
            redundancy_delta.delta,
            lower_is_better=True,
            before=redundancy_delta.before,
            after=redundancy_delta.after,
            suffix="%",
        )
        self._append_hallucination_message(
            improvements,
            regressions,
            hallucination_delta.before,
            hallucination_delta.after,
        )
        self._append_score_message(improvements, regressions, score_delta.delta)

        if tokens_delta < 0:
            improvements.append(
                self._token_efficiency_message(
                    report_a.cost_analysis.total_tokens,
                    report_b.cost_analysis.total_tokens,
                    improved=True,
                )
            )
        elif tokens_delta > 0:
            regressions.append(
                self._token_efficiency_message(
                    report_a.cost_analysis.total_tokens,
                    report_b.cost_analysis.total_tokens,
                    improved=False,
                )
            )

        verdict = self._build_verdict(
            score_delta,
            cost_delta,
            loop_delta,
            redundancy_delta,
            hallucination_delta,
            improvements,
            regressions,
        )

        return ComparisonReport(
            score_delta=score_delta,
            cost_delta=cost_delta,
            loop_delta=loop_delta,
            redundancy_delta=redundancy_delta,
            hallucination_delta=hallucination_delta,
            regressions=regressions,
            improvements=improvements,
            verdict=verdict,
        )

    @staticmethod
    def _metric_delta(before: float | int, after: float | int) -> MetricDelta:
        return MetricDelta(before=before, after=after, delta=round(float(after) - float(before), 2))

    @staticmethod
    def _percentage_change(before: float | int, after: float | int) -> float | None:
        if before == 0:
            return None
        return round(((float(after) - float(before)) / float(before)) * 100, 1)

    def _append_score_message(self, improvements: list[str], regressions: list[str], delta: float) -> None:
        if delta > 0:
            improvements.append(f"Health score improved by {self._format_signed(delta)} points")
        elif delta < 0:
            regressions.append(f"Health score declined by {self._format_signed(abs(delta))} points")

    def _append_directional_message(
        self,
        improvements: list[str],
        regressions: list[str],
        improvement_message: str,
        regression_message: str,
        delta: float,
        *,
        lower_is_better: bool,
        before: float | int,
        after: float | int,
        suffix: str = "",
    ) -> None:
        if delta == 0:
            return

        target = improvements if (delta < 0 if lower_is_better else delta > 0) else regressions
        percentage = self._percentage_change(before, after)
        message = improvement_message if target is improvements else regression_message
        if percentage is None:
            target.append(message)
            return

        target.append(f"{message}: {abs(percentage)}{suffix}")

    def _append_percent_message(
        self,
        improvements: list[str],
        regressions: list[str],
        improvement_message: str,
        regression_message: str,
        delta: float,
        before: float | int,
        after: float | int,
        *,
        label: str,
    ) -> None:
        if delta == 0:
            return

        percentage = self._percentage_change(before, after)
        if delta < 0:
            if percentage is None:
                improvements.append(improvement_message)
            else:
                improvements.append(f"{improvement_message}: {abs(percentage)}% lower {label}")
        else:
            if percentage is None:
                regressions.append(regression_message)
            else:
                regressions.append(f"{regression_message}: {abs(percentage)}% higher {label}")

    def _append_hallucination_message(
        self,
        improvements: list[str],
        regressions: list[str],
        before: float | int,
        after: float | int,
    ) -> None:
        if before > 0 and after == 0:
            improvements.append("Hallucinations eliminated")
        elif before == 0 and after > 0:
            regressions.append("New hallucinated tools appeared")
        elif after > before:
            regressions.append("Hallucinations increased")
        elif after < before:
            improvements.append("Hallucinations decreased")

    @staticmethod
    def _token_efficiency_message(before: int, after: int, *, improved: bool) -> str:
        if improved:
            return f"Tool efficiency improved: tokens dropped from {before} to {after}"
        return f"Tool efficiency regressed: tokens increased from {before} to {after}"

    @staticmethod
    def _format_signed(value: float) -> str:
        if float(value).is_integer():
            return f"{int(value):+d}"
        return f"{value:+.2f}"

    def _build_verdict(
        self,
        score_delta: MetricDelta,
        cost_delta: MetricDelta,
        loop_delta: MetricDelta,
        redundancy_delta: MetricDelta,
        hallucination_delta: MetricDelta,
        improvements: list[str],
        regressions: list[str],
    ) -> str:
        score_improved = score_delta.delta > 0
        score_regressed = score_delta.delta < 0
        cost_improved = cost_delta.delta < 0
        cost_regressed = cost_delta.delta > 0
        loops_improved = loop_delta.delta < 0
        loops_regressed = loop_delta.delta > 0
        redundancy_improved = redundancy_delta.delta < 0
        redundancy_regressed = redundancy_delta.delta > 0
        hallucinations_improved = hallucination_delta.before > 0 and hallucination_delta.after == 0
        hallucinations_regressed = hallucination_delta.before == 0 and hallucination_delta.after > 0

        strong_improvement = score_delta.delta >= 10 and cost_improved and loops_improved and not hallucinations_regressed
        serious_regression = score_regressed or cost_regressed or hallucinations_regressed
        balanced_improvement = score_improved and (cost_improved or loops_improved or redundancy_improved or hallucinations_improved)
        balanced_regression = score_regressed and (cost_regressed or loops_regressed or redundancy_regressed or hallucinations_regressed)

        if strong_improvement and not regressions:
            return "Major Improvement"
        if serious_regression and not improvements:
            return "Regression Detected"
        if strong_improvement and regressions:
            return "Major Improvement"
        if balanced_improvement and regressions:
            return "Mixed Results"
        if balanced_regression and improvements:
            return "Mixed Results"
        if improvements and regressions:
            return "Mixed Results"
        if improvements:
            return "Major Improvement" if score_improved else "Improvement"
        if regressions:
            return "Regression Detected"
        return "No Significant Change"