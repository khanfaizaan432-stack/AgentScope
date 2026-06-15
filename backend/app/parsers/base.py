from abc import ABC, abstractmethod
from typing import Any

from app.models.trace import (
    NormalizedTrace,
    Stage,
    StepType,
    TokenUsage,
    TraceMetadata,
    TraceStep,
)


class BaseParser(ABC):
    @abstractmethod
    def parse(self, raw: dict[str, Any]) -> NormalizedTrace:
        pass

    @staticmethod
    def _estimate_tokens(text: str) -> TokenUsage:
        char_count = len(text)
        completion = max(char_count // 4, 1)
        return TokenUsage(prompt=0, completion=completion)

    @staticmethod
    def _infer_stage(step_type: StepType, tool_name: str | None = None) -> Stage:
        if step_type == StepType.THOUGHT:
            return Stage.PLANNING
        if step_type == StepType.TOOL_CALL and tool_name:
            name_lower = tool_name.lower()
            if any(kw in name_lower for kw in ("search", "retrieve", "fetch", "query")):
                return Stage.RETRIEVAL
            return Stage.EXECUTION
        if step_type == StepType.TOOL_RESULT:
            return Stage.EXECUTION
        return Stage.UNKNOWN
