"use client";

import { Issue, IssueSeverity } from "@/types";
import { AlertTriangle, CheckCircle, XCircle, Info, AlertCircle } from "lucide-react";

interface IssuesListProps {
  issues: Issue[];
  strengths: string[];
}

const severityConfig: Record<
  IssueSeverity,
  { icon: typeof AlertTriangle; color: string; bg: string }
> = {
  critical: { icon: XCircle, color: "text-red-400", bg: "bg-red-500/10" },
  high: { icon: AlertTriangle, color: "text-orange-400", bg: "bg-orange-500/10" },
  medium: { icon: AlertCircle, color: "text-yellow-400", bg: "bg-yellow-500/10" },
  low: { icon: Info, color: "text-blue-400", bg: "bg-blue-500/10" },
  info: { icon: Info, color: "text-zinc-400", bg: "bg-zinc-500/10" },
};

export default function IssuesList({ issues, strengths }: IssuesListProps) {
  return (
    <div className="space-y-6">
      {issues.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-sm font-medium text-zinc-400 mb-4">
            Issues Detected ({issues.length})
          </h3>
          <div className="space-y-3">
            {issues.map((issue, i) => {
              const config = severityConfig[issue.severity];
              const Icon = config.icon;
              return (
                <div
                  key={i}
                  className={`flex gap-3 p-3 rounded-lg ${config.bg}`}
                >
                  <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${config.color}`} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{issue.title}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}>
                        {issue.severity}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-400 mt-1">{issue.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {strengths.length > 0 && (
        <div className="glass-card p-6">
          <h3 className="text-sm font-medium text-zinc-400 mb-4">Strengths</h3>
          <div className="space-y-2">
            {strengths.map((strength, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                <span className="text-zinc-300">{strength}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
