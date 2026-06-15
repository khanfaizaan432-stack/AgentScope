"use client";

import { useEffect } from "react";
import { AnalysisReport } from "@/types";
import Link from "next/link";
import { Activity, ArrowLeft, ArrowRightLeft } from "lucide-react";
import HealthScore from "@/components/HealthScore";
import IssuesList from "@/components/IssuesList";
import ToolUsageChart from "@/components/ToolUsageChart";
import CostBreakdown from "@/components/CostBreakdown";
import AgentTimeline from "@/components/AgentTimeline";
import FailureGraph from "@/components/FailureGraph";
import RecommendationsPanel from "@/components/RecommendationsPanel";
import LangGraphInsights from "@/components/LangGraphInsights";
import ExecutiveSummaryPanel from "@/components/ExecutiveSummaryPanel";
import MetricHeatmapPanel from "@/components/MetricHeatmapPanel";
import CausalAnalysisPanel from "@/components/CausalAnalysisPanel";

interface ReportDashboardProps {
  report: AnalysisReport;
  onReset: () => void;
  scrollToFailurePanels?: boolean;
}

export default function ReportDashboard({
  report,
  onReset,
  scrollToFailurePanels = false,
}: ReportDashboardProps) {
  useEffect(() => {
    if (!scrollToFailurePanels) return;

    let innerTimer: number | undefined;
    const outerTimer = window.setTimeout(() => {
      document.getElementById("causal-analysis")?.scrollIntoView({ behavior: "smooth", block: "start" });
      innerTimer = window.setTimeout(() => {
        document.getElementById("metric-heatmap")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 600);
    }, 150);

    return () => {
      window.clearTimeout(outerTimer);
      if (innerTimer !== undefined) {
        window.clearTimeout(innerTimer);
      }
    };
  }, [scrollToFailurePanels]);
  return (
    <main className="min-h-screen">
      <header className="border-b border-border sticky top-0 z-50 bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-accent" />
            <span className="text-xl font-bold gradient-text">AgentScope</span>
            <span className="text-sm text-zinc-500">
              Report — {report.metadata.run_id}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/compare" className="flex items-center gap-2 text-sm text-zinc-400 hover:text-foreground transition-colors">
              <ArrowRightLeft className="w-4 h-4" />
              Compare Runs
            </Link>
            <button
              onClick={onReset}
              className="flex items-center gap-2 text-sm text-zinc-400 hover:text-foreground transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              New Analysis
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <div className="flex flex-wrap gap-4 text-sm text-zinc-400">
          <span>
            Framework: <strong className="text-zinc-300">{report.metadata.framework}</strong>
          </span>
          <span>
            Agent: <strong className="text-zinc-300">{report.metadata.agent_name || "—"}</strong>
          </span>
          <span>
            Status:{" "}
            <strong
              className={
                report.metadata.status === "success" ? "text-green-400" : "text-red-400"
              }
            >
              {report.metadata.status}
            </strong>
          </span>
          <span>
            Steps: <strong className="text-zinc-300">{report.metadata.total_steps}</strong>
          </span>
          <span>
            Redundancy:{" "}
            <strong className="text-zinc-300">{report.redundancy.redundancy_score}%</strong>
          </span>
        </div>

        <ExecutiveSummaryPanel data={report.executive_summary} />
        <CausalAnalysisPanel data={report.causal_analysis} />
        <MetricHeatmapPanel data={report.causal_analysis} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <HealthScore health={report.health} />
          <div className="lg:col-span-2">
            <IssuesList issues={report.issues} strengths={report.health.strengths} />
          </div>
        </div>

        <RecommendationsPanel recommendations={report.recommendations} />

        {report.metadata.framework === "langgraph" && report.langgraph_analysis && (
          <LangGraphInsights analysis={report.langgraph_analysis} />
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ToolUsageChart data={report.tool_analysis} />
          <CostBreakdown data={report.cost_analysis} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AgentTimeline nodes={report.timeline} />
          <FailureGraph graph={report.workflow_graph} />
        </div>
      </div>
    </main>
  );
}
