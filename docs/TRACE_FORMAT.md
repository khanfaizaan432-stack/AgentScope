# AgentScope Trace Format Specification

## Canonical Schema

All parsers normalize input to this schema before analysis.

```json
{
  "metadata": {
    "run_id": "string",
    "framework": "generic | langgraph | crewai | openai_agents",
    "started_at": "ISO-8601",
    "completed_at": "ISO-8601",
    "status": "success | failure | timeout | unknown",
    "agent_name": "string (optional)"
  },
  "available_tools": [
    { "name": "Search", "description": "Web search tool" },
    { "name": "Calculator", "description": "Math operations" }
  ],
  "steps": [
    {
      "index": 0,
      "type": "thought | tool_call | tool_result | state_transition",
      "timestamp": "ISO-8601 (optional)",
      "content": "string",
      "tool_name": "string (for tool_call/tool_result)",
      "tool_input": {},
      "tool_output": {},
      "state_from": "string (for state_transition)",
      "state_to": "string (for state_transition)",
      "tokens": {
        "prompt": 0,
        "completion": 0
      },
      "cost_usd": 0.0,
      "stage": "planning | execution | retrieval | synthesis"
    }
  ]
}
```

## Step Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `thought` | Agent reasoning / planning text | `content` |
| `tool_call` | Tool invocation | `tool_name`, `tool_input` |
| `tool_result` | Tool response | `tool_name`, `tool_output` |
| `state_transition` | Workflow state change | `state_from`, `state_to` |

## Framework-Specific Formats

### Generic (Default)

Uses the canonical schema directly. Set `"framework": "generic"` in metadata.

### LangGraph

```json
{
  "metadata": { "framework": "langgraph", "run_id": "..." },
  "available_tools": [...],
  "messages": [
    { "role": "assistant", "content": "...", "tool_calls": [...] },
    { "role": "tool", "name": "Search", "content": "..." }
  ],
  "node_transitions": [
    { "from": "planner", "to": "executor" }
  ]
}
```

### CrewAI

```json
{
  "metadata": { "framework": "crewai", "run_id": "..." },
  "available_tools": [...],
  "tasks": [
    {
      "agent": "Researcher",
      "description": "...",
      "tools_used": ["Search"],
      "output": "..."
    }
  ]
}
```

## Token & Cost Fields

Per-step token counts enable cost analysis. If not provided, the analyzer estimates based on content length (~4 chars/token).

Cost defaults to GPT-4o-mini pricing unless overridden:
- Prompt: $0.15 / 1M tokens
- Completion: $0.60 / 1M tokens

## Validation Rules

1. `steps` must be non-empty
2. Each step must have a valid `type`
3. `tool_call` steps must reference a `tool_name`
4. `available_tools` is optional but required for hallucination detection
