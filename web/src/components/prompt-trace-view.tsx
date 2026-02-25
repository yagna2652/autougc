"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export interface PromptTrace {
  trace_id: string;
  job_id: string | null;
  template_hash: string;
  template_version: number;
  assembled_prompt: string;
  model: string;
  inputs_snapshot: {
    video_analysis?: Record<string, unknown>;
    product_description?: string;
    product_mechanics?: string;
  } | null;
  raw_response: string | null;
  processed_output: {
    video_prompt?: string;
    suggested_script?: string;
    scene_description?: string;
  } | null;
  token_usage: { input_tokens?: number; output_tokens?: number } | null;
  latency_ms: number | null;
  created_at: string;
}

function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: 12 }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          background: "none",
          border: "none",
          color: "#999",
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          cursor: "pointer",
          padding: "4px 0",
        }}
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {title}
      </button>
      {open && <div style={{ marginTop: 6 }}>{children}</div>}
    </div>
  );
}

function MonoBox({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: "#0d0d0d",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: "10px 12px",
        color: "#d4d4d4",
        fontSize: 11,
        lineHeight: 1.6,
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        maxHeight: 400,
        overflowY: "auto",
        fontFamily: "monospace",
      }}
    >
      {children}
    </div>
  );
}

export function PromptTraceView({ trace }: { trace: PromptTrace }) {
  const tokens = trace.token_usage;
  const totalTokens =
    (tokens?.input_tokens || 0) + (tokens?.output_tokens || 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Header row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: 10,
            color: "#93c5fd",
            background: "rgba(59,130,246,0.1)",
            padding: "2px 7px",
            borderRadius: 4,
            fontWeight: 600,
          }}
        >
          v{trace.template_version}
        </span>
        <span style={{ fontSize: 11, color: "#888" }}>{trace.model}</span>
        {trace.latency_ms != null && (
          <span style={{ fontSize: 10, color: "#666" }}>
            {(trace.latency_ms / 1000).toFixed(1)}s
          </span>
        )}
        {totalTokens > 0 && (
          <span style={{ fontSize: 10, color: "#666" }}>
            {totalTokens.toLocaleString()} tok
          </span>
        )}
        <span style={{ fontSize: 10, color: "#555", marginLeft: "auto" }}>
          {new Date(trace.created_at).toLocaleString()}
        </span>
      </div>

      {/* Assembled prompt */}
      <CollapsibleSection title="Assembled Prompt">
        <MonoBox>{trace.assembled_prompt}</MonoBox>
      </CollapsibleSection>

      {/* Inputs snapshot */}
      {trace.inputs_snapshot && (
        <CollapsibleSection title="Inputs Snapshot">
          {trace.inputs_snapshot.video_analysis && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  color: "#666",
                  fontSize: 10,
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Video Analysis
              </div>
              <MonoBox>
                {JSON.stringify(trace.inputs_snapshot.video_analysis, null, 2)}
              </MonoBox>
            </div>
          )}
          {trace.inputs_snapshot.product_description && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  color: "#666",
                  fontSize: 10,
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Product Description
              </div>
              <MonoBox>{trace.inputs_snapshot.product_description}</MonoBox>
            </div>
          )}
          {trace.inputs_snapshot.product_mechanics && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  color: "#666",
                  fontSize: 10,
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Product Mechanics
              </div>
              <MonoBox>{trace.inputs_snapshot.product_mechanics}</MonoBox>
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* Raw response */}
      {trace.raw_response && (
        <CollapsibleSection title="Raw Response">
          <MonoBox>{trace.raw_response}</MonoBox>
        </CollapsibleSection>
      )}

      {/* Processed output */}
      {trace.processed_output && (
        <CollapsibleSection title="Processed Output" defaultOpen>
          {trace.processed_output.video_prompt && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  color: "#666",
                  fontSize: 10,
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Video Prompt
              </div>
              <MonoBox>{trace.processed_output.video_prompt}</MonoBox>
            </div>
          )}
          {trace.processed_output.suggested_script && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  color: "#666",
                  fontSize: 10,
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Script
              </div>
              <MonoBox>{trace.processed_output.suggested_script}</MonoBox>
            </div>
          )}
          {trace.processed_output.scene_description && (
            <div style={{ marginBottom: 8 }}>
              <div
                style={{
                  color: "#666",
                  fontSize: 10,
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Scene Description
              </div>
              <MonoBox>{trace.processed_output.scene_description}</MonoBox>
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* Token breakdown */}
      {tokens && (tokens.input_tokens || tokens.output_tokens) && (
        <div
          style={{
            display: "flex",
            gap: 16,
            fontSize: 10,
            color: "#666",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            paddingTop: 8,
          }}
        >
          <span>Input: {(tokens.input_tokens || 0).toLocaleString()}</span>
          <span>Output: {(tokens.output_tokens || 0).toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}
