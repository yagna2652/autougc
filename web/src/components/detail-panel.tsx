"use client";

import { X } from "lucide-react";
import { NODE_DEFINITIONS, INPUT_NODE } from "@/lib/nodes";
import { InputForm } from "./left-sidebar";
import type { NodeState, PipelineStatus } from "@/hooks/use-pipeline";

interface DetailPanelProps {
  selectedNode: string | null;
  nodeStates: Record<string, NodeState>;
  onClose: () => void;
  // Input form props
  videoUrl: string;
  setVideoUrl: (url: string) => void;
  videoModel: "sora" | "kling" | "kling-v3";
  setVideoModel: (model: "sora" | "kling" | "kling-v3") => void;
  productImages: string[];
  handleImageUpload: (files: FileList | null) => void;
  removeImage: (index: number) => void;
  pipelineStatus: PipelineStatus;
  startPipeline: () => void;
  resetPipeline: () => void;
  error: string | null;
}

function FieldRow({
  label,
  value,
}: {
  label: string;
  value: string | number | null | undefined;
}) {
  if (!value && value !== 0) return null;
  return (
    <div style={{ marginBottom: 12 }}>
      <div
        style={{
          color: "#555",
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div style={{ color: "#d4d4d4", fontSize: 13, lineHeight: 1.5 }}>
        {String(value)}
      </div>
    </div>
  );
}

function NodeOutputContent({
  nodeId,
  nodeState,
}: {
  nodeId: string;
  nodeState: NodeState | undefined;
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

  // node-specific rendering
  if (nodeId === "download_video") {
    return (
      <div>
        <FieldRow label="Video Path" value={output.video_path as string} />
        <div
          style={{
            marginTop: 8,
            padding: "8px 12px",
            background: "rgba(34,197,94,0.06)",
            border: "1px solid rgba(34,197,94,0.15)",
            borderRadius: 7,
            color: "#86efac",
            fontSize: 12,
          }}
        >
          Video downloaded successfully
        </div>
      </div>
    );
  }

  if (nodeId === "extract_frames") {
    const count = output.frame_count as number;
    return (
      <div>
        <FieldRow label="Frames Extracted" value={count} />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 4,
          }}
        >
          {Array.from({ length: Math.min(count || 0, 8) }).map((_, i) => (
            <div
              key={i}
              style={{
                width: 28,
                height: 20,
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 3,
              }}
            />
          ))}
          {(count || 0) > 8 && (
            <span style={{ color: "#555", fontSize: 11 }}>+{count - 8} more</span>
          )}
        </div>
      </div>
    );
  }

  if (nodeId === "analyze_video") {
    const analysis = output.video_analysis as Record<string, unknown> | null;
    if (!analysis) return <div style={{ color: "#444", fontSize: 13 }}>No analysis data</div>;
    return (
      <div>
        <FieldRow label="Setting" value={analysis.setting as string} />
        <FieldRow label="Lighting" value={analysis.lighting as string} />
        <FieldRow label="Style" value={analysis.style as string} />
        <FieldRow label="Energy" value={analysis.energy as string} />
        <FieldRow label="Mood" value={analysis.mood as string} />
        <FieldRow label="Actions" value={analysis.actions as string} />
        {!!analysis.camera && (
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                color: "#555",
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.07em",
                textTransform: "uppercase",
                marginBottom: 4,
              }}
            >
              Camera
            </div>
            <div style={{ color: "#d4d4d4", fontSize: 13, lineHeight: 1.5 }}>
              {Object.entries(analysis.camera as Record<string, string>)
                .map(([k, v]) => `${k}: ${v}`)
                .join(" · ")}
            </div>
          </div>
        )}
        {!!analysis.what_makes_it_work && (
          <FieldRow label="What Makes It Work" value={analysis.what_makes_it_work as string} />
        )}
      </div>
    );
  }

  if (nodeId === "generate_prompt") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {!!output.video_prompt && (
          <div>
            <div
              style={{
                color: "#555",
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.07em",
                textTransform: "uppercase",
                marginBottom: 6,
              }}
            >
              Video Prompt
            </div>
            <div
              style={{
                background: "#0d0d0d",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 8,
                padding: "10px 12px",
                color: "#d4d4d4",
                fontSize: 12,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {output.video_prompt as string}
            </div>
          </div>
        )}
        {!!output.suggested_script && (
          <div>
            <div
              style={{
                color: "#555",
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.07em",
                textTransform: "uppercase",
                marginBottom: 6,
              }}
            >
              Script
            </div>
            <div
              style={{
                background: "#0d0d0d",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 8,
                padding: "10px 12px",
                color: "#d4d4d4",
                fontSize: 12,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
              }}
            >
              {output.suggested_script as string}
            </div>
          </div>
        )}
        {!!output.scene_description && (
          <div>
            <div
              style={{
                color: "#555",
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.07em",
                textTransform: "uppercase",
                marginBottom: 6,
              }}
            >
              Scene Description
            </div>
            <div
              style={{
                color: "#d4d4d4",
                fontSize: 13,
                lineHeight: 1.5,
              }}
            >
              {output.scene_description as string}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (nodeId === "generate_scene_image") {
    const url = output.scene_image_url as string;
    if (!url) return <div style={{ color: "#444", fontSize: 13 }}>No image URL</div>;
    return (
      <div>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt="Generated scene"
          style={{
            width: "100%",
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.07)",
            marginBottom: 12,
          }}
        />
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "7px 14px",
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 7,
            color: "#f0f0f0",
            fontSize: 12,
            textDecoration: "none",
            transition: "background 0.15s",
          }}
        >
          Open full image ↗
        </a>
      </div>
    );
  }

  if (nodeId === "generate_video") {
    const videoUrl = output.generated_video_url as string;
    const i2vUrl = output.i2v_image_url as string;
    if (!videoUrl) return <div style={{ color: "#444", fontSize: 13 }}>No video URL yet</div>;
    return (
      <div>
        <video
          src={videoUrl}
          controls
          style={{
            width: "100%",
            borderRadius: 10,
            border: "1px solid rgba(255,255,255,0.07)",
            marginBottom: 12,
            background: "#000",
          }}
        />
        <div style={{ display: "flex", gap: 8 }}>
          <a
            href={videoUrl}
            download
            style={{
              flex: 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              padding: "8px 0",
              background: "#3b82f6",
              border: "none",
              borderRadius: 7,
              color: "#fff",
              fontSize: 12,
              fontWeight: 500,
              textDecoration: "none",
              cursor: "pointer",
            }}
          >
            Download Video
          </a>
          <a
            href={videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "8px 14px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: 7,
              color: "#f0f0f0",
              fontSize: 12,
              textDecoration: "none",
            }}
          >
            Open ↗
          </a>
        </div>
        {i2vUrl && (
          <div style={{ marginTop: 16 }}>
            <div
              style={{
                color: "#555",
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.07em",
                textTransform: "uppercase",
                marginBottom: 6,
              }}
            >
              Reference Image Used
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={i2vUrl}
              alt="I2V reference"
              style={{
                width: 80,
                height: 80,
                objectFit: "cover",
                borderRadius: 6,
                border: "1px solid rgba(255,255,255,0.08)",
              }}
            />
          </div>
        )}
      </div>
    );
  }

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

export function DetailPanel({
  selectedNode,
  nodeStates,
  onClose,
  videoUrl,
  setVideoUrl,
  videoModel,
  setVideoModel,
  productImages,
  handleImageUpload,
  removeImage,
  pipelineStatus,
  startPipeline,
  resetPipeline,
  error,
}: DetailPanelProps) {
  const isOpen = selectedNode !== null;

  const allNodes = [INPUT_NODE, ...NODE_DEFINITIONS];
  const nodeDef = allNodes.find((n) => n.id === selectedNode);
  const nodeState = selectedNode ? nodeStates[selectedNode] : undefined;

  return (
    <div
      style={{
        width: 380,
        flexShrink: 0,
        height: "100vh",
        background: "#141414",
        borderLeft: "1px solid rgba(255,255,255,0.07)",
        display: "flex",
        flexDirection: "column",
        transform: isOpen ? "translateX(0)" : "translateX(100%)",
        transition: "transform 0.28s cubic-bezier(0.4, 0, 0.2, 1)",
        position: "fixed",
        right: 0,
        top: 0,
        zIndex: 10,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ color: "#f0f0f0", fontSize: 14, fontWeight: 600 }}>
            {nodeDef?.label ?? "Details"}
          </div>
          {nodeDef && selectedNode !== "input" && nodeState && (
            <div
              style={{
                color:
                  nodeState.status === "running"
                    ? "#93c5fd"
                    : nodeState.status === "done"
                    ? "#86efac"
                    : nodeState.status === "failed"
                    ? "#fca5a5"
                    : "#555",
                fontSize: 11,
                marginTop: 2,
                textTransform: "capitalize",
              }}
            >
              {nodeState.status}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#555",
            cursor: "pointer",
            padding: 4,
            borderRadius: 6,
            display: "flex",
            alignItems: "center",
            transition: "color 0.15s",
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.color = "#f0f0f0")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.color = "#555")
          }
        >
          <X size={16} />
        </button>
      </div>

      {/* Body */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px",
        }}
      >
        {selectedNode === "input" ? (
          <InputForm
            videoUrl={videoUrl}
            setVideoUrl={setVideoUrl}
            videoModel={videoModel}
            setVideoModel={setVideoModel}
            productImages={productImages}
            handleImageUpload={handleImageUpload}
            removeImage={removeImage}
            pipelineStatus={pipelineStatus}
            startPipeline={startPipeline}
            resetPipeline={resetPipeline}
            error={error}
          />
        ) : selectedNode ? (
          <NodeOutputContent nodeId={selectedNode} nodeState={nodeState} />
        ) : null}
      </div>
    </div>
  );
}
