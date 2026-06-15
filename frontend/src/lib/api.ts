import { AnalysisReport } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function analyzeTrace(file: File): Promise<AnalysisReport> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(error.detail || "Analysis failed");
  }

  return response.json();
}

export async function analyzeSample(): Promise<AnalysisReport> {
  const response = await fetch(`${API_BASE}/api/v1/analyze/sample`);

  if (!response.ok) {
    throw new Error("Failed to load sample analysis");
  }

  return response.json();
}

export async function analyzeJson(trace: object): Promise<AnalysisReport> {
  const response = await fetch(`${API_BASE}/api/v1/analyze/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(trace),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(error.detail || "Analysis failed");
  }

  return response.json();
}
