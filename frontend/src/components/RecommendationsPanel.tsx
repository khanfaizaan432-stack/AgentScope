"use client";

import { Recommendation, IssueSeverity } from "@/types";
import {
  AlertTriangle,
  XCircle,
  AlertCircle,
  Info,
  Lightbulb,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState } from "react";

interface RecommendationsPanelProps {
  recommendations: Recommendation[];
}

// ── Severity styling ──────────────────────────────────────────────────────────
const severityConfig: Record<
  IssueSeverity,
  { icon: typeof AlertTriangle; color: string; bg: string; border: string; badge: string }
> = {
  critical: {
    icon: XCircle,
    color: "text-red-400",
    bg: "bg-red-500 bg-opacity-10",
    border: "border-red-500 border-opacity-25",
    badge: "bg-red-500 bg-opacity-20 text-red-400",
  },
  high: {
    icon: AlertTriangle,
    color: "text-orange-400",
    bg: "bg-orange-500 bg-opacity-10",
    border: "border-orange-500 border-opacity-25",
    badge: "bg-orange-500 bg-opacity-20 text-orange-400",
  },
  medium: {
    icon: AlertCircle,
    color: "text-yellow-400",
    bg: "bg-yellow-500 bg-opacity-10",
    border: "border-yellow-500 border-opacity-25",
    badge: "bg-yellow-500 bg-opacity-20 text-yellow-400",
  },
  low: {
    icon: Info,
    color: "text-blue-400",
    bg: "bg-blue-500 bg-opacity-10",
    border: "border-blue-500 border-opacity-25",
    badge: "bg-blue-500 bg-opacity-20 text-blue-400",
  },
  info: {
    icon: Info,
    color: "text-zinc-400",
    bg: "bg-zinc-500 bg-opacity-10",
    border: "border-zinc-500 border-opacity-20",
    badge: "bg-zinc-500 bg-opacity-20 text-zinc-400",
  },
};

// ── Category labels ───────────────────────────────────────────────────────────
const categoryLabel: Record<string, string> = {
  loop: "Loop",
  hallucination: "Hallucination",
  redundancy: "Redundancy",
  cost: "Cost",
  tool: "Tool",
  convergence: "Convergence",
};

// ── Evidence value renderer ───────────────────────────────────────────────────
function EvidenceValue({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    return (
      <span className="flex flex-wrap gap-1">
        {value.map((v, i) => (
          <span
            key={i}
            className="px-1.5 py-0.5 rounded text-xs font-mono bg-zinc-800 text-zinc-300"
          >
            {String(v)}
          </span>
        ))}
      </span>
    );
  }
  if (typeof value === "number") {
    return (
      <span className="font-mono text-zinc-200">
        {Number.isInteger(value) ? value : value.toFixed(2)}
      </span>
    );
  }
  return <span className="font-mono text-zinc-200">{String(value)}</span>;
}

// ── Evidence table ────────────────────────────────────────────────────────────
function EvidenceTable({ evidence }: { evidence: Record<string, unknown> }) {
  const entries = Object.entries(evidence).filter(
    ([, v]) => v !== null && v !== undefined
  );
  if (entries.length === 0) return null;

  return (
    <div className="mt-3 rounded-lg overflow-hidden border border-zinc-700/40">
      <table className="w-full text-xs">
        <tbody>
          {entries.map(([key, val], i) => (
            <tr
              key={key}
              className={i % 2 === 0 ? "bg-zinc-800/40" : "bg-zinc-800/20"}
            >
              <td className="px-3 py-1.5 text-zinc-400 font-medium w-1/3 whitespace-nowrap">
                {key.replace(/_/g, " ")}
              </td>
              <td className="px-3 py-1.5">
                <EvidenceValue value={val} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Single recommendation card ────────────────────────────────────────────────
function RecommendationCard({ rec, index }: { rec: Recommendation; index: number }) {
  const [expanded, setExpanded] = useState(index === 0); // first card open by default
  const cfg = severityConfig[rec.severity];
  const Icon = cfg.icon;

  return (
    <div
      className={`rounded-xl border ${cfg.border} ${cfg.bg} transition-all duration-200`}
    >
      {/* Header row — always visible */}
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-start gap-3 p-4 text-left group"
      >
        <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${cfg.color}`} />

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-sm text-zinc-100">{rec.issue}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.badge}`}>
              {rec.severity}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-700/50 text-zinc-400">
              {categoryLabel[rec.category] ?? rec.category}
            </span>
          </div>
          {/* Show recommendation preview when collapsed */}
          {!expanded && (
            <p className="mt-1 text-xs text-zinc-400 line-clamp-1 truncate">
              {rec.recommendation}
            </p>
          )}
        </div>

        <span className={`flex-shrink-0 mt-0.5 ${cfg.color} opacity-60 group-hover:opacity-100 transition-opacity`}>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </span>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {/* Evidence */}
          {Object.keys(rec.evidence).length > 0 && (
            <div>
              <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">
                Evidence
              </p>
              <EvidenceTable evidence={rec.evidence} />
            </div>
          )}

          {/* Recommendation text */}
          <div>
            <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide mb-1">
              Recommendation
            </p>
            <div className="flex gap-2 p-3 rounded-lg bg-indigo-500 bg-opacity-10 border border-indigo-500 border-opacity-20">
              <Lightbulb className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-zinc-300 leading-relaxed">{rec.recommendation}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────
export default function RecommendationsPanel({
  recommendations,
}: RecommendationsPanelProps) {
  const criticalCount = recommendations.filter((r) => r.severity === "critical").length;
  const highCount = recommendations.filter((r) => r.severity === "high").length;

  if (recommendations.length === 0) {
    return (
      <div className="glass-card p-6 flex items-center gap-3">
        <Lightbulb className="w-5 h-5 text-green-400 flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-zinc-200">No recommendations</p>
          <p className="text-xs text-zinc-500 mt-0.5">
            No actionable issues were detected in this trace.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card p-6 space-y-4">
      {/* Panel header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-indigo-400" />
          <h3 className="text-sm font-semibold text-zinc-200">
            Recommendations
          </h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-700/60 text-zinc-400">
            {recommendations.length}
          </span>
        </div>

        {/* Severity summary badges */}
        <div className="flex gap-2">
          {criticalCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 font-medium">
              {criticalCount} critical
            </span>
          )}
          {highCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 font-medium">
              {highCount} high
            </span>
          )}
        </div>
      </div>

      {/* Cards */}
      <div className="space-y-3">
        {recommendations.map((rec, i) => (
          <RecommendationCard key={`${rec.issue}-${i}`} rec={rec} index={i} />
        ))}
      </div>
    </div>
  );
}
