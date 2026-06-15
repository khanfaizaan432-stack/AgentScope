# AgentScope

**Datadog for AI Agents** — automatically analyze agent execution traces to detect loops, hallucinations, cost hotspots, and reasoning redundancy.

![AgentScope](https://img.shields.io/badge/AgentScope-v0.1.0-6366f1)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB)
![Next.js](https://img.shields.io/badge/Next.js-15-000000)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)

## What It Does

AgentScope ingests JSON execution traces from AI agent frameworks and produces an automated **Agent Health Report**:

```
Agent Health Score: 72/100

Issues Detected:
  • Repeated Search tool calls (infinite loop)
  • Reasoning redundancy = 91%
  • Cost concentration in planning phase
  • Hallucinated tool: DatabaseLookup

Strengths:
  ✓ Good task completion
  ✓ Reasonable tool call count
```

## Features

| Feature | Description |
|---------|-------------|
| **Trace Upload** | Generic, LangGraph, CrewAI JSON formats |
| **Loop Detection** | Consecutive identical tool calls + cyclic state graphs |
| **Tool Analysis** | Call counts, usage distribution, unused tools |
| **Cost Analysis** | Token usage, cost estimation, per-step breakdown |
| **Redundancy Detection** | TF-IDF + Jaccard cosine similarity on adjacent thoughts |
| **Hallucination Guard** | Flags tools not in the declared registry |
| **Health Score** | Composite 0–100 score with weighted penalties |
| **Visualizations** | Tool bar chart, cost pie chart, timeline, workflow graph |

## Architecture

```
Trace JSON → Parser → NormalizedTrace → Analyzers → Health Report → Dashboard
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full system design.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and upload a trace or click "analyze the sample trace".

### API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Analyze sample trace
curl http://localhost:8000/api/v1/analyze/sample

# Upload trace file
curl -X POST http://localhost:8000/api/v1/analyze -F "file=@samples/sample_trace.json"
```

## Project Structure

```
AgentScope/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── models/              # Pydantic schemas
│   │   ├── parsers/             # Generic, LangGraph, CrewAI
│   │   ├── analyzers/           # Loop, tool, cost, redundancy, hallucination
│   │   ├── scoring/             # Health score + graph builder
│   │   └── services/            # Analysis orchestration
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # Dashboard visualizations
│   │   ├── lib/                 # API client
│   │   └── types/               # TypeScript interfaces
│   └── package.json
├── samples/
│   └── sample_trace.json        # Demo trace with all issue types
└── docs/
    ├── ARCHITECTURE.md
    ├── TRACE_FORMAT.md
    └── MVP_ROADMAP.md
```

## Health Scoring Algorithm

Starting score: **100**

| Factor | Max Penalty | Trigger |
|--------|-------------|---------|
| Loop penalty | -25 | Each loop pattern (-8 per loop) |
| Redundancy penalty | -20 | Redundancy score > 0% (scaled) |
| Cost penalty | -15 | Expensive step concentration |
| Tool penalty | -15 | Single tool > 50% of calls |
| Hallucination penalty | -15 | Each hallucinated tool (-10) |
| Completion bonus | +10 | Task completed successfully |

Grade: A (90+), B (80+), C (70+), D (60+), F (<60)

## Trace Format

See [docs/TRACE_FORMAT.md](docs/TRACE_FORMAT.md) for the canonical schema. Minimal example:

```json
{
  "metadata": { "run_id": "run-001", "framework": "generic", "status": "success" },
  "available_tools": [{ "name": "Search" }, { "name": "Calculator" }],
  "steps": [
    { "index": 0, "type": "thought", "content": "I need to search...", "stage": "planning" },
    { "index": 1, "type": "tool_call", "tool_name": "Search", "stage": "retrieval" },
    { "index": 2, "type": "tool_result", "tool_name": "Search", "stage": "retrieval" }
  ]
}
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | FastAPI, Pydantic |
| Analysis | NetworkX, pure-Python TF-IDF |
| Charts | Plotly.js, React Flow |

## Roadmap

See [docs/MVP_ROADMAP.md](docs/MVP_ROADMAP.md) for development milestones and stretch goals including LangGraph native integration, trace replay, and agent benchmarking.

## License

MIT
