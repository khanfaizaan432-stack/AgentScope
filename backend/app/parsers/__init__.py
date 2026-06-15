from typing import Any

from app.models.trace import NormalizedTrace
from app.parsers.crewai import CrewAIParser
from app.parsers.generic import GenericParser
from app.parsers.langgraph import LangGraphParser


def detect_and_parse(raw: dict[str, Any]) -> NormalizedTrace:
    framework = raw.get("metadata", {}).get("framework", "")

    if framework == "langgraph" or "messages" in raw:
        return LangGraphParser().parse(raw)
    if framework == "crewai" or "tasks" in raw:
        return CrewAIParser().parse(raw)
    return GenericParser().parse(raw)
