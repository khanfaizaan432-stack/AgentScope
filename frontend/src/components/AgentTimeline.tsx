"use client";

import { TimelineNode } from "@/types";
import { Brain, Wrench, ArrowDown, AlertTriangle } from "lucide-react";

interface AgentTimelineProps {
  nodes: TimelineNode[];
}

const typeIcons: Record<string, typeof Brain> = {
  thought: Brain,
  tool_call: Wrench,
  tool_result: Wrench,
  state_transition: ArrowDown,
};

const typeColors: Record<string, string> = {
  thought: "border-purple-500/50 bg-purple-500/10",
  tool_call: "border-blue-500/50 bg-blue-500/10",
  tool_result: "border-green-500/50 bg-green-500/10",
  state_transition: "border-zinc-500/50 bg-zinc-500/10",
};

export default function AgentTimeline({ nodes }: AgentTimelineProps) {
  if (nodes.length === 0) {
    return (
      <div className="glass-card p-6 flex items-center justify-center h-48">
        <p className="text-zinc-500 text-sm">No execution steps</p>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">Execution Timeline</h3>
      <div className="space-y-1 max-h-[500px] overflow-y-auto pr-2">
        {nodes.map((node, i) => {
          const Icon = typeIcons[node.type] || Brain;
          const colorClass = typeColors[node.type] || typeColors.thought;
          const loopClass = node.is_loop ? "ring-2 ring-red-500/50" : "";

          return (
            <div key={node.id}>
              <div
                className={`flex items-start gap-3 p-3 rounded-lg border ${colorClass} ${loopClass}`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  {node.is_loop ? (
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                  ) : (
                    <Icon className="w-4 h-4 text-zinc-400" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-zinc-500">Step {node.step_index}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                      {node.type.replace("_", " ")}
                    </span>
                    <span className="text-xs text-zinc-600">{node.stage}</span>
                  </div>
                  <p className="text-sm text-zinc-300 truncate">{node.label}</p>
                </div>
              </div>
              {i < nodes.length - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowDown className="w-3 h-3 text-zinc-600" />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
