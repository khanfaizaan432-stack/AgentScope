from app.analyzers.text_similarity import _tfidf_vectors, combined_similarity
from app.models.report import Issue, IssueCategory, IssueSeverity, RedundancyPair, RedundancyResult
from app.models.trace import NormalizedTrace


class RedundancyAnalyzer:
    SIMILARITY_THRESHOLD = 0.55

    def analyze(self, trace: NormalizedTrace) -> tuple[RedundancyResult, list[Issue]]:
        issues: list[Issue] = []
        thoughts = trace.thoughts

        if len(thoughts) < 2:
            return (
                RedundancyResult(
                    redundancy_score=0.0,
                    redundant_pairs=[],
                    total_thoughts=len(thoughts),
                    redundant_thought_count=0,
                ),
                issues,
            )

        texts = [t.content for t in thoughts]
        vectors = _tfidf_vectors(texts)

        pairs: list[RedundancyPair] = []
        redundant_indices: set[int] = set()

        for i in range(len(thoughts) - 1):
            sim = combined_similarity(texts[i], texts[i + 1], vectors[i], vectors[i + 1])
            if sim >= self.SIMILARITY_THRESHOLD:
                pairs.append(
                    RedundancyPair(
                        step_a=thoughts[i].index,
                        step_b=thoughts[i + 1].index,
                        similarity=round(sim, 3),
                        content_a=thoughts[i].content[:100],
                        content_b=thoughts[i + 1].content[:100],
                    )
                )
                redundant_indices.add(thoughts[i].index)
                redundant_indices.add(thoughts[i + 1].index)

        redundancy_score = (
            round(len(redundant_indices) / len(thoughts) * 100, 1) if thoughts else 0.0
        )

        result = RedundancyResult(
            redundancy_score=redundancy_score,
            redundant_pairs=pairs,
            total_thoughts=len(thoughts),
            redundant_thought_count=len(redundant_indices),
        )

        if redundancy_score >= 50:
            severity = IssueSeverity.HIGH if redundancy_score >= 75 else IssueSeverity.MEDIUM
            issues.append(
                Issue(
                    category=IssueCategory.REDUNDANCY,
                    severity=severity,
                    title="Reasoning redundancy detected",
                    description=(
                        f"Reasoning redundancy = {redundancy_score:.0f}%. "
                        f"{len(pairs)} adjacent thought pairs exceed "
                        f"{self.SIMILARITY_THRESHOLD:.0%} similarity. "
                        f"Possible planning loop."
                    ),
                    affected_steps=list(redundant_indices),
                    metric_value=redundancy_score,
                )
            )

        return result, issues
