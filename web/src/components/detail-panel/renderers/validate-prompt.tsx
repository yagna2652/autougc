"use client";

import { useState, useRef } from "react";
import type { NodeOutputRendererProps } from "../node-renderers";

export function ValidatePromptOutput({
  output,
  pipelineStatus,
  resumePipeline,
}: NodeOutputRendererProps) {
  const isPaused = pipelineStatus === "paused";
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
    resumePipeline?.(promptChanged ? editedPrompt.trim() : undefined);
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
          {Array.isArray(validation.issues) && validation.issues.length > 0 && (
            <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
              {(validation.issues as Array<string | Record<string, unknown>>).map((issue, i) => {
                const text =
                  typeof issue === "string"
                    ? issue
                    : (issue.description as string) ?? JSON.stringify(issue);
                return (
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
                    {text}
                  </div>
                );
              })}
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
