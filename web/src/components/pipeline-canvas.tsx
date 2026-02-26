"use client";

import { useRef, useCallback } from "react";
import { PipelineNode } from "./pipeline-node";
import { NODE_DEFINITIONS, INPUT_NODE } from "@/lib/nodes";
import type { NodeState, PipelineStatus } from "@/hooks/use-pipeline";

interface PipelineCanvasProps {
  nodeStates: Record<string, NodeState>;
  selectedNode: string | null;
  pipelineStatus: PipelineStatus;
  onSelectNode: (id: string) => void;
}

function ArrowConnector({ isActive, isPaused }: { isActive: boolean; isPaused?: boolean }) {
  const color = isPaused ? "#f59e0b" : isActive ? "#3b82f6" : "rgba(255,255,255,0.1)";
  return (
    <svg
      width="48"
      height="110"
      viewBox="0 0 48 110"
      style={{ flexShrink: 0, overflow: "visible" }}
    >
      <line
        x1="0"
        y1="55"
        x2="36"
        y2="55"
        stroke={color}
        strokeWidth="1.5"
        strokeDasharray={isActive || isPaused ? "4 4" : undefined}
        style={
          isActive
            ? { animation: "dash-flow 0.5s linear infinite" }
            : undefined
        }
      />
      <polygon points="33,51 44,55 33,59" fill={color} />
      {isPaused && (
        <>
          <rect x="16" y="48" width="3" height="14" rx="1" fill="#f59e0b" />
          <rect x="22" y="48" width="3" height="14" rx="1" fill="#f59e0b" />
        </>
      )}
    </svg>
  );
}

export function PipelineCanvas({
  nodeStates,
  selectedNode,
  pipelineStatus,
  onSelectNode,
}: PipelineCanvasProps) {
  const allNodes = [INPUT_NODE, ...NODE_DEFINITIONS];
  const containerRef = useRef<HTMLDivElement>(null);
  const dragState = useRef({ active: false, startX: 0, scrollLeft: 0, moved: false });

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    const el = containerRef.current;
    if (!el) return;
    // Only primary button (left click)
    if (e.button !== 0) return;
    dragState.current = { active: true, startX: e.clientX, scrollLeft: el.scrollLeft, moved: false };
    el.setPointerCapture(e.pointerId);
    el.style.cursor = "grabbing";
  }, []);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    const ds = dragState.current;
    if (!ds.active) return;
    const dx = e.clientX - ds.startX;
    if (Math.abs(dx) > 3) ds.moved = true;
    containerRef.current!.scrollLeft = ds.scrollLeft - dx;
  }, []);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    const ds = dragState.current;
    if (!ds.active) return;
    ds.active = false;
    const el = containerRef.current!;
    el.releasePointerCapture(e.pointerId);
    el.style.cursor = "grab";
  }, []);

  function getInputNodeStatus() {
    if (pipelineStatus === "idle") return "input-idle" as const;
    return "input-configured" as const;
  }

  return (
    <div
      ref={containerRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        minHeight: "100vh",
        overflowX: "auto",
        overflowY: "hidden",
        padding: "0 48px",
        cursor: "grab",
        userSelect: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexShrink: 0,
          margin: "0 auto",
        }}
      >
        {allNodes.map((node, index) => {
          const isInput = node.id === "input";
          const nodeState = isInput ? null : nodeStates[node.id];
          const status = isInput
            ? getInputNodeStatus()
            : (nodeState?.status ?? "idle");

          const nextNode = allNodes[index + 1];
          const isLast = index === allNodes.length - 1;

          // Arrow is active when the node after this one is running
          const nextNodeState = nextNode
            ? nextNode.id === "input"
              ? null
              : nodeStates[nextNode.id]
            : null;
          const arrowActive = nextNodeState?.status === "running";

          // Arrow between validate_prompt and generate_scene_image shows pause indicator
          const arrowPaused =
            pipelineStatus === "paused" &&
            node.id === "validate_prompt" &&
            nextNode?.id === "generate_scene_image";

          return (
            <div
              key={node.id}
              style={{ display: "flex", alignItems: "center" }}
            >
              <PipelineNode
                id={node.id}
                label={node.label}
                description={node.description}
                iconName={node.iconName}
                status={status}
                isSelected={selectedNode === node.id}
                onClick={() => {
                  if (!dragState.current.moved) onSelectNode(node.id);
                }}
              />
              {!isLast && <ArrowConnector isActive={arrowActive} isPaused={arrowPaused} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
