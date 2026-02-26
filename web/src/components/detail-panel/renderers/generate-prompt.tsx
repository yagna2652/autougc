"use client";

import { useState, useCallback } from "react";
import { PromptTraceView } from "../../prompt-trace-view";
import type { PromptTrace } from "../../prompt-trace-view";
import type { NodeOutputRendererProps } from "../node-renderers";

interface TraceSummary {
  trace_id: string;
  job_id: string | null;
  template_version: number;
  model: string;
  latency_ms: number | null;
  created_at: string;
}

export function GeneratePromptOutput({ output }: NodeOutputRendererProps) {
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
