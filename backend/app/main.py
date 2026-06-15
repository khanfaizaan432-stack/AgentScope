import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.services.analysis_service import AnalysisService

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

MAX_UPLOAD_SIZE = 10 * 1024 * 1024


@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "service": "agentscope", "version": "0.1.0"}


@app.post("/api/v1/analyze")
async def analyze_trace(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON trace files are accepted")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 10 MB limit")

    try:
        raw = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not raw.get("steps") and not raw.get("messages") and not raw.get("tasks"):
        raise HTTPException(
            status_code=400,
            detail="Trace must contain 'steps', 'messages', or 'tasks'",
        )

    try:
        report = service.analyze_raw(raw)
        return report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.post("/api/v1/analyze/json")
async def analyze_json(body: dict):
    if not body.get("steps") and not body.get("messages") and not body.get("tasks"):
        raise HTTPException(
            status_code=400,
            detail="Trace must contain 'steps', 'messages', or 'tasks'",
        )

    try:
        report = service.analyze_raw(body)
        return report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.get("/api/v1/analyze/sample")
async def analyze_sample():
    sample_path = Path(__file__).resolve().parent.parent.parent / "samples" / "sample_trace.json"
    if not sample_path.exists():
        sample_path = Path(__file__).resolve().parent.parent.parent.parent / "samples" / "sample_trace.json"

    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample trace not found")

    with open(sample_path) as f:
        raw = json.load(f)

    report = service.analyze_raw(raw)
    return report.model_dump()
