"use client";

import type { NodeState, PipelineStatus } from "@/hooks/use-pipeline";
import { NODE_RENDERERS } from "./node-renderers";

export function NodeOutputContent({
  nodeId,
  nodeState,
  pipelineStatus,
  resumePipeline,
}: {
  nodeId: string;
  nodeState: NodeState | undefined;
  pipelineStatus?: PipelineStatus;
  resumePipeline?: (editedPrompt?: string) => void;
}) {
  const output = nodeState?.output;
  const status = nodeState?.status ?? "idle";

  if (status === "idle") {
    return (
      <div style={{ color: "#444", fontSize: 13, textAlign: "center", marginTop: 40 }}>
        Waiting to start…
      </div>
    );
  }

  if (status === "running") {
    return (
      <div style={{ color: "#93c5fd", fontSize: 13, textAlign: "center", marginTop: 40 }}>
        <div
          style={{
            width: 24,
            height: 24,
            border: "2px solid rgba(59,130,246,0.3)",
            borderTopColor: "#3b82f6",
            borderRadius: "50%",
            margin: "0 auto 12px",
            animation: "spin-slow 0.8s linear infinite",
          }}
        />
        Running…
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div
        style={{
          background: "rgba(239,68,68,0.08)",
          border: "1px solid rgba(239,68,68,0.2)",
          borderRadius: 8,
          padding: "12px 14px",
          color: "#fca5a5",
          fontSize: 13,
          marginTop: 16,
        }}
      >
        Node failed. Check backend logs for details.
      </div>
    );
  }

  if (!output) {
    return (
      <div style={{ color: "#444", fontSize: 13, marginTop: 16 }}>
        No output data available.
      </div>
    );
  }

  const Renderer = NODE_RENDERERS[nodeId];
  if (Renderer) {
    return (
      <Renderer
        output={output}
        nodeState={nodeState!}
        pipelineStatus={pipelineStatus}
        resumePipeline={resumePipeline}
      />
    );
  }

  // Fallback: raw JSON for unknown nodes
  return (
    <pre
      style={{
        color: "#888",
        fontSize: 11,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}
    >
      {JSON.stringify(output, null, 2)}
    </pre>
  );
}
