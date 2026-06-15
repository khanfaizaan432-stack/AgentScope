"use client";

import { HealthReport } from "@/types";

interface HealthScoreProps {
  health: HealthReport;
}

function scoreColor(score: number): string {
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#f59e0b";
  return "#ef4444";
}

export default function HealthScore({ health }: HealthScoreProps) {
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (health.score / 100) * circumference;
  const color = scoreColor(health.score);

  return (
    <div className="glass-card p-6 flex flex-col items-center">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Agent Health Score</h3>
      <div className="relative w-36 h-36">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#27272a" strokeWidth="8" />
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            className="score-ring"
            style={{ strokeDasharray: circumference, strokeDashoffset: offset }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold" style={{ color }}>
            {health.score}
          </span>
          <span className="text-sm text-zinc-400">/ 100</span>
        </div>
      </div>
      <div
        className="mt-3 px-3 py-1 rounded-full text-sm font-semibold"
        style={{ backgroundColor: `${color}20`, color }}
      >
        Grade {health.grade}
      </div>
      <p className="mt-4 text-sm text-zinc-400 text-center leading-relaxed">{health.summary}</p>
    </div>
  );
}
