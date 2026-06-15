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


class LangGraphParser(BaseParser):
    def parse(self, raw: dict[str, Any]) -> NormalizedTrace:
        metadata_raw = raw.get("metadata", {})
        metadata = TraceMetadata(
            run_id=metadata_raw.get("run_id", "unknown"),
            framework="langgraph",
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

        for msg in raw.get("messages", []):
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "assistant":
                if content:
                    steps.append(
                        TraceStep(
                            index=idx,
                            type=StepType.THOUGHT,
                            content=content if isinstance(content, str) else str(content),
                            stage=Stage.PLANNING,
                            tokens=self._estimate_tokens(
                                content if isinstance(content, str) else str(content)
                            ),
                        )
                    )
                    idx += 1

                for tc in msg.get("tool_calls", []):
                    fn = tc.get("function", tc)
                    tool_name = fn.get("name", "unknown")
                    steps.append(
                        TraceStep(
                            index=idx,
                            type=StepType.TOOL_CALL,
                            tool_name=tool_name,
                            tool_input=fn.get("arguments", {}),
                            stage=self._infer_stage(StepType.TOOL_CALL, tool_name),
                        )
                    )
                    idx += 1

            elif role == "tool":
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.TOOL_RESULT,
                        tool_name=msg.get("name", "unknown"),
                        tool_output={"content": content},
                        stage=Stage.EXECUTION,
                    )
                )
                idx += 1

        for trans in raw.get("node_transitions", []):
            steps.append(
                TraceStep(
                    index=idx,
                    type=StepType.STATE_TRANSITION,
                    state_from=trans.get("from", ""),
                    state_to=trans.get("to", ""),
                    content=f"{trans.get('from')} → {trans.get('to')}",
                    stage=Stage.UNKNOWN,
                )
            )
            idx += 1

        return NormalizedTrace(metadata=metadata, available_tools=tools, steps=steps)
