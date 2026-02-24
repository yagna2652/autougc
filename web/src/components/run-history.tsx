"use client";

import { useState } from "react";
import { History, Plus, X, ChevronLeft, ChevronRight, Trash2 } from "lucide-react";
import type { RunHistoryEntry } from "@/types/pipeline";

interface RunHistoryPanelProps {
  runs: RunHistoryEntry[];
  activeRunId: string | null;
  onSelectRun: (id: string) => void;
  onDeleteRun: (id: string) => void;
  onClearAll: () => void;
  onNewRun: () => void;
}

function formatRelativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function truncateUrl(url: string, max: number = 28): string {
  // Try to show the meaningful part of the URL
  try {
    const parsed = new URL(url);
    const path = parsed.pathname;
    const display = parsed.host + path;
    return display.length > max ? display.slice(0, max) + "..." : display;
  } catch {
    return url.length > max ? url.slice(0, max) + "..." : url;
  }
}

const STATUS_DOT: Record<string, { color: string; pulse: boolean }> = {
  running: { color: "#3b82f6", pulse: true },
  completed: { color: "#22c55e", pulse: false },
  failed: { color: "#ef4444", pulse: false },
};

export function RunHistoryPanel({
  runs,
  activeRunId,
  onSelectRun,
  onDeleteRun,
  onClearAll,
  onNewRun,
}: RunHistoryPanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [hoveredRun, setHoveredRun] = useState<string | null>(null);
  const [hoveredDelete, setHoveredDelete] = useState<string | null>(null);
  const [hoveredNew, setHoveredNew] = useState(false);
  const [hoveredCollapse, setHoveredCollapse] = useState(false);
  const [hoveredClear, setHoveredClear] = useState(false);

  if (collapsed) {
    return (
      <div
        style={{
          width: 48,
          minWidth: 48,
          background: "#0a0a0a",
          borderRight: "1px solid rgba(255,255,255,0.06)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: 14,
          gap: 12,
        }}
      >
        <button
          onClick={() => setCollapsed(false)}
          onMouseEnter={() => setHoveredCollapse(true)}
          onMouseLeave={() => setHoveredCollapse(false)}
          style={{
            background: "none",
            border: "none",
            color: hoveredCollapse ? "#f0f0f0" : "#666",
            cursor: "pointer",
            padding: 6,
            borderRadius: 6,
            transition: "color 0.15s",
          }}
          title="Expand run history"
        >
          <ChevronRight size={16} />
        </button>
        <div style={{ color: "#444", transform: "rotate(-90deg)", whiteSpace: "nowrap" }}>
          <History size={14} />
        </div>
        {runs.length > 0 && (
          <div
            style={{
              width: 18,
              height: 18,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.08)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 10,
              color: "#888",
              fontWeight: 500,
            }}
          >
            {runs.length}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        width: 280,
        minWidth: 280,
        background: "#0a0a0a",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "14px 14px 10px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <History size={14} style={{ color: "#666", flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: "#999", letterSpacing: "0.04em", textTransform: "uppercase", flex: 1 }}>
          History
        </span>

        {runs.length > 0 && (
          <button
            onClick={onClearAll}
            onMouseEnter={() => setHoveredClear(true)}
            onMouseLeave={() => setHoveredClear(false)}
            style={{
              background: "none",
              border: "none",
              color: hoveredClear ? "#ef4444" : "#555",
              cursor: "pointer",
              padding: 4,
              borderRadius: 4,
              transition: "color 0.15s",
              display: "flex",
              alignItems: "center",
            }}
            title="Clear all history"
          >
            <Trash2 size={13} />
          </button>
        )}

        <button
          onClick={onNewRun}
          onMouseEnter={() => setHoveredNew(true)}
          onMouseLeave={() => setHoveredNew(false)}
          style={{
            background: hoveredNew ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#ccc",
            cursor: "pointer",
            padding: "3px 8px",
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            gap: 3,
            transition: "background 0.15s",
          }}
        >
          <Plus size={12} />
          New
        </button>

        <button
          onClick={() => setCollapsed(true)}
          onMouseEnter={() => setHoveredCollapse(true)}
          onMouseLeave={() => setHoveredCollapse(false)}
          style={{
            background: "none",
            border: "none",
            color: hoveredCollapse ? "#f0f0f0" : "#555",
            cursor: "pointer",
            padding: 4,
            borderRadius: 4,
            transition: "color 0.15s",
          }}
          title="Collapse panel"
        >
          <ChevronLeft size={14} />
        </button>
      </div>

      {/* Run list */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "6px 8px",
        }}
      >
        {runs.length === 0 && (
          <div
            style={{
              padding: "32px 16px",
              textAlign: "center",
              color: "#444",
              fontSize: 12,
              lineHeight: 1.5,
            }}
          >
            No runs yet.
            <br />
            Start a pipeline to see history here.
          </div>
        )}

        {runs.map((run) => {
          const dot = STATUS_DOT[run.status] ?? STATUS_DOT.failed;
          const isActive = run.id === activeRunId;
          const isHovered = hoveredRun === run.id;

          return (
            <div
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              onMouseEnter={() => setHoveredRun(run.id)}
              onMouseLeave={() => setHoveredRun(null)}
              style={{
                padding: "10px 10px",
                borderRadius: 8,
                cursor: "pointer",
                background: isActive
                  ? "rgba(255,255,255,0.06)"
                  : isHovered
                  ? "rgba(255,255,255,0.03)"
                  : "transparent",
                border: isActive
                  ? "1px solid rgba(255,255,255,0.1)"
                  : "1px solid transparent",
                marginBottom: 2,
                transition: "background 0.15s, border-color 0.15s",
                position: "relative",
              }}
            >
              {/* Delete button */}
              {isHovered && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteRun(run.id);
                  }}
                  onMouseEnter={() => setHoveredDelete(run.id)}
                  onMouseLeave={() => setHoveredDelete(null)}
                  style={{
                    position: "absolute",
                    top: 8,
                    right: 8,
                    background: "none",
                    border: "none",
                    color: hoveredDelete === run.id ? "#ef4444" : "#555",
                    cursor: "pointer",
                    padding: 2,
                    borderRadius: 4,
                    transition: "color 0.15s",
                    display: "flex",
                    alignItems: "center",
                  }}
                >
                  <X size={12} />
                </button>
              )}

              {/* Top row: status dot + URL */}
              <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <div
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background: dot.color,
                    flexShrink: 0,
                    animation: dot.pulse
                      ? "pulse-border 1.2s ease-in-out infinite"
                      : undefined,
                  }}
                />
                <div
                  style={{
                    fontSize: 12,
                    color: "#d0d0d0",
                    fontWeight: 500,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    flex: 1,
                    paddingRight: isHovered ? 18 : 0,
                  }}
                >
                  {truncateUrl(run.videoUrl)}
                </div>
              </div>

              {/* Bottom row: model + time */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  marginTop: 4,
                  paddingLeft: 14,
                }}
              >
                <span
                  style={{
                    fontSize: 10,
                    color: "#666",
                    fontWeight: 500,
                    textTransform: "uppercase",
                    letterSpacing: "0.03em",
                  }}
                >
                  {run.videoModel}
                </span>
                <span style={{ fontSize: 10, color: "#444" }}>·</span>
                <span style={{ fontSize: 10, color: "#555" }}>
                  {formatRelativeTime(run.startedAt)}
                </span>
              </div>

              {/* Scene thumbnail if available */}
              {run.sceneImageUrl && (
                <div style={{ marginTop: 6, paddingLeft: 14 }}>
                  <img
                    src={run.sceneImageUrl}
                    alt="Scene"
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: 6,
                      objectFit: "cover",
                      border: "1px solid rgba(255,255,255,0.08)",
                    }}
                  />
                </div>
              )}

              {/* Error message */}
              {run.status === "failed" && run.error && (
                <div
                  style={{
                    marginTop: 4,
                    paddingLeft: 14,
                    fontSize: 10,
                    color: "#ef4444",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {run.error}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
