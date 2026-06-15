from typing import Any

from app.models.trace import NormalizedTrace
from app.parsers.crewai import CrewAIParser
from app.parsers.generic import GenericParser
from app.parsers.langgraph import LangGraphParser


def _looks_like_langgraph(raw: dict[str, Any]) -> bool:
    metadata_fw = raw.get("metadata", {}).get("framework")
    if metadata_fw == "langgraph":
        return True

    # Strong structural markers
    if any(k in raw for k in ("events", "node_transitions", "graph", "runs")):
        return True

    # Weak marker: "messages" is common across many agent traces, so only treat it as LangGraph
    # if it contains LangGraph-ish tool calling structure.
    messages = raw.get("messages")
    if isinstance(messages, list) and messages:
        for m in messages:
            if not isinstance(m, dict):
                continue
            if m.get("role") == "tool":
                return True
            if "tool_calls" in m:
                return True

    return False


def detect_and_parse(raw: dict[str, Any]) -> NormalizedTrace:
    framework = raw.get("metadata", {}).get("framework", "")

    if framework == "crewai" or "tasks" in raw:
        return CrewAIParser().parse(raw)
    # Canonical AgentScope schema should always be treated as generic, even if it happens to
    # include other fields like "messages".
    if "steps" in raw:
        return GenericParser().parse(raw)
    if framework == "langgraph" or _looks_like_langgraph(raw):
        return LangGraphParser().parse(raw)
    return GenericParser().parse(raw)
