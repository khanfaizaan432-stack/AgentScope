"use client";

import { ExecutiveSummary, HealthVerdict } from "@/types";
import { ClipboardList } from "lucide-react";

interface ExecutiveSummaryPanelProps {
  data: ExecutiveSummary;
}

function verdictClasses(verdict: HealthVerdict): string {
  switch (verdict) {
    case "Excellent":
      return "bg-green-100 text-green-800";
    case "Good":
      return "bg-emerald-100 text-emerald-800";
    case "Fair":
      return "bg-yellow-100 text-yellow-800";
    case "Poor":
      return "bg-orange-100 text-orange-800";
    case "Critical":
      return "bg-red-100 text-red-800";
    default:
      return "bg-zinc-100 text-zinc-800";
  }
}

export default function ExecutiveSummaryPanel({ data }: ExecutiveSummaryPanelProps) {
  return (
    <section className="glass-card p-6 space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm text-zinc-400">
            <ClipboardList className="w-4 h-4" />
            <span>Executive Summary</span>
          </div>
          <p className="text-zinc-200 leading-relaxed">{data.overview}</p>
        </div>

        <span
          className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${verdictClasses(
            data.health_verdict
          )}`}
        >
          {data.health_verdict}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-zinc-300">Key Findings</h3>
          {data.key_findings.length === 0 ? (
            <p className="text-sm text-zinc-500">No major issues detected.</p>
          ) : (
            <ul className="space-y-2 text-sm text-zinc-400 list-disc pl-5">
              {data.key_findings.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-zinc-300">Priority Actions</h3>
          {data.priority_actions.length === 0 ? (
            <p className="text-sm text-zinc-500">No priority actions suggested.</p>
          ) : (
            <ul className="space-y-2 text-sm text-zinc-400 list-disc pl-5">
              {data.priority_actions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
