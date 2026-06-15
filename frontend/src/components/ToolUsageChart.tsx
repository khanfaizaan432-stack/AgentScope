"use client";

import dynamic from "next/dynamic";
import { ToolAnalysisResult } from "@/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface ToolUsageChartProps {
  data: ToolAnalysisResult;
}

export default function ToolUsageChart({ data }: ToolUsageChartProps) {
  if (data.per_tool.length === 0) {
    return (
      <div className="glass-card p-6 flex items-center justify-center h-64">
        <p className="text-zinc-500 text-sm">No tool calls detected</p>
      </div>
    );
  }

  const names = data.per_tool.map((t) => t.tool_name);
  const counts = data.per_tool.map((t) => t.call_count);

  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Tool Usage</h3>
      <Plot
        data={[
          {
            type: "bar",
            x: names,
            y: counts,
            marker: {
              color: counts.map((_, i) => `hsl(${240 + i * 30}, 70%, 60%)`),
              line: { width: 0 },
            },
            text: counts.map((c) => `${c} calls`),
            textposition: "auto",
          },
        ]}
        layout={{
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          font: { color: "#a1a1aa", size: 12 },
          margin: { t: 20, b: 60, l: 50, r: 20 },
          xaxis: {
            tickangle: -30,
            gridcolor: "#27272a",
          },
          yaxis: {
            title: "Calls",
            gridcolor: "#27272a",
          },
          height: 300,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: "100%" }}
      />
      <div className="mt-4 grid grid-cols-3 gap-4 text-center text-sm">
        <div>
          <div className="text-zinc-500">Total Calls</div>
          <div className="text-lg font-semibold">{data.total_calls}</div>
        </div>
        <div>
          <div className="text-zinc-500">Most Used</div>
          <div className="text-lg font-semibold text-accent">{data.most_used || "—"}</div>
        </div>
        <div>
          <div className="text-zinc-500">Unique Tools</div>
          <div className="text-lg font-semibold">{data.unique_tools}</div>
        </div>
      </div>
    </div>
  );
}
