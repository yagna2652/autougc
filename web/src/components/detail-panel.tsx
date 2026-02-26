"use client";

import { useState, useCallback, useRef } from "react";
import { X } from "lucide-react";
import { NODE_DEFINITIONS, INPUT_NODE } from "@/lib/nodes";
import { InputForm } from "./left-sidebar";
import type { NodeState, PipelineStatus } from "@/hooks/use-pipeline";
import { PromptTraceView } from "./prompt-trace-view";
import type { PromptTrace } from "./prompt-trace-view";

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
  identityPack: Record<string, string>;
  handleIdentityImageUpload: (angle: string, file: File) => void;
  removeIdentityImage: (angle: string) => void;
  useIdentityPack: boolean;
  toggleIdentityPack: (enabled: boolean) => void;
  useTailImage: boolean;
  setUseTailImage: (v: boolean) => void;
  falKey: string;
  setFalKey: (key: string) => void;
  pipelineStatus: PipelineStatus;
  startPipeline: () => void;
  resumePipeline: (editedPrompt?: string) => void;
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
      <GeneratePromptOutput output={output} />
    );
  }

  if (nodeId === "validate_prompt") {
    return (
      <ValidatePromptOutput
        output={output}
        isPaused={pipelineStatus === "paused"}
        onResume={resumePipeline}
      />
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

// ---------------------------------------------------------------------------
// Validate Prompt section — editable textarea when paused
// ---------------------------------------------------------------------------

function ValidatePromptOutput({
  output,
  isPaused,
  onResume,
}: {
  output: Record<string, unknown>;
  isPaused: boolean;
  onResume?: (editedPrompt?: string) => void;
}) {
  const validation = output.prompt_validation as Record<string, unknown> | null;
  const videoPrompt = (output.video_prompt as string) ?? "";
  const [editedPrompt, setEditedPrompt] = useState(videoPrompt);
  const [resuming, setResuming] = useState(false);

  // Sync editedPrompt when output changes (e.g. initial load)
  const promptRef = useRef(videoPrompt);
  if (promptRef.current !== videoPrompt) {
    promptRef.current = videoPrompt;
    // Only reset if not currently editing (paused)
    if (!isPaused) setEditedPrompt(videoPrompt);
  }

  const handleContinue = () => {
    setResuming(true);
    const promptChanged = editedPrompt.trim() !== videoPrompt.trim();
    onResume?.(promptChanged ? editedPrompt.trim() : undefined);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Validation results */}
      {validation && (
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
            Validation Result
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 12px",
              background: validation.passed
                ? "rgba(34,197,94,0.06)"
                : "rgba(245,158,11,0.06)",
              border: `1px solid ${validation.passed ? "rgba(34,197,94,0.15)" : "rgba(245,158,11,0.2)"}`,
              borderRadius: 7,
              fontSize: 12,
              color: validation.passed ? "#86efac" : "#fbbf24",
            }}
          >
            {validation.passed ? "Passed" : "Issues found"}
            {!!validation.rewritten && (
              <span style={{ color: "#93c5fd", fontSize: 11 }}>(prompt was rewritten)</span>
            )}
          </div>
          {Array.isArray(validation.issues) && (validation.issues as string[]).length > 0 && (
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
              {(validation.issues as string[]).map((issue, i) => (
                <div
                  key={i}
                  style={{
                    color: "#fbbf24",
                    fontSize: 11,
                    padding: "4px 8px",
                    background: "rgba(245,158,11,0.04)",
                    borderRadius: 4,
                  }}
                >
                  {issue}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Video prompt — editable when paused, read-only otherwise */}
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
        {isPaused ? (
          <>
            <textarea
              value={editedPrompt}
              onChange={(e) => setEditedPrompt(e.target.value)}
              style={{
                width: "100%",
                minHeight: 180,
                background: "#0d0d0d",
                border: "1px solid rgba(245,158,11,0.3)",
                borderRadius: 8,
                padding: "10px 12px",
                color: "#d4d4d4",
                fontSize: 12,
                lineHeight: 1.6,
                resize: "vertical",
                outline: "none",
                fontFamily: "inherit",
                boxSizing: "border-box",
              }}
            />
            <div style={{ color: "#666", fontSize: 11, marginTop: 6, lineHeight: 1.4 }}>
              Review and edit the video prompt, then continue to generate
            </div>
            <button
              onClick={handleContinue}
              disabled={resuming || !editedPrompt.trim()}
              style={{
                width: "100%",
                marginTop: 12,
                padding: "11px 0",
                borderRadius: 8,
                border: "none",
                background: resuming || !editedPrompt.trim() ? "rgba(245,158,11,0.2)" : "#f59e0b",
                color: resuming || !editedPrompt.trim() ? "rgba(255,255,255,0.4)" : "#000",
                fontSize: 13,
                fontWeight: 600,
                cursor: resuming || !editedPrompt.trim() ? "default" : "pointer",
                transition: "all 0.15s",
                letterSpacing: "0.01em",
              }}
            >
              {resuming ? "Resuming..." : "Continue Pipeline"}
            </button>
          </>
        ) : (
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
            {videoPrompt || "No prompt available"}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Generate Prompt section with trace viewer + compare
// ---------------------------------------------------------------------------

interface TraceSummary {
  trace_id: string;
  job_id: string | null;
  template_version: number;
  model: string;
  latency_ms: number | null;
  created_at: string;
}

function GeneratePromptOutput({ output }: { output: Record<string, unknown> }) {
  const [traceData, setTraceData] = useState<PromptTrace | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceOpen, setTraceOpen] = useState(false);

  // Compare state
  const [compareList, setCompareList] = useState<TraceSummary[] | null>(null);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareTrace, setCompareTrace] = useState<PromptTrace | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const traceId = output.trace_id as string | undefined;

  const loadTrace = useCallback(async () => {
    if (!traceId || traceData) return;
    setTraceLoading(true);
    try {
      const res = await fetch(`/api/prompts?action=trace&traceId=${traceId}`);
      if (res.ok) {
        const data = await res.json();
        setTraceData(data);
      }
    } catch {
      // non-fatal
    } finally {
      setTraceLoading(false);
    }
  }, [traceId, traceData]);

  const handleTraceToggle = () => {
    if (!traceOpen) loadTrace();
    setTraceOpen(!traceOpen);
  };

  const loadCompareList = useCallback(async () => {
    if (compareList) return;
    try {
      const res = await fetch("/api/prompts?action=list&limit=20");
      if (res.ok) {
        const data = await res.json();
        setCompareList(
          (data.traces || []).filter(
            (t: TraceSummary) => t.trace_id !== traceId,
          ),
        );
      }
    } catch {
      // non-fatal
    }
  }, [compareList, traceId]);

  const handleCompareSelect = async (otherTraceId: string) => {
    setCompareLoading(true);
    try {
      const res = await fetch(
        `/api/prompts?action=trace&traceId=${otherTraceId}`,
      );
      if (res.ok) {
        const data = await res.json();
        setCompareTrace(data);
      }
    } catch {
      // non-fatal
    } finally {
      setCompareLoading(false);
    }
  };

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

      {/* Trace viewer section */}
      {traceId && (
        <div
          style={{
            borderTop: "1px solid rgba(255,255,255,0.06)",
            paddingTop: 12,
          }}
        >
          <button
            onClick={handleTraceToggle}
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 6,
              padding: "6px 12px",
              color: "#93c5fd",
              fontSize: 11,
              fontWeight: 500,
              cursor: "pointer",
              transition: "background 0.15s",
              width: "100%",
              textAlign: "left",
            }}
          >
            {traceOpen ? "Hide Full Trace" : "View Full Trace"}
          </button>

          {traceOpen && (
            <div style={{ marginTop: 12 }}>
              {traceLoading && (
                <div style={{ color: "#666", fontSize: 12 }}>Loading trace...</div>
              )}
              {traceData && <PromptTraceView trace={traceData} />}
            </div>
          )}

          {/* Compare dropdown */}
          <div style={{ marginTop: 8 }}>
            <button
              onClick={() => {
                setCompareOpen(!compareOpen);
                if (!compareOpen) loadCompareList();
              }}
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 6,
                padding: "6px 12px",
                color: "#a78bfa",
                fontSize: 11,
                fontWeight: 500,
                cursor: "pointer",
                transition: "background 0.15s",
                width: "100%",
                textAlign: "left",
              }}
            >
              {compareOpen ? "Hide Compare" : "Compare with..."}
            </button>

            {compareOpen && (
              <div style={{ marginTop: 8 }}>
                {!compareList && (
                  <div style={{ color: "#666", fontSize: 11 }}>
                    Loading traces...
                  </div>
                )}
                {compareList && compareList.length === 0 && (
                  <div style={{ color: "#666", fontSize: 11 }}>
                    No other traces to compare with.
                  </div>
                )}
                {compareList && compareList.length > 0 && (
                  <div
                    style={{
                      maxHeight: 160,
                      overflowY: "auto",
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                    }}
                  >
                    {compareList.map((t) => (
                      <button
                        key={t.trace_id}
                        onClick={() => handleCompareSelect(t.trace_id)}
                        style={{
                          background:
                            compareTrace?.trace_id === t.trace_id
                              ? "rgba(167,139,250,0.12)"
                              : "rgba(255,255,255,0.03)",
                          border: "1px solid rgba(255,255,255,0.06)",
                          borderRadius: 6,
                          padding: "6px 10px",
                          color: "#d4d4d4",
                          fontSize: 11,
                          cursor: "pointer",
                          textAlign: "left",
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 9,
                            color: "#93c5fd",
                            background: "rgba(59,130,246,0.1)",
                            padding: "1px 5px",
                            borderRadius: 3,
                            fontWeight: 600,
                          }}
                        >
                          v{t.template_version}
                        </span>
                        <span style={{ color: "#888", fontSize: 10 }}>
                          {t.model}
                        </span>
                        <span
                          style={{
                            color: "#555",
                            fontSize: 10,
                            marginLeft: "auto",
                          }}
                        >
                          {new Date(t.created_at).toLocaleString()}
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {compareLoading && (
                  <div style={{ color: "#666", fontSize: 11, marginTop: 8 }}>
                    Loading comparison trace...
                  </div>
                )}
                {compareTrace && (
                  <div
                    style={{
                      marginTop: 12,
                      borderTop: "1px solid rgba(167,139,250,0.15)",
                      paddingTop: 12,
                    }}
                  >
                    <div
                      style={{
                        color: "#a78bfa",
                        fontSize: 10,
                        fontWeight: 600,
                        letterSpacing: "0.07em",
                        textTransform: "uppercase",
                        marginBottom: 8,
                      }}
                    >
                      Comparison Trace
                    </div>
                    <PromptTraceView trace={compareTrace} />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
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
  identityPack,
  handleIdentityImageUpload,
  removeIdentityImage,
  useIdentityPack,
  toggleIdentityPack,
  useTailImage,
  setUseTailImage,
  falKey,
  setFalKey,
  pipelineStatus,
  startPipeline,
  resumePipeline,
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
            identityPack={identityPack}
            handleIdentityImageUpload={handleIdentityImageUpload}
            removeIdentityImage={removeIdentityImage}
            useIdentityPack={useIdentityPack}
            toggleIdentityPack={toggleIdentityPack}
            useTailImage={useTailImage}
            setUseTailImage={setUseTailImage}
            falKey={falKey}
            setFalKey={setFalKey}
            pipelineStatus={pipelineStatus}
            startPipeline={startPipeline}
            resetPipeline={resetPipeline}
            error={error}
          />
        ) : selectedNode ? (
          <NodeOutputContent
            nodeId={selectedNode}
            nodeState={nodeState}
            pipelineStatus={pipelineStatus}
            resumePipeline={resumePipeline}
          />
        ) : null}
      </div>
    </div>
  );
}
