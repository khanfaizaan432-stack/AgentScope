"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { Activity, ArrowRightLeft, FileJson, Loader2, Upload, X } from "lucide-react";
import ComparisonDashboard from "@/components/ComparisonDashboard";
import { compareTraces } from "@/lib/api";
import { ComparisonReport } from "@/types";

const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const COMPARISON_HIGHLIGHTS = [
  { title: "Health score", description: "Did the candidate run improve overall quality?" },
  { title: "Cost and tokens", description: "Did the run spend less and use fewer tokens?" },
  { title: "Loops and hallucinations", description: "Did the agent behave more reliably?" },
];

function validateTraceFile(file: File | null): string | null {
  if (!file) {
    return null;
  }

  if (!file.name.toLowerCase().endsWith(".json")) {
    return "Only JSON trace files are supported.";
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return "File exceeds the 10 MB upload limit.";
  }

  return null;
}

function RunPicker({
  label,
  file,
  onSelect,
  loading,
  error,
}: {
  label: string;
  file: File | null;
  onSelect: (file: File | null) => void;
  loading: boolean;
  error: string | null;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div
      className={`glass-card p-5 border transition-colors ${
        error ? "border-red-500/40" : file ? "border-accent/40" : "border-border"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-zinc-500">{label}</p>
          <h3 className="mt-2 text-lg font-semibold text-zinc-100">Upload trace JSON</h3>
          <p className="mt-1 text-sm text-zinc-400">
            Choose a raw agent execution trace to compare its analysis output.
          </p>
        </div>
        <div className="rounded-full bg-accent/10 p-3 text-accent">
          <ArrowRightLeft className="w-5 h-5" />
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={(e) => onSelect(e.target.files?.[0] ?? null)}
        disabled={loading}
      />

      <div
        className={`mt-5 rounded-2xl border border-dashed bg-background/40 px-4 py-5 transition-colors hover:bg-accent/5 ${
          error ? "border-red-500/40 hover:border-red-500/50" : "border-border hover:border-accent/60"
        }`}
      >
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={loading}
          className="w-full text-left disabled:opacity-50"
        >
          {file ? (
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="rounded-xl bg-emerald-500/10 p-3 text-emerald-400">
                  <FileJson className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-zinc-100 truncate">{file.name}</p>
                  <p className="text-xs text-zinc-500">{Math.max(1, Math.round(file.size / 1024))} KB</p>
                </div>
              </div>
              <span className="text-xs uppercase tracking-[0.2em] text-emerald-400/80">Selected</span>
            </div>
          ) : (
            <div className="flex items-center gap-3 text-zinc-400">
              <Upload className="w-5 h-5 text-accent" />
              <div>
                <p className="text-sm font-medium text-zinc-200">Click to choose a trace</p>
                <p className="text-xs text-zinc-500">JSON only. Generic, LangGraph, and CrewAI traces are supported.</p>
              </div>
            </div>
          )}
        </button>

        {file && (
          <div className="mt-3 flex items-center justify-end">
            <button
              type="button"
              onClick={() => onSelect(null)}
              disabled={loading}
              className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-200 transition-colors disabled:opacity-50"
            >
              <X className="w-3.5 h-3.5" />
              Clear file
            </button>
          </div>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}
    </div>
  );
}

export default function CompareRunsPage() {
  const [runA, setRunA] = useState<File | null>(null);
  const [runB, setRunB] = useState<File | null>(null);
  const [report, setReport] = useState<ComparisonReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runAError, setRunAError] = useState<string | null>(null);
  const [runBError, setRunBError] = useState<string | null>(null);

  const canCompare = Boolean(runA && runB && !runAError && !runBError && !loading);

  const handleRunSelection = (target: "a" | "b", file: File | null) => {
    const validationError = validateTraceFile(file);
    setError(null);
    setReport(null);

    if (target === "a") {
      setRunA(validationError ? null : file);
      setRunAError(validationError);
      return;
    }

    setRunB(validationError ? null : file);
    setRunBError(validationError);
  };

  const handleCompare = async () => {
    if (!runA || !runB) {
      setError("Please upload both runs before comparing.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const result = await compareTraces(runA, runB);
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setRunA(null);
    setRunB(null);
    setReport(null);
    setError(null);
    setRunAError(null);
    setRunBError(null);
  };

  if (report) {
    return <ComparisonDashboard report={report} onReset={handleReset} />;
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-border bg-background/75 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-accent" />
            <span className="text-xl font-bold gradient-text">AgentScope</span>
            <span className="text-sm text-zinc-500">Compare Runs</span>
          </div>
          <Link href="/" className="text-sm text-zinc-400 hover:text-foreground transition-colors">
            Back to Analysis
          </Link>
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-6 py-14 space-y-10">
        <div className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.28em] text-zinc-500">P2 Run Comparison</p>
          <h1 className="mt-3 text-4xl md:text-5xl font-bold text-zinc-50 leading-tight">
            Compare two agent runs and see which version is healthier.
          </h1>
          <p className="mt-4 text-lg text-zinc-400 max-w-2xl">
            Run A is the baseline. Run B is the candidate. Upload both traces to compare health score,
            cost, looping, redundancy, and hallucinations with a rule-based verdict.
          </p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <RunPicker
            label="Run A · Baseline"
            file={runA}
            onSelect={(file) => handleRunSelection("a", file)}
            loading={loading}
            error={runAError}
          />
          <RunPicker
            label="Run B · Candidate"
            file={runB}
            onSelect={(file) => handleRunSelection("b", file)}
            loading={loading}
            error={runBError}
          />
        </div>

        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="text-sm text-zinc-500 flex items-center gap-2">
            <FileJson className="w-4 h-4" />
            JSON only, up to 10 MB each. Files stay local until you click Compare runs.
          </div>
          <button
            onClick={handleCompare}
            disabled={!canCompare}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-white transition-all hover:bg-accent-light disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRightLeft className="w-4 h-4" />}
            {loading ? "Comparing runs..." : "Compare runs"}
          </button>
        </div>

        {error && (
          <div
            aria-live="polite"
            className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300"
          >
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {COMPARISON_HIGHLIGHTS.map((item) => (
            <div key={item.title} className="glass-card p-5">
              <p className="text-sm font-semibold text-zinc-100">{item.title}</p>
              <p className="mt-2 text-sm text-zinc-400">{item.description}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
