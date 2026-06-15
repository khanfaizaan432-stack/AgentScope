"use client";

import { LangGraphAnalysisResult } from "@/types";
import { GitBranch, Repeat2, Timer, DollarSign, Hash } from "lucide-react";

interface LangGraphInsightsProps {
  analysis: LangGraphAnalysisResult;
}

function formatMs(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

export default function LangGraphInsights({ analysis }: LangGraphInsightsProps) {
  const loops = analysis.state_loops ?? [];
  const branches = analysis.branches;
  const bottlenecks = analysis.bottlenecks;

  return (
    <div className="glass-card p-6 space-y-5">
      <div className="flex items-center gap-2">
        <GitBranch className="w-4 h-4 text-accent" />
        <h3 className="text-sm font-medium text-zinc-300">LangGraph Analysis</h3>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="rounded-lg border border-border/60 p-4 bg-background/20">
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <Repeat2 className="w-4 h-4" />
            <span>State loops</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-zinc-200">{loops.length}</div>
          <p className="mt-1 text-sm text-zinc-400">
            {loops.length === 0 ? "No repeating state cycles detected." : "Repeated state cycles detected."}
          </p>
        </div>

        <div className="rounded-lg border border-border/60 p-4 bg-background/20">
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <GitBranch className="w-4 h-4" />
            <span>Branches</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-zinc-200">{branches?.branch_count ?? 0}</div>
          <p className="mt-1 text-sm text-zinc-400">{branches?.summary ?? "No branching detected."}</p>
        </div>

        <div className="rounded-lg border border-border/60 p-4 bg-background/20">
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <Timer className="w-4 h-4" />
            <span>Bottlenecks</span>
          </div>
          <div className="mt-2 text-2xl font-bold text-zinc-200">
            {bottlenecks?.most_frequent_node ?? "—"}
          </div>
          <p className="mt-1 text-sm text-zinc-400">Most frequent node</p>
        </div>
      </div>

      {(loops.length > 0 || branches || bottlenecks) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {loops.length > 0 && (
            <div className="rounded-lg border border-border/60 p-4">
              <h4 className="text-sm font-medium text-zinc-300 flex items-center gap-2">
                <Repeat2 className="w-4 h-4 text-yellow-400" />
                State loop details
              </h4>
              <div className="mt-3 space-y-2">
                {loops.slice(0, 3).map((loop, i) => (
                  <div key={i} className="text-sm text-zinc-400">
                    <span className="text-zinc-300 font-medium">
                      Cycle {loop.cycle_length} ({loop.severity})
                    </span>
                    : {loop.repeated_states.join(" → ")} (x{loop.repetitions})
                  </div>
                ))}
                {loops.length > 3 && (
                  <div className="text-sm text-zinc-500">+{loops.length - 3} more</div>
                )}
              </div>
            </div>
          )}

          {(branches || bottlenecks) && (
            <div className="rounded-lg border border-border/60 p-4">
              <h4 className="text-sm font-medium text-zinc-300">Branch & bottleneck metrics</h4>
              <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2 text-zinc-400">
                  <GitBranch className="w-4 h-4" />
                  <span>Max depth:</span>
                  <span className="text-zinc-200 font-medium">{branches?.max_branch_depth ?? "—"}</span>
                </div>
                <div className="flex items-center gap-2 text-zinc-400">
                  <GitBranch className="w-4 h-4" />
                  <span>Dead-ends:</span>
                  <span className="text-zinc-200 font-medium">{branches?.dead_end_branches ?? "—"}</span>
                </div>
                <div className="flex items-center gap-2 text-zinc-400">
                  <DollarSign className="w-4 h-4" />
                  <span>Most expensive:</span>
                  <span className="text-zinc-200 font-medium">
                    {bottlenecks?.most_expensive_node ?? "—"}{" "}
                    {bottlenecks?.most_expensive_node ? `($${bottlenecks.most_expensive_cost_usd.toFixed(4)})` : ""}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-zinc-400">
                  <Timer className="w-4 h-4" />
                  <span>Slowest:</span>
                  <span className="text-zinc-200 font-medium">
                    {bottlenecks?.slowest_node ?? "—"}{" "}
                    {bottlenecks?.slowest_node ? `(${formatMs(bottlenecks.slowest_duration_ms)})` : ""}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-zinc-400 sm:col-span-2">
                  <Hash className="w-4 h-4" />
                  <span>Most frequent:</span>
                  <span className="text-zinc-200 font-medium">
                    {bottlenecks?.most_frequent_node ?? "—"}{" "}
                    {bottlenecks?.most_frequent_node ? `(x${bottlenecks.most_frequent_count})` : ""}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

