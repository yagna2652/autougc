"use client";

import {
  Download,
  Layers,
  ScanEye,
  Sparkles,
  ImagePlus,
  Clapperboard,
  Zap,
  LucideProps,
} from "lucide-react";
import type { NodeStatus } from "@/hooks/use-pipeline";

type IconName =
  | "Download"
  | "Layers"
  | "ScanEye"
  | "Sparkles"
  | "ImagePlus"
  | "Clapperboard"
  | "Zap";

const ICONS: Record<IconName, React.ComponentType<LucideProps>> = {
  Download,
  Layers,
  ScanEye,
  Sparkles,
  ImagePlus,
  Clapperboard,
  Zap,
};

interface PipelineNodeProps {
  id: string;
  label: string;
  description: string;
  iconName: string;
  status: NodeStatus | "input-idle" | "input-configured";
  isSelected: boolean;
  onClick: () => void;
}

const STATUS_STYLES: Record<
  string,
  { border: string; dot: string; glow: string; label: string }
> = {
  idle: {
    border: "rgba(255,255,255,0.07)",
    dot: "#333",
    glow: "none",
    label: "#555",
  },
  running: {
    border: "#3b82f6",
    dot: "#3b82f6",
    glow: "0 0 20px rgba(59,130,246,0.25)",
    label: "#93c5fd",
  },
  done: {
    border: "rgba(34,197,94,0.4)",
    dot: "#22c55e",
    glow: "0 0 12px rgba(34,197,94,0.12)",
    label: "#86efac",
  },
  failed: {
    border: "rgba(239,68,68,0.4)",
    dot: "#ef4444",
    glow: "0 0 12px rgba(239,68,68,0.12)",
    label: "#fca5a5",
  },
  "input-idle": {
    border: "rgba(255,255,255,0.1)",
    dot: "#444",
    glow: "none",
    label: "#888",
  },
  "input-configured": {
    border: "rgba(34,197,94,0.4)",
    dot: "#22c55e",
    glow: "0 0 12px rgba(34,197,94,0.12)",
    label: "#86efac",
  },
};

export function PipelineNode({
  id,
  label,
  description,
  iconName,
  status,
  isSelected,
  onClick,
}: PipelineNodeProps) {
  const Icon = ICONS[iconName as IconName] ?? Zap;
  const styles = STATUS_STYLES[status] ?? STATUS_STYLES.idle;
  const isRunning = status === "running";

  const selectedOutline = isSelected ? "rgba(255,255,255,0.18)" : styles.border;

  return (
    <button
      onClick={onClick}
      style={{
        width: 180,
        height: 110,
        background: "#111111",
        border: `1px solid ${selectedOutline}`,
        borderRadius: 12,
        padding: "14px 16px",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: 6,
        position: "relative",
        boxShadow: isSelected
          ? `${styles.glow}, 0 0 0 1px rgba(255,255,255,0.08)`
          : styles.glow,
        transition: "border-color 0.2s, box-shadow 0.2s",
        flexShrink: 0,
        outline: "none",
      }}
    >
      {/* Status dot */}
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          width: 7,
          height: 7,
          borderRadius: "50%",
          background: styles.dot,
          animation: isRunning
            ? "pulse-border 1.2s ease-in-out infinite"
            : undefined,
          opacity: isRunning ? 1 : 0.8,
        }}
      />

      {/* Icon */}
      <div
        style={{
          color: isRunning ? "#3b82f6" : status === "done" || status === "input-configured" ? "#22c55e" : "#444",
          transition: "color 0.2s",
        }}
      >
        <Icon size={18} strokeWidth={1.5} />
      </div>

      {/* Label */}
      <div
        style={{
          color: "#f0f0f0",
          fontSize: 13,
          fontWeight: 500,
          lineHeight: 1.2,
          letterSpacing: "-0.01em",
        }}
      >
        {label}
      </div>

      {/* Description */}
      <div
        style={{
          color: styles.label,
          fontSize: 11,
          lineHeight: 1.3,
          transition: "color 0.2s",
        }}
      >
        {isRunning ? "Running…" : description}
      </div>

      {/* Running bar */}
      {isRunning && (
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: 2,
            background:
              "linear-gradient(90deg, transparent 0%, #3b82f6 50%, transparent 100%)",
            borderRadius: "0 0 12px 12px",
            animation: "dash-flow 1.5s linear infinite",
          }}
        />
      )}
    </button>
  );
}
