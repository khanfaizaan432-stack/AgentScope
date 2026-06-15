# AgentScope Architecture

## System Overview

AgentScope is a trace analysis platform that ingests agent execution logs and produces automated diagnostic reports. It follows a **parse → analyze → score → visualize** pipeline.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Trace JSON │────▶│ Trace Parser │────▶│ NormalizedTrace │────▶│  Analyzers   │
│  (upload)   │     │ (multi-fmt)  │     │  (canonical)    │     │  (parallel)  │
└─────────────┘     └──────────────┘     └─────────────────┘     └──────┬───────┘
                                                                         │
                    ┌──────────────┐     ┌─────────────────┐            │
                    │  Next.js UI  │◀────│  Health Report  │◀───────────┘
                    │  (dashboard) │     │  (JSON API)     │
                    └──────────────┘     └─────────────────┘
```

## Components

### 1. Trace Ingestion Layer

**Purpose:** Accept traces from multiple agent frameworks and normalize to a canonical format.

| Parser | Input Format | Key Mappings |
|--------|-------------|--------------|
| `GenericParser` | Custom JSON schema | Direct field mapping |
| `LangGraphParser` | LangGraph checkpoint/stream logs | `messages`, `tool_calls`, node transitions |
| `CrewAIParser` | CrewAI task logs | `agent`, `task`, `tool` events |

**Canonical Model:** `NormalizedTrace`
- `steps[]`: ordered execution steps (thought, tool_call, tool_result, state_transition)
- `available_tools[]`: declared tool registry
- `metadata`: run_id, framework, timestamps, completion status

### 2. Analysis Engine

Five independent analyzers run against the normalized trace:

| Analyzer | Algorithm | Output |
|----------|-----------|--------|
| `LoopDetector` | Consecutive identical tool calls, cyclic state graph (NetworkX) | Loop events with severity |
| `ToolAnalyzer` | Aggregation (pandas) | Per-tool call counts, efficiency metrics |
| `CostAnalyzer` | Token summation, per-step cost allocation | Cost breakdown by stage |
| `RedundancyAnalyzer` | TF-IDF + Jaccard similarity on adjacent thoughts | Redundancy score 0–100% |
| `HallucinationDetector` | Set difference (called tools − available tools) | Hallucinated tool list |

### 3. Health Scoring

Weighted composite score (0–100):

```
score = 100
  - loop_penalty        (max -25)
  - redundancy_penalty  (max -20)
  - cost_penalty        (max -15)
  - tool_penalty        (max -15)
  - hallucination_penalty (max -15)
  + completion_bonus    (max +10)
```

### 4. API Layer (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | Upload trace JSON, return full report |
| `/api/v1/analyze/sample` | GET | Return sample trace analysis |
| `/api/v1/health` | GET | Service health check |

### 5. Frontend (Next.js)

- **Upload page:** Drag-and-drop JSON trace upload
- **Report dashboard:** Health score, issues, strengths
- **Visualizations:** Plotly charts (tool usage, cost), React Flow graph (execution timeline with loop highlighting)

## Data Flow

1. User uploads JSON via frontend
2. Frontend POSTs to `/api/v1/analyze`
3. Backend detects format, parses to `NormalizedTrace`
4. All analyzers execute (can be parallelized)
5. `HealthScorer` computes composite score
6. `AnalysisReport` returned as JSON
7. Frontend renders dashboard components

## Database (Optional — Phase 2)

MVP is stateless (no persistence). Future schema:

```sql
CREATE TABLE traces (
  id UUID PRIMARY KEY,
  filename VARCHAR(255),
  framework VARCHAR(50),
  uploaded_at TIMESTAMP,
  raw_json JSONB
);

CREATE TABLE reports (
  id UUID PRIMARY KEY,
  trace_id UUID REFERENCES traces(id),
  health_score INTEGER,
  report_json JSONB,
  created_at TIMESTAMP
);
```

## Deployment Topology

```
┌─────────────────────────────────────────┐
│              Docker Compose             │
│  ┌─────────────┐    ┌────────────────┐  │
│  │  Next.js    │───▶│  FastAPI       │  │
│  │  :3000      │    │  :8000         │  │
│  └─────────────┘    └────────────────┘  │
└─────────────────────────────────────────┘
```

## Security Considerations

- File size limits on upload (10 MB default)
- JSON schema validation before analysis
- No arbitrary code execution from trace content
- CORS restricted to frontend origin in production
