"use client";

import { CausalAnalysis } from "@/types";
import { GitBranch, AlertOctagon } from "lucide-react";

interface CausalAnalysisPanelProps {
  data: CausalAnalysis;
}

export default function CausalAnalysisPanel({ data }: CausalAnalysisPanelProps) {
  const hasFailure = Boolean(data.root_cause_node || data.failure_path.length > 0);

  return (
    <section id="causal-analysis" className="glass-card p-6 space-y-4 scroll-mt-24">
      <div className="flex items-center gap-2">
        <GitBranch className="w-5 h-5 text-accent" />
        <h3 className="text-sm font-medium text-zinc-400">Causal Analysis</h3>
      </div>

      {!hasFailure ? (
        <p className="text-sm text-zinc-500">No failure cascade detected — agent completed successfully.</p>
      ) : (
        <div className="space-y-4">
          {data.root_cause_node && (
            <div className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/40">
              <AlertOctagon className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-xs text-red-300/80 uppercase tracking-wide mb-1">Root Cause Node</div>
                <div className="text-lg font-semibold text-red-100">{data.root_cause_node}</div>
              </div>
            </div>
          )}

          {data.failure_path.length > 0 && (
            <div>
              <div className="text-xs text-zinc-500 mb-2">Failure Path</div>
              <div className="flex flex-wrap items-center gap-2 text-sm">
                {data.failure_path.map((node, i) => (
                  <span key={`${node}-${i}`} className="flex items-center gap-2">
                    <span
                      className={`px-2.5 py-1 rounded-md border ${
                        data.root_cause_node === node
                          ? "bg-red-500/20 border-red-500/50 text-red-100"
                          : "bg-zinc-800/50 border-border text-zinc-300"
                      }`}
                    >
                      {node}
                    </span>
                    {i < data.failure_path.length - 1 && (
                      <span className="text-zinc-600">→</span>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
