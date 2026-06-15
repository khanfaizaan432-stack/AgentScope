"use client";

import { ComparisonReport } from "@/types";
import { ArrowLeft, CheckCircle2, AlertTriangle, Minus, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

interface ComparisonDashboardProps {
  report: ComparisonReport;
  onReset: () => void;
}

function metricColor(delta: number, lowerIsBetter: boolean): string {
  if (delta === 0) return "text-zinc-400";
  const improved = lowerIsBetter ? delta < 0 : delta > 0;
  return improved ? "text-green-400" : "text-red-400";
}

function metricBackground(delta: number, lowerIsBetter: boolean): string {
  if (delta === 0) return "bg-zinc-500/10 border-zinc-500/20";
  const improved = lowerIsBetter ? delta < 0 : delta > 0;
  return improved ? "bg-green-500/10 border-green-500/20" : "bg-red-500/10 border-red-500/20";
}

function formatNumber(value: number): string {
  if (Number.isInteger(value)) {
    return value.toString();
  }
  return value.toFixed(2).replace(/\.0+$/, "");
}

function formatCurrency(value: number): string {
  if (value === 0) {
    return "$0.00";
  }

  const absoluteValue = Math.abs(value);
  const decimals = absoluteValue >= 1 ? 2 : absoluteValue >= 0.01 ? 4 : 6;
  const formatted = value.toFixed(decimals).replace(/\.?0+$/, "");
  const sign = value < 0 ? "-" : "";
  return `${sign}$${formatted.replace("-", "")}`;
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function MetricCard({
  title,
  before,
  after,
  delta,
  lowerIsBetter,
  formatter = formatNumber,
}: {
  title: string;
  before: number;
  after: number;
  delta: number;
  lowerIsBetter: boolean;
  formatter?: (value: number) => string;
}) {
  const colorClass = metricColor(delta, lowerIsBetter);
  const bgClass = metricBackground(delta, lowerIsBetter);
  const Icon = delta === 0 ? Minus : lowerIsBetter ? (delta < 0 ? TrendingDown : TrendingUp) : delta > 0 ? TrendingUp : TrendingDown;

  return (
    <div className={`rounded-2xl border p-4 ${bgClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-zinc-500">{title}</p>
          <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-zinc-500 text-xs">Before</p>
              <p className="font-semibold text-zinc-100">{formatter(before)}</p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">After</p>
              <p className="font-semibold text-zinc-100">{formatter(after)}</p>
            </div>
            <div>
              <p className="text-zinc-500 text-xs">Delta</p>
              <p className={`font-semibold ${colorClass}`}>{delta > 0 ? "+" : ""}{formatter(delta)}</p>
            </div>
          </div>
        </div>
        <Icon className={`w-5 h-5 shrink-0 ${colorClass}`} />
      </div>
    </div>
  );
}

function VerdictTone(verdict: string): string {
  if (verdict === "Major Improvement") return "from-emerald-500/20 to-teal-500/10 border-emerald-500/30";
  if (verdict === "Regression Detected") return "from-red-500/20 to-orange-500/10 border-red-500/30";
  if (verdict === "Mixed Results") return "from-amber-500/20 to-yellow-500/10 border-amber-500/30";
  return "from-zinc-500/20 to-zinc-500/10 border-zinc-500/30";
}

export default function ComparisonDashboard({ report, onReset }: ComparisonDashboardProps) {
  const verdictClass = VerdictTone(report.verdict);

  return (
    <main className="min-h-screen">
      <header className="border-b border-border sticky top-0 z-50 bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Sparkles className="w-6 h-6 text-accent" />
            <span className="text-xl font-bold gradient-text">AgentScope</span>
            <span className="text-sm text-zinc-500">Compare Runs</span>
          </div>
          <button
            onClick={onReset}
            className="flex items-center gap-2 text-sm text-zinc-400 hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            New Comparison
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <section className={`rounded-3xl border bg-gradient-to-br ${verdictClass} p-6 md:p-8`}>
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-zinc-400">Verdict</p>
              <h1 className="mt-2 text-3xl md:text-4xl font-bold text-zinc-50">{report.verdict}</h1>
              <p className="mt-2 text-sm text-zinc-300 max-w-2xl">
                Run A score {formatNumber(report.score_delta.before)} vs Run B score {formatNumber(report.score_delta.after)}.
                The comparison highlights where the newer run is healthier and where it regressed.
              </p>
            </div>
            <div className="rounded-2xl bg-background/60 border border-white/10 px-4 py-3 text-sm text-zinc-200">
              <p>Run A Score: <span className="font-semibold text-zinc-50">{formatNumber(report.score_delta.before)}</span></p>
              <p>Run B Score: <span className="font-semibold text-zinc-50">{formatNumber(report.score_delta.after)}</span></p>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
          <MetricCard title="Health Score" before={report.score_delta.before} after={report.score_delta.after} delta={report.score_delta.delta} lowerIsBetter={false} />
          <MetricCard title="Cost" before={report.cost_delta.before} after={report.cost_delta.after} delta={report.cost_delta.delta} lowerIsBetter={true} formatter={formatCurrency} />
          <MetricCard title="Loops" before={report.loop_delta.before} after={report.loop_delta.after} delta={report.loop_delta.delta} lowerIsBetter={true} />
          <MetricCard title="Redundancy" before={report.redundancy_delta.before} after={report.redundancy_delta.after} delta={report.redundancy_delta.delta} lowerIsBetter={true} formatter={formatPercent} />
          <MetricCard title="Hallucinations" before={report.hallucination_delta.before} after={report.hallucination_delta.after} delta={report.hallucination_delta.delta} lowerIsBetter={true} />
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              <h2 className="text-sm font-semibold text-zinc-100">Improvements</h2>
            </div>
            {report.improvements.length > 0 ? (
              <div className="space-y-3">
                {report.improvements.map((item) => (
                  <div key={item} className="flex gap-3 rounded-xl border border-green-500/20 bg-green-500/8 p-3">
                    <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-zinc-200">{item}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No clear improvements were detected.</p>
            )}
          </div>

          <div className="glass-card p-6">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-orange-400" />
              <h2 className="text-sm font-semibold text-zinc-100">Regressions</h2>
            </div>
            {report.regressions.length > 0 ? (
              <div className="space-y-3">
                {report.regressions.map((item) => (
                  <div key={item} className="flex gap-3 rounded-xl border border-orange-500/20 bg-orange-500/8 p-3">
                    <AlertTriangle className="w-5 h-5 text-orange-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-zinc-200">{item}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No regressions were detected.</p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
