"use client";

import { useState } from "react";
import { Activity, Search, DollarSign, Brain, Shield } from "lucide-react";
import UploadForm from "@/components/UploadForm";
import OnboardingDemo from "@/components/OnboardingDemo";
import { analyzeTrace, analyzeSample, analyzeChaoticDemo } from "@/lib/api";
import { AnalysisReport } from "@/types";
import ReportDashboard from "@/components/ReportDashboard";

export default function Home() {
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scrollToFailurePanels, setScrollToFailurePanels] = useState(false);

  const handleUpload = async (file: File) => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeTrace(file);
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSample = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeSample();
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load sample");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setError(null);
    setScrollToFailurePanels(false);
  };

  const handleTriageDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const result = await analyzeChaoticDemo();
      setScrollToFailurePanels(true);
      setReport(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Triage demo failed");
    } finally {
      setLoading(false);
    }
  };

  if (report) {
    return (
      <ReportDashboard
        report={report}
        onReset={handleReset}
        scrollToFailurePanels={scrollToFailurePanels}
      />
    );
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-border">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-3">
          <Activity className="w-6 h-6 text-accent" />
          <span className="text-xl font-bold gradient-text">AgentScope</span>
          <span className="text-xs text-zinc-500 ml-2">v0.1.0</span>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 pt-10 pb-6">
        <OnboardingDemo onTriage={handleTriageDemo} loading={loading} />
      </section>

      <section className="max-w-6xl mx-auto px-6 py-14 text-center">
        <h1 className="text-4xl md:text-5xl font-bold mb-4">
          <span className="gradient-text">Datadog for AI Agents</span>
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl mx-auto mb-12">
          Upload agent execution traces and get automated diagnostics — loop detection,
          hallucination analysis, cost hotspots, and reasoning redundancy scoring.
        </p>

        <UploadForm onUpload={handleUpload} onSample={handleSample} loading={loading} />

        {error && (
          <div className="mt-6 max-w-2xl mx-auto p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
            {error}
          </div>
        )}
      </section>

      <section className="max-w-6xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            {
              icon: Search,
              title: "Loop Detection",
              desc: "Find infinite tool loops and cyclic workflow patterns",
            },
            {
              icon: Brain,
              title: "Reasoning Analysis",
              desc: "Detect redundant planning with semantic similarity",
            },
            {
              icon: DollarSign,
              title: "Cost Hotspots",
              desc: "Identify steps consuming disproportionate tokens",
            },
            {
              icon: Shield,
              title: "Hallucination Guard",
              desc: "Flag tools the agent called but don't exist",
            },
          ].map((feature) => (
            <div key={feature.title} className="glass-card p-6">
              <feature.icon className="w-8 h-8 text-accent mb-3" />
              <h3 className="font-semibold mb-2">{feature.title}</h3>
              <p className="text-sm text-zinc-400">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
