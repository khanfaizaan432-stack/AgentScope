from typing import Any

from app.models.trace import (
    NormalizedTrace,
    RunStatus,
    Stage,
    StepType,
    ToolDefinition,
    TraceMetadata,
    TraceStep,
)
from app.parsers.base import BaseParser


class CrewAIParser(BaseParser):
    def parse(self, raw: dict[str, Any]) -> NormalizedTrace:
        metadata_raw = raw.get("metadata", {})
        metadata = TraceMetadata(
            run_id=metadata_raw.get("run_id", "unknown"),
            framework="crewai",
            started_at=metadata_raw.get("started_at"),
            completed_at=metadata_raw.get("completed_at"),
            status=RunStatus(metadata_raw.get("status", "unknown")),
            agent_name=metadata_raw.get("agent_name"),
        )

        tools = [
            ToolDefinition(name=t["name"], description=t.get("description", ""))
            for t in raw.get("available_tools", [])
        ]

        steps: list[TraceStep] = []
        idx = 0

        for task in raw.get("tasks", []):
            agent = task.get("agent", "Agent")
            description = task.get("description", "")

            steps.append(
                TraceStep(
                    index=idx,
                    type=StepType.THOUGHT,
                    content=f"[{agent}] {description}",
                    stage=Stage.PLANNING,
                    tokens=self._estimate_tokens(description),
                )
            )
            idx += 1

            for tool_name in task.get("tools_used", []):
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.TOOL_CALL,
                        tool_name=tool_name,
                        stage=self._infer_stage(StepType.TOOL_CALL, tool_name),
                    )
                )
                idx += 1

                output = task.get("output", "")
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.TOOL_RESULT,
                        tool_name=tool_name,
                        tool_output={"output": output},
                        stage=Stage.EXECUTION,
                    )
                )
                idx += 1

        return NormalizedTrace(metadata=metadata, available_tools=tools, steps=steps)
