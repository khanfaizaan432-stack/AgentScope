from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepType(str, Enum):
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    STATE_TRANSITION = "state_transition"


class Stage(str, Enum):
    PLANNING = "planning"
    EXECUTION = "execution"
    RETRIEVAL = "retrieval"
    SYNTHESIS = "synthesis"
    UNKNOWN = "unknown"


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class TokenUsage(BaseModel):
    prompt: int = 0
    completion: int = 0

    @property
    def total(self) -> int:
        return self.prompt + self.completion


class ToolDefinition(BaseModel):
    name: str
    description: str = ""


class TraceStep(BaseModel):
    index: int
    type: StepType
    timestamp: str | None = None
    content: str = ""
    tool_name: str | None = None
    tool_input: dict[str, Any] = Field(default_factory=dict)
    tool_output: dict[str, Any] = Field(default_factory=dict)
    state_from: str | None = None
    state_to: str | None = None
    tokens: TokenUsage = Field(default_factory=TokenUsage)
    cost_usd: float = 0.0
    stage: Stage = Stage.UNKNOWN


class TraceMetadata(BaseModel):
    run_id: str = "unknown"
    framework: str = "generic"
    started_at: str | None = None
    completed_at: str | None = None
    status: RunStatus = RunStatus.UNKNOWN
    agent_name: str | None = None


class NormalizedTrace(BaseModel):
    metadata: TraceMetadata
    available_tools: list[ToolDefinition] = Field(default_factory=list)
    steps: list[TraceStep]

    @property
    def available_tool_names(self) -> set[str]:
        return {t.name for t in self.available_tools}

    @property
    def thoughts(self) -> list[TraceStep]:
        return [s for s in self.steps if s.type == StepType.THOUGHT]

    @property
    def tool_calls(self) -> list[TraceStep]:
        return [s for s in self.steps if s.type == StepType.TOOL_CALL]

    @property
    def state_transitions(self) -> list[TraceStep]:
        return [s for s in self.steps if s.type == StepType.STATE_TRANSITION]
