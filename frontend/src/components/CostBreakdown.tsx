"use client";

import dynamic from "next/dynamic";
import { CostAnalysisResult } from "@/types";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

interface CostBreakdownProps {
  data: CostAnalysisResult;
}

const STAGE_COLORS: Record<string, string> = {
  planning: "#6366f1",
  execution: "#22c55e",
  retrieval: "#f59e0b",
  synthesis: "#a78bfa",
  unknown: "#71717a",
};

export default function CostBreakdown({ data }: CostBreakdownProps) {
  const stages = Object.keys(data.cost_by_stage);
  const values = Object.values(data.cost_by_stage);
  const colors = stages.map((s) => STAGE_COLORS[s] || STAGE_COLORS.unknown);

  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Cost Breakdown</h3>
      {stages.length > 0 ? (
        <Plot
          data={[
            {
              type: "pie",
              labels: stages.map((s) => s.charAt(0).toUpperCase() + s.slice(1)),
              values,
              marker: { colors },
              textinfo: "label+percent",
              hole: 0.4,
            },
          ]}
          layout={{
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { color: "#a1a1aa", size: 12 },
            margin: { t: 20, b: 20, l: 20, r: 20 },
            showlegend: false,
            height: 280,
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      ) : (
        <div className="flex items-center justify-center h-64">
          <p className="text-zinc-500 text-sm">No cost data available</p>
        </div>
      )}
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <div className="text-zinc-500">Total Tokens</div>
          <div className="text-lg font-semibold">{data.total_tokens.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-zinc-500">Est. Cost</div>
          <div className="text-lg font-semibold">${data.total_cost_usd.toFixed(4)}</div>
        </div>
        <div>
          <div className="text-zinc-500">Prompt Tokens</div>
          <div className="font-medium">{data.total_prompt_tokens.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-zinc-500">Completion Tokens</div>
          <div className="font-medium">{data.total_completion_tokens.toLocaleString()}</div>
        </div>
      </div>
      {data.most_expensive_step && (
        <div className="mt-4 p-3 rounded-lg bg-yellow-500/10 text-sm">
          <span className="text-yellow-400 font-medium">
            Step {data.most_expensive_step.step_index}
          </span>
          <span className="text-zinc-400">
            {" "}
            consumed {data.most_expensive_step.percentage}% of total cost (
            {data.most_expensive_step.stage} phase)
          </span>
        </div>
      )}
    </div>
  );
}
