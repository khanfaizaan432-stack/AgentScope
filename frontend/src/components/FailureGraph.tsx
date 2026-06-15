"use client";

import { useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { WorkflowGraph } from "@/types";

interface FailureGraphProps {
  graph: WorkflowGraph;
}

export default function FailureGraph({ graph }: FailureGraphProps) {
  const nodes: Node[] = useMemo(
    () =>
      graph.nodes.map((n, i) => ({
        id: n.id,
        data: { label: n.label },
        position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 100 },
        style: {
          background: n.is_loop ? "#ef444420" : n.node_type === "thought" ? "#6366f120" : "#22c55e20",
          border: n.is_loop ? "2px solid #ef4444" : "1px solid #27272a",
          borderRadius: "8px",
          padding: "8px 12px",
          fontSize: "12px",
          color: "#e4e4e7",
          width: 180,
        },
      })),
    [graph.nodes]
  );

  const edges: Edge[] = useMemo(
    () =>
      graph.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        animated: e.is_loop,
        style: { stroke: e.is_loop ? "#ef4444" : "#52525b" },
        markerEnd: { type: MarkerType.ArrowClosed, color: e.is_loop ? "#ef4444" : "#52525b" },
      })),
    [graph.edges]
  );

  if (graph.nodes.length === 0) {
    return (
      <div className="glass-card p-6 flex items-center justify-center h-64">
        <p className="text-zinc-500 text-sm">No workflow graph data</p>
      </div>
    );
  }

  return (
    <div className="glass-card p-6">
      <h3 className="text-sm font-medium text-zinc-400 mb-4">
        Workflow Graph
        <span className="ml-2 text-xs text-red-400">Red = loop detected</span>
      </h3>
      <div className="h-[400px] rounded-lg overflow-hidden border border-border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#27272a" gap={20} />
          <Controls />
          <MiniMap
            nodeColor={(n) => (n.style?.border?.toString().includes("ef4444") ? "#ef4444" : "#6366f1")}
            maskColor="#0a0a0f80"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
