from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

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
from app.analyzers.langgraph_analyzer import assign_node_context_from_transitions


class LangGraphParser(BaseParser):
    def parse(self, raw: dict[str, Any]) -> NormalizedTrace:
        # ------------------------------------------------------------------
        # Format 0: LangSmith export (runs array)
        # ------------------------------------------------------------------
        if isinstance(raw.get("runs"), list) and raw.get("runs"):
            return self._parse_langsmith_export(raw)

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

        # ------------------------------------------------------------------
        # Format 1: LangGraph exported events (best-effort)
        # ------------------------------------------------------------------
        current_node: str | None = None
        for event in raw.get("events", []):
            event_type = str(event.get("type", "")).lower()
            node = event.get("node") or event.get("name") or event.get("node_name")
            timestamp = event.get("timestamp") or event.get("ts")

            if event_type in ("node_start", "node_enter", "state_enter"):
                current_node = str(node) if node is not None else current_node
                continue

            if event_type in ("node_end", "state_exit"):
                current_node = str(node) if node is not None else current_node
                continue

            if event_type in ("state_transition", "node_transition", "transition"):
                state_from = event.get("from") or event.get("state_from") or ""
                state_to = event.get("to") or event.get("state_to") or ""
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.STATE_TRANSITION,
                        state_from=str(state_from) if state_from is not None else "",
                        state_to=str(state_to) if state_to is not None else "",
                        content=f"{state_from} → {state_to}",
                        stage=Stage.UNKNOWN,
                        timestamp=timestamp,
                    )
                )
                idx += 1
                current_node = str(state_to) if state_to else current_node
                continue

            if event_type in ("message", "llm_message"):
                role = event.get("role", "assistant")
                content = event.get("content", "")
                if role == "assistant" and content:
                    text = content if isinstance(content, str) else str(content)
                    steps.append(
                        TraceStep(
                            index=idx,
                            type=StepType.THOUGHT,
                            content=text,
                            stage=Stage.PLANNING,
                            tokens=self._estimate_tokens(text),
                            node_name=current_node,
                            timestamp=timestamp,
                        )
                    )
                    idx += 1
                continue

            if event_type in ("tool_start", "tool_call"):
                tool_name = event.get("tool_name") or event.get("name") or "unknown"
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.TOOL_CALL,
                        tool_name=str(tool_name),
                        tool_input=event.get("arguments", {}) or event.get("input", {}) or {},
                        stage=self._infer_stage(StepType.TOOL_CALL, str(tool_name)),
                        node_name=current_node,
                        timestamp=timestamp,
                    )
                )
                idx += 1
                continue

            if event_type in ("tool_end", "tool_result"):
                tool_name = event.get("tool_name") or event.get("name") or "unknown"
                output = event.get("output", event.get("content", ""))
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.TOOL_RESULT,
                        tool_name=str(tool_name),
                        tool_output={"content": output},
                        stage=Stage.EXECUTION,
                        node_name=current_node,
                        timestamp=timestamp,
                    )
                )
                idx += 1

        # ------------------------------------------------------------------
        # Format 2: minimal LangGraph export (messages + node_transitions)
        # ------------------------------------------------------------------
        if not steps:
            for msg in raw.get("messages", []):
                role = msg.get("role", "")
                content = msg.get("content", "")

                if role == "assistant":
                    if content:
                        text = content if isinstance(content, str) else str(content)
                        steps.append(
                            TraceStep(
                                index=idx,
                                type=StepType.THOUGHT,
                                content=text,
                                stage=Stage.PLANNING,
                                tokens=self._estimate_tokens(text),
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
                state_from = trans.get("from", "")
                state_to = trans.get("to", "")
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.STATE_TRANSITION,
                        state_from=state_from,
                        state_to=state_to,
                        content=f"{state_from} → {state_to}",
                        stage=Stage.UNKNOWN,
                    )
                )
                idx += 1

        assign_node_context_from_transitions(steps)
        return NormalizedTrace(metadata=metadata, available_tools=tools, steps=steps)

    # ------------------------------------------------------------------
    # LangSmith export parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_iso_dt(value: Any) -> datetime | None:
        if not value or not isinstance(value, str):
            return None
        try:
            # LangSmith uses ISO-ish timestamps, often without "Z"
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _duration_ms(start: Any, end: Any) -> float | None:
        start_dt = LangGraphParser._parse_iso_dt(start)
        end_dt = LangGraphParser._parse_iso_dt(end)
        if not start_dt or not end_dt:
            return None
        return max(0.0, (end_dt - start_dt).total_seconds() * 1000)

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _sort_key_for_run(run: dict[str, Any]) -> tuple[str, str]:
        # dotted_order is a stable ordering key for hierarchical traces.
        dotted = str(run.get("dotted_order") or "")
        run_id = str(run.get("id") or "")
        return (dotted, run_id)

    @staticmethod
    def _walk_parents(
        run: dict[str, Any], by_id: dict[str, dict[str, Any]]
    ) -> Iterable[dict[str, Any]]:
        current = run
        visited: set[str] = set()
        while current:
            rid = str(current.get("id") or "")
            if not rid or rid in visited:
                break
            visited.add(rid)
            parent_id = current.get("parent_run_id")
            if not parent_id:
                break
            parent = by_id.get(str(parent_id))
            if not parent:
                break
            yield parent
            current = parent

    @staticmethod
    def _nearest_chain_name(run: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> str | None:
        for parent in LangGraphParser._walk_parents(run, by_id):
            if parent.get("run_type") == "chain":
                return str(parent.get("name") or "unknown")
        return None

    @staticmethod
    def _extract_llm_text(outputs: Any) -> str:
        if not isinstance(outputs, dict):
            return ""

        # Common: {"messages": [{"role":"assistant","content":"..."}]}
        messages = outputs.get("messages")
        if isinstance(messages, list) and messages:
            for m in reversed(messages):
                if not isinstance(m, dict):
                    continue
                role = m.get("role") or m.get("type")
                if role in ("assistant", "ai"):
                    content = m.get("content")
                    if isinstance(content, str) and content.strip():
                        return content

        # Common: {"generations": [[{"text": "..."}]]}
        generations = outputs.get("generations")
        if isinstance(generations, list) and generations:
            first = generations[0] if generations else None
            if isinstance(first, list) and first:
                gen0 = first[0]
                if isinstance(gen0, dict):
                    text = gen0.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
                    message = gen0.get("message")
                    if isinstance(message, dict):
                        content = message.get("content")
                        if isinstance(content, str) and content.strip():
                            return content

        # Fallback: stringify a small-ish selection of fields
        for key in ("content", "output", "text"):
            if isinstance(outputs.get(key), str) and outputs[key].strip():
                return outputs[key]
        return ""

    def _parse_langsmith_export(self, raw: dict[str, Any]) -> NormalizedTrace:
        runs_raw = raw.get("runs", [])
        runs: list[dict[str, Any]] = [r for r in runs_raw if isinstance(r, dict)]
        if not runs:
            # Shouldn't happen due to guard in parse(), but keep it safe.
            return NormalizedTrace(metadata=TraceMetadata(framework="langgraph"), steps=[])

        by_id: dict[str, dict[str, Any]] = {str(r.get("id")): r for r in runs if r.get("id")}
        ordered = sorted(runs, key=self._sort_key_for_run)

        root = next((r for r in ordered if not r.get("parent_run_id")), ordered[0])
        root_id = str(root.get("id") or "")

        # Metadata: prefer trace_id when present.
        run_id = str(root.get("trace_id") or root.get("id") or "unknown")
        status = str(root.get("status") or "unknown").lower()
        status_norm = "success" if status in ("success", "completed") else ("failure" if status in ("error", "failed") else "unknown")

        metadata = TraceMetadata(
            run_id=run_id,
            framework="langgraph",
            started_at=root.get("start_time"),
            completed_at=root.get("end_time"),
            status=RunStatus(status_norm),
            agent_name=None,
        )

        steps: list[TraceStep] = []
        idx = 0

        # Node-level transitions: use direct children of the root run as "nodes" when possible.
        node_runs = [
            r
            for r in ordered
            if str(r.get("parent_run_id") or "") == root_id and r.get("run_type") in ("chain", "tool")
        ]
        if node_runs:
            prev = "__start__"
            for r in node_runs:
                name = str(r.get("name") or "unknown")
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.STATE_TRANSITION,
                        state_from=prev,
                        state_to=name,
                        content=f"{prev} → {name}",
                        stage=Stage.UNKNOWN,
                        timestamp=r.get("start_time"),
                    )
                )
                idx += 1
                prev = name

        # Tool + LLM spans
        for run in ordered:
            run_type = str(run.get("run_type") or "").lower()
            name = str(run.get("name") or "unknown")
            node_name = self._nearest_chain_name(run, by_id)

            duration_ms = self._duration_ms(run.get("start_time"), run.get("end_time"))
            tokens = TokenUsage(
                prompt=int(run.get("prompt_tokens") or 0),
                completion=int(run.get("completion_tokens") or 0),
            )
            cost = self._safe_float(run.get("total_cost") or 0.0)

            if run_type == "tool":
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.TOOL_CALL,
                        tool_name=name,
                        tool_input=run.get("inputs") or {},
                        stage=self._infer_stage(StepType.TOOL_CALL, name),
                        node_name=node_name,
                        timestamp=run.get("start_time"),
                        duration_ms=duration_ms,
                        tokens=tokens,
                        cost_usd=cost,
                    )
                )
                idx += 1
                steps.append(
                    TraceStep(
                        index=idx,
                        type=StepType.TOOL_RESULT,
                        tool_name=name,
                        tool_output=run.get("outputs") or {},
                        stage=Stage.EXECUTION,
                        node_name=node_name,
                        timestamp=run.get("end_time"),
                        duration_ms=duration_ms,
                        tokens=tokens,
                        cost_usd=cost,
                    )
                )
                idx += 1
                continue

            if run_type == "llm":
                content = self._extract_llm_text(run.get("outputs") or {})
                if content:
                    steps.append(
                        TraceStep(
                            index=idx,
                            type=StepType.THOUGHT,
                            content=content,
                            stage=Stage.PLANNING,
                            node_name=node_name,
                            timestamp=run.get("end_time") or run.get("start_time"),
                            duration_ms=duration_ms,
                            tokens=tokens if tokens.total > 0 else self._estimate_tokens(content),
                            cost_usd=cost,
                        )
                    )
                    idx += 1

        assign_node_context_from_transitions(steps)
        return NormalizedTrace(metadata=metadata, available_tools=[], steps=steps)
