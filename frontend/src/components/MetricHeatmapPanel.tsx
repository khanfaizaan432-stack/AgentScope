"use client";

import { useMemo, useState } from "react";
import { CausalAnalysis, sanitizeIncomingMetrics } from "@/types";
import { Clock, DollarSign } from "lucide-react";

type HeatmapMetric = "latency" | "cost";

interface MetricHeatmapPanelProps {
  data: CausalAnalysis;
}

function intensityClass(ratio: number): string {
  if (ratio >= 0.9) return "bg-red-500/20 border-red-500/60 text-red-100";
  if (ratio >= 0.6) return "bg-red-400/10 border-red-400/40 text-zinc-100";
  if (ratio >= 0.3) return "bg-slate-500/10 border-slate-500/30 text-zinc-200";
  return "bg-slate-500/5 border-slate-500/20 text-zinc-300";
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${ms.toFixed(0)}ms`;
}

function formatUsd(usd: number): string {
  if (usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

export default function MetricHeatmapPanel({ data }: MetricHeatmapPanelProps) {
  const [metric, setMetric] = useState<HeatmapMetric>("latency");

  const nodes = useMemo(() => {
    const entries = Object.entries(data.node_metrics || {}).map(([node, m]) => {
      const sanitized = sanitizeIncomingMetrics(m);
      return {
        node,
        duration_ms: sanitized.duration_ms,
        cost_usd: sanitized.cost_usd,
      };
    });
    entries.sort((a, b) => a.node.localeCompare(b.node));
    return entries;
  }, [data.node_metrics]);

  const maxValue = useMemo(() => {
    if (nodes.length === 0) return 0;
    return Math.max(
      ...nodes.map((n) => (metric === "latency" ? n.duration_ms : n.cost_usd))
    );
  }, [nodes, metric]);

  const root = data.root_cause_node;

  return (
    <section id="metric-heatmap" className="glass-card p-6 space-y-4 scroll-mt-24">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="text-sm text-zinc-400">Latency / Cost Heatmap</div>
          {root ? (
            <div className="text-sm text-zinc-200">
              Root cause: <span className="font-semibold">{root}</span>
            </div>
          ) : (
            <div className="text-sm text-zinc-500">No causal failure detected.</div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setMetric("latency")}
            className={`px-3 py-1.5 rounded-full text-sm border ${
              metric === "latency"
                ? "bg-background/40 border-border text-zinc-100"
                : "bg-transparent border-border/40 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <Clock className="w-4 h-4" /> Latency
            </span>
          </button>
          <button
            type="button"
            onClick={() => setMetric("cost")}
            className={`px-3 py-1.5 rounded-full text-sm border ${
              metric === "cost"
                ? "bg-background/40 border-border text-zinc-100"
                : "bg-transparent border-border/40 text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <span className="inline-flex items-center gap-1.5">
              <DollarSign className="w-4 h-4" /> Cost
            </span>
          </button>
        </div>
      </div>

      {data.failure_path.length > 0 && (
        <div className="text-xs text-zinc-500">
          Failure path: {data.failure_path.join(" → ")}
        </div>
      )}

      {nodes.length === 0 ? (
        <div className="text-sm text-zinc-500">No node metrics available.</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {nodes.map((n) => {
            const value = metric === "latency" ? n.duration_ms : n.cost_usd;
            const ratio = maxValue > 0 ? value / maxValue : 0;
            const highlight = root && n.node === root;

            return (
              <div
                key={n.node}
                className={`rounded-lg border p-4 ${intensityClass(ratio)} ${
                  highlight ? "ring-1 ring-red-500/50" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="font-semibold text-sm truncate">{n.node}</div>
                  {highlight && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-100">
                      Root
                    </span>
                  )}
                </div>

                <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                  <div className="text-zinc-300">
                    <div className="text-zinc-500">Latency</div>
                    <div>{formatMs(n.duration_ms)}</div>
                  </div>
                  <div className="text-zinc-300">
                    <div className="text-zinc-500">Cost</div>
                    <div>{formatUsd(n.cost_usd)}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

