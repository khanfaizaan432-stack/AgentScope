import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.comparison.comparison_engine import ComparisonEngine
from app.comparison.comparison_models import ComparisonReport, ComparisonRequest
from app.models.report import AnalysisReport
from app.services.analysis_service import AnalysisService
from app.services.demo_data import get_chaotic_trace, get_excellent_trace
from app.utils.security import (
    TraceAggregateMemoryError,
    TracePayloadTooLargeError,
    TraceSecurityError,
    enforce_size_limit,
    sanitize_raw_json_bytes,
    validate_and_secure_payload,
)

app = FastAPI(
    title="AgentScope API",
    description="AI Agent Failure Analyzer — Datadog for AI Agents",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = AnalysisService()
comparison_engine = ComparisonEngine()

MAX_UPLOAD_SIZE = 5 * 1024 * 1024


def _secure_ingest_payload(payload: dict, *, label: str = "Trace") -> dict:
    """Run unified security gate and map validation failures to HTTP errors."""
    try:
        secured = validate_and_secure_payload(payload)
    except TracePayloadTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except (TraceAggregateMemoryError, TraceSecurityError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    _validate_trace_payload(secured, label=label)
    return secured


def _validate_trace_payload(payload: dict, *, label: str = "Trace") -> None:
    # Supported ingestion formats:
    # - Canonical AgentScope trace: {"steps": [...]}
    # - LangGraph minimal: {"messages": [...], "node_transitions": [...]}
    # - LangGraph exported events: {"events": [...]}
    # - LangSmith export: {"runs": [...]}
    if (
        payload.get("steps")
        or payload.get("messages")
        or payload.get("tasks")
        or payload.get("events")
        or payload.get("node_transitions")
        or payload.get("graph")
        or payload.get("runs")
    ):
        return

    raise HTTPException(
        status_code=400,
        detail=(
            f"{label} must contain one of: "
            "'steps', 'messages', 'tasks', 'events', 'node_transitions', 'graph', or 'runs'"
        ),
    )


@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "service": "agentscope", "version": "0.1.0"}


@app.post("/api/v1/analyze", response_model=AnalysisReport)
async def analyze_trace(file: UploadFile = File(...)) -> AnalysisReport:
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON trace files are accepted")

    content = await file.read()
    try:
        enforce_size_limit(content)
        parsed = sanitize_raw_json_bytes(content)
    except TracePayloadTooLargeError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except TraceSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    _validate_trace_payload(parsed)

    try:
        return service.analyze_raw(parsed)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.post("/api/v1/analyze/json", response_model=AnalysisReport)
async def analyze_json(body: dict) -> AnalysisReport:
    secured = _secure_ingest_payload(body)

    try:
        return service.analyze_raw(secured)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.get("/api/v1/demo/excellent")
async def demo_excellent_trace() -> dict:
    return get_excellent_trace()


@app.get("/api/v1/demo/chaotic")
async def demo_chaotic_trace() -> dict:
    return get_chaotic_trace()


@app.get("/api/v1/demo/chaotic/analyze", response_model=AnalysisReport)
async def analyze_chaotic_demo() -> AnalysisReport:
    return service.analyze_raw(get_chaotic_trace())


@app.get("/api/v1/demo/excellent/analyze", response_model=AnalysisReport)
async def analyze_excellent_demo() -> AnalysisReport:
    return service.analyze_raw(get_excellent_trace())


@app.get("/api/v1/analyze/sample", response_model=AnalysisReport)
async def analyze_sample() -> AnalysisReport:
    sample_path = Path(__file__).resolve().parent.parent.parent / "samples" / "sample_trace.json"
    if not sample_path.exists():
        sample_path = Path(__file__).resolve().parent.parent.parent.parent / "samples" / "sample_trace.json"

    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample trace not found")

    with open(sample_path) as f:
        raw = json.load(f)

    return service.analyze_raw(raw)


@app.post("/api/v1/compare", response_model=ComparisonReport)
async def compare_runs(body: ComparisonRequest) -> ComparisonReport:
    run_a = _secure_ingest_payload(body.run_a, label="Run A")
    run_b = _secure_ingest_payload(body.run_b, label="Run B")

    try:
        report_a = service.analyze_raw(run_a)
        report_b = service.analyze_raw(run_b)
        return comparison_engine.compare_reports(report_a, report_b)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")
