"use client";

import { useRef } from "react";
import type { PipelineStatus } from "@/hooks/use-pipeline";

interface InputFormProps {
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

export function InputForm({
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
}: InputFormProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isRunning = pipelineStatus === "running";
  const isDone = pipelineStatus === "completed" || pipelineStatus === "failed";

  const inputStyle: React.CSSProperties = {
    width: "100%",
    background: "#0d0d0d",
    border: "1px solid rgba(255,255,255,0.09)",
    borderRadius: 8,
    padding: "9px 12px",
    color: "#f0f0f0",
    fontSize: 13,
    outline: "none",
    transition: "border-color 0.15s",
    boxSizing: "border-box",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    color: "#888",
    fontSize: 11,
    fontWeight: 500,
    letterSpacing: "0.05em",
    textTransform: "uppercase",
    marginBottom: 6,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div>
        <div style={{ color: "#f0f0f0", fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
          Configure Pipeline
        </div>
        <div style={{ color: "#555", fontSize: 12 }}>
          Enter a TikTok or Reel URL to analyze
        </div>
      </div>

      {/* Video URL */}
      <div>
        <label style={labelStyle}>Source Video URL</label>
        <input
          type="url"
          placeholder="https://www.tiktok.com/@..."
          value={videoUrl}
          onChange={(e) => setVideoUrl(e.target.value)}
          disabled={isRunning}
          style={{
            ...inputStyle,
            opacity: isRunning ? 0.5 : 1,
          }}
          onFocus={(e) => {
            e.target.style.borderColor = "rgba(255,255,255,0.2)";
          }}
          onBlur={(e) => {
            e.target.style.borderColor = "rgba(255,255,255,0.09)";
          }}
        />
      </div>

      {/* Product Images */}
      <div>
        <label style={labelStyle}>Product Images</label>
        <div
          onClick={() => !isRunning && fileInputRef.current?.click()}
          style={{
            border: "1px dashed rgba(255,255,255,0.12)",
            borderRadius: 8,
            padding: "12px 16px",
            cursor: isRunning ? "default" : "pointer",
            textAlign: "center",
            color: "#555",
            fontSize: 12,
            transition: "border-color 0.15s, color 0.15s",
            opacity: isRunning ? 0.5 : 1,
          }}
          onMouseEnter={(e) => {
            if (!isRunning) {
              (e.currentTarget as HTMLDivElement).style.borderColor =
                "rgba(255,255,255,0.25)";
              (e.currentTarget as HTMLDivElement).style.color = "#888";
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLDivElement).style.borderColor =
              "rgba(255,255,255,0.12)";
            (e.currentTarget as HTMLDivElement).style.color = "#555";
          }}
        >
          {productImages.length === 0
            ? "Click to upload product images (optional)"
            : `${productImages.length} image${productImages.length > 1 ? "s" : ""} selected — click to add more`}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={(e) => handleImageUpload(e.target.files)}
        />

        {productImages.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginTop: 10,
            }}
          >
            {productImages.map((img, i) => (
              <div
                key={i}
                style={{ position: "relative", width: 56, height: 56 }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img}
                  alt={`Product ${i + 1}`}
                  style={{
                    width: 56,
                    height: 56,
                    objectFit: "cover",
                    borderRadius: 6,
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                />
                {!isRunning && (
                  <button
                    onClick={() => removeImage(i)}
                    style={{
                      position: "absolute",
                      top: -4,
                      right: -4,
                      width: 16,
                      height: 16,
                      borderRadius: "50%",
                      background: "#ef4444",
                      border: "none",
                      color: "#fff",
                      fontSize: 10,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      lineHeight: 1,
                    }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Video Model */}
      <div>
        <label style={labelStyle}>Video Model</label>
        <div style={{ display: "flex", gap: 8 }}>
          {(["sora", "kling", "kling-v3"] as const).map((m) => (
            <button
              key={m}
              onClick={() => !isRunning && setVideoModel(m)}
              disabled={isRunning}
              style={{
                flex: 1,
                padding: "8px 0",
                borderRadius: 7,
                border: `1px solid ${videoModel === m ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.07)"}`,
                background: videoModel === m ? "rgba(255,255,255,0.06)" : "transparent",
                color: videoModel === m ? "#f0f0f0" : "#555",
                fontSize: 12,
                fontWeight: videoModel === m ? 500 : 400,
                cursor: isRunning ? "default" : "pointer",
                transition: "all 0.15s",
                opacity: isRunning ? 0.5 : 1,
              }}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.25)",
            borderRadius: 8,
            padding: "10px 12px",
            color: "#fca5a5",
            fontSize: 12,
          }}
        >
          {error}
        </div>
      )}

      {/* Action button */}
      {isDone ? (
        <button
          onClick={resetPipeline}
          style={{
            width: "100%",
            padding: "11px 0",
            borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.1)",
            background: "rgba(255,255,255,0.04)",
            color: "#f0f0f0",
            fontSize: 13,
            fontWeight: 500,
            cursor: "pointer",
            transition: "all 0.15s",
          }}
        >
          Run Again
        </button>
      ) : (
        <button
          onClick={startPipeline}
          disabled={isRunning || !videoUrl.trim()}
          style={{
            width: "100%",
            padding: "11px 0",
            borderRadius: 8,
            border: "none",
            background:
              isRunning || !videoUrl.trim()
                ? "rgba(59,130,246,0.2)"
                : "#3b82f6",
            color: isRunning || !videoUrl.trim() ? "rgba(255,255,255,0.4)" : "#fff",
            fontSize: 13,
            fontWeight: 600,
            cursor: isRunning || !videoUrl.trim() ? "default" : "pointer",
            transition: "all 0.15s",
            letterSpacing: "0.01em",
          }}
        >
          {isRunning ? "Running…" : "Run Pipeline"}
        </button>
      )}
    </div>
  );
}
