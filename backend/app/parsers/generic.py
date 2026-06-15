from typing import Any

from app.models.trace import (
    NormalizedTrace,
    RunStatus,
    Stage,
    StepType,
    TokenUsage,
    ToolDefinition,
    TraceMetadata,
    TraceStep,
)
from app.parsers.base import BaseParser

PROMPT_COST_PER_M = 0.15
COMPLETION_COST_PER_M = 0.60


class GenericParser(BaseParser):
    def parse(self, raw: dict[str, Any]) -> NormalizedTrace:
        metadata_raw = raw.get("metadata", {})
        metadata = TraceMetadata(
            run_id=metadata_raw.get("run_id", "unknown"),
            framework=metadata_raw.get("framework", "generic"),
            started_at=metadata_raw.get("started_at"),
            completed_at=metadata_raw.get("completed_at"),
            status=RunStatus(metadata_raw.get("status", "unknown")),
            agent_name=metadata_raw.get("agent_name"),
        )

        tools = [
            ToolDefinition(name=t["name"], description=t.get("description", ""))
            for t in raw.get("available_tools", [])
        ]

        steps = []
        for i, s in enumerate(raw.get("steps", [])):
            tokens_raw = s.get("tokens", {})
            tokens = TokenUsage(
                prompt=tokens_raw.get("prompt", 0),
                completion=tokens_raw.get("completion", 0),
            )
            if tokens.total == 0 and s.get("content"):
                tokens = self._estimate_tokens(s["content"])

            cost = s.get("cost_usd", 0.0)
            if cost == 0.0 and tokens.total > 0:
                cost = (
                    tokens.prompt * PROMPT_COST_PER_M / 1_000_000
                    + tokens.completion * COMPLETION_COST_PER_M / 1_000_000
                )

            step_type = StepType(s.get("type", "thought"))
            tool_name = s.get("tool_name")
            stage_str = s.get("stage")
            stage = Stage(stage_str) if stage_str else self._infer_stage(step_type, tool_name)

            steps.append(
                TraceStep(
                    index=s.get("index", i),
                    type=step_type,
                    timestamp=s.get("timestamp"),
                    content=s.get("content", ""),
                    tool_name=tool_name,
                    tool_input=s.get("tool_input", {}),
                    tool_output=s.get("tool_output", {}),
                    state_from=s.get("state_from"),
                    state_to=s.get("state_to"),
                    tokens=tokens,
                    cost_usd=cost,
                    stage=stage,
                )
            )

        return NormalizedTrace(metadata=metadata, available_tools=tools, steps=steps)
