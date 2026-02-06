"use client";

import {
  Download,
  Layers,
  ScanSearch,
  PenTool,
  Image,
  Video,
} from "lucide-react";
import type { PipelineNodeId, PipelineStatus } from "@/types/pipeline";

// ─── Node definitions ────────────────────────────────────────────────
const PIPELINE_NODES: {
  id: PipelineNodeId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  completedStep: string; // currentStep value when this node is done
}[] = [
  { id: "download_video", label: "Download", icon: Download, completedStep: "video_downloaded" },
  { id: "extract_frames", label: "Extract", icon: Layers, completedStep: "frames_extracted" },
  { id: "analyze_video", label: "Analyze", icon: ScanSearch, completedStep: "video_analyzed" },
  { id: "generate_prompt", label: "Prompt", icon: PenTool, completedStep: "prompt_generated" },
  { id: "generate_scene_image", label: "Scene", icon: Image, completedStep: "scene_image_generated" },
  { id: "generate_video", label: "Video", icon: Video, completedStep: "video_generated" },
];

// ─── Status derivation ──────────────────────────────────────────────
export type NodeStatus = "idle" | "completed" | "running" | "pending" | "failed";

function findCompletedUpTo(currentStep: string): number {
  for (let i = PIPELINE_NODES.length - 1; i >= 0; i--) {
    if (
      PIPELINE_NODES[i].completedStep === currentStep ||
      (currentStep === "scene_image_skipped" && PIPELINE_NODES[i].id === "generate_scene_image")
    ) {
      return i;
    }
  }
  return -1;
}

function deriveNodeStatuses(
  currentStep: string,
  pipelineStatus: PipelineStatus,
): Record<PipelineNodeId, NodeStatus> {
  const result = {} as Record<PipelineNodeId, NodeStatus>;

  if (pipelineStatus === "idle") {
    for (const node of PIPELINE_NODES) result[node.id] = "idle";
    return result;
  }

  const completedUpTo = findCompletedUpTo(currentStep);

  if (pipelineStatus === "failed") {
    for (let i = 0; i < PIPELINE_NODES.length; i++) {
      if (i <= completedUpTo) {
        result[PIPELINE_NODES[i].id] = "completed";
      } else if (i === completedUpTo + 1) {
        result[PIPELINE_NODES[i].id] = "failed";
      } else {
        result[PIPELINE_NODES[i].id] = "pending";
      }
    }
    // Edge case: failed before any step completed
    if (completedUpTo === -1) {
      result[PIPELINE_NODES[0].id] = "failed";
      for (let i = 1; i < PIPELINE_NODES.length; i++) {
        result[PIPELINE_NODES[i].id] = "pending";
      }
    }
    return result;
  }

  // running or completed pipeline
  for (let i = 0; i < PIPELINE_NODES.length; i++) {
    if (i <= completedUpTo) {
      result[PIPELINE_NODES[i].id] = "completed";
    } else if (i === completedUpTo + 1 && pipelineStatus === "running") {
      result[PIPELINE_NODES[i].id] = "running";
    } else {
      result[PIPELINE_NODES[i].id] = pipelineStatus === "completed" ? "completed" : "pending";
    }
  }

  // If pipeline is running but no step completed yet, first node is running
  if (pipelineStatus === "running" && completedUpTo === -1) {
    result[PIPELINE_NODES[0].id] = "running";
  }

  return result;
}

// ─── Colors ──────────────────────────────────────────────────────────
const STATUS_COLORS: Record<NodeStatus, { border: string; bg: string; text: string; dot: string }> = {
  idle:      { border: "border-[hsl(220,4%,22%)]",  bg: "bg-[hsl(220,6%,13%)]", text: "text-[hsl(220,4%,45%)]", dot: "bg-[hsl(220,4%,30%)]" },
  completed: { border: "border-[hsl(145,65%,42%)]",  bg: "bg-[hsl(220,6%,13%)]", text: "text-[hsl(220,4%,88%)]", dot: "bg-[hsl(145,65%,42%)]" },
  running:   { border: "border-[hsl(210,80%,60%)]",  bg: "bg-[hsl(220,6%,13%)]", text: "text-[hsl(210,80%,60%)]", dot: "bg-[hsl(210,80%,60%)]" },
  pending:   { border: "border-[hsl(220,4%,22%)]",  bg: "bg-[hsl(220,6%,13%)]", text: "text-[hsl(220,4%,45%)]", dot: "bg-[hsl(220,4%,30%)]" },
  failed:    { border: "border-[hsl(0,70%,55%)]",    bg: "bg-[hsl(220,6%,13%)]", text: "text-[hsl(0,70%,55%)]",  dot: "bg-[hsl(0,70%,55%)]" },
};

// ─── Component ───────────────────────────────────────────────────────
interface PipelineFlowProps {
  currentStep: string;
  status: PipelineStatus;
  selectedNode: PipelineNodeId | null;
  onNodeClick: (nodeId: PipelineNodeId) => void;
}

export function PipelineFlow({
  currentStep,
  status,
  selectedNode,
  onNodeClick,
}: PipelineFlowProps) {
  const nodeStatuses = deriveNodeStatuses(currentStep, status);

  return (
    <div className="rounded-lg bg-[hsl(220,6%,9%)] p-8">
      {/* Label */}
      <div className="mb-4 font-mono text-xs uppercase tracking-[0.1em] text-[hsl(220,4%,45%)]">
        Pipeline
      </div>

      {/* Flow row */}
      <div className="flex items-center overflow-x-auto pb-2">
        {PIPELINE_NODES.map((node, i) => {
          const ns = nodeStatuses[node.id];
          const colors = STATUS_COLORS[ns];
          const isClickable = ns === "completed";
          const isSelected = selectedNode === node.id;
          const Icon = node.icon;

          return (
            <div key={node.id} className="flex items-center shrink-0">
              {/* Node box */}
              <button
                type="button"
                disabled={!isClickable}
                onClick={() => isClickable && onNodeClick(node.id)}
                className={[
                  "relative flex items-center gap-2 rounded-md border px-6 py-3 transition-all duration-200",
                  colors.border,
                  colors.bg,
                  colors.text,
                  isClickable && "cursor-pointer hover:scale-[1.02]",
                  !isClickable && "cursor-default",
                  isSelected && "ring-1 ring-[hsl(145,65%,42%)]/50",
                  ns === "running" && "animate-pulse-glow",
                ].filter(Boolean).join(" ")}
              >
                {/* Status dot */}
                <span className={`h-2 w-2 rounded-full shrink-0 ${colors.dot} ${ns === "running" ? "animate-pulse" : ""}`} />
                <Icon className="h-4 w-4 shrink-0" />
                <span className="font-mono text-xs uppercase tracking-[0.05em] whitespace-nowrap">
                  {node.label}
                </span>
              </button>

              {/* Connector line */}
              {i < PIPELINE_NODES.length - 1 && (
                <div
                  className={[
                    "h-[2px] w-8 shrink-0 transition-colors duration-300",
                    // Connector turns green once the *next* node is completed or running
                    nodeStatuses[PIPELINE_NODES[i + 1].id] === "completed" ||
                    nodeStatuses[PIPELINE_NODES[i + 1].id] === "running"
                      ? "bg-[hsl(145,65%,42%)]"
                      : "bg-[hsl(220,4%,22%)]",
                  ].join(" ")}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Status message */}
      {status === "running" && (
        <div className="mt-4 flex items-center gap-2 text-sm text-[hsl(210,80%,60%)]">
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
          <span className="font-mono text-xs">{currentStep || "Starting..."}</span>
        </div>
      )}

      {status === "failed" && (
        <div className="mt-4 text-sm font-mono text-[hsl(0,70%,55%)]">
          Pipeline failed
        </div>
      )}

      {status === "completed" && (
        <div className="mt-4 text-sm font-mono text-[hsl(145,65%,42%)]">
          Pipeline complete — click a node to inspect output
        </div>
      )}
    </div>
  );
}

export { PIPELINE_NODES };
