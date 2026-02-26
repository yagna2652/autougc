"use client";

import { useRef } from "react";
import type { PipelineStatus } from "@/hooks/use-pipeline";

const IDENTITY_ANGLES = [
  { key: "front", label: "Front" },
  { key: "side_45", label: "45°" },
  { key: "back", label: "Back" },
  { key: "top", label: "Top" },
  { key: "close_up_logo", label: "Logo" },
  { key: "close_up_material", label: "Material" },
] as const;

interface InputFormProps {
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
  resetPipeline,
  error,
}: InputFormProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const angleInputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const isRunning = pipelineStatus === "running";
  const isPaused = pipelineStatus === "paused";
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
          style={{ ...inputStyle, opacity: isRunning ? 0.5 : 1 }}
          onFocus={(e) => { e.target.style.borderColor = "rgba(255,255,255,0.2)"; }}
          onBlur={(e) => { e.target.style.borderColor = "rgba(255,255,255,0.09)"; }}
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
              (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.25)";
              (e.currentTarget as HTMLDivElement).style.color = "#888";
            }
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.12)";
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
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 10 }}>
            {productImages.map((img, i) => (
              <div key={i} style={{ position: "relative", width: 56, height: 56 }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img}
                  alt={`Product ${i + 1}`}
                  style={{
                    width: 56, height: 56, objectFit: "cover",
                    borderRadius: 6, border: "1px solid rgba(255,255,255,0.1)",
                  }}
                />
                {!isRunning && (
                  <button
                    onClick={() => removeImage(i)}
                    style={{
                      position: "absolute", top: -4, right: -4,
                      width: 16, height: 16, borderRadius: "50%",
                      background: "#ef4444", border: "none",
                      color: "#fff", fontSize: 10, cursor: "pointer",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}
                  >×</button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Identity Pack */}
      <div
        style={{
          border: `1px solid ${useIdentityPack ? "rgba(168,85,247,0.3)" : "rgba(255,255,255,0.07)"}`,
          borderRadius: 10,
          padding: "14px",
          transition: "border-color 0.2s",
          background: useIdentityPack ? "rgba(168,85,247,0.04)" : "transparent",
        }}
      >
        {/* Header row */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: useIdentityPack ? 14 : 0 }}>
          <div>
            <div style={{ color: "#f0f0f0", fontSize: 12, fontWeight: 500 }}>
              Identity Pack
            </div>
            <div style={{ color: "#555", fontSize: 11, marginTop: 2 }}>
              Multi-angle refs · Kling V3 only
            </div>
          </div>
          {/* Toggle */}
          <button
            onClick={() => !isRunning && toggleIdentityPack(!useIdentityPack)}
            disabled={isRunning}
            style={{
              width: 36,
              height: 20,
              borderRadius: 10,
              border: "none",
              background: useIdentityPack ? "#a855f7" : "rgba(255,255,255,0.1)",
              cursor: isRunning ? "default" : "pointer",
              position: "relative",
              transition: "background 0.2s",
              flexShrink: 0,
            }}
          >
            <div
              style={{
                position: "absolute",
                top: 2,
                left: useIdentityPack ? 18 : 2,
                width: 16,
                height: 16,
                borderRadius: "50%",
                background: "#fff",
                transition: "left 0.2s",
              }}
            />
          </button>
        </div>

        {/* Angle slots — only visible when enabled */}
        {useIdentityPack && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
              {IDENTITY_ANGLES.map(({ key, label }) => {
                const hasImage = !!identityPack[key];
                return (
                  <div key={key}>
                    <div
                      onClick={() => !isRunning && angleInputRefs.current[key]?.click()}
                      style={{
                        width: "100%",
                        aspectRatio: "1",
                        borderRadius: 8,
                        border: `1px ${hasImage ? "solid rgba(168,85,247,0.4)" : "dashed rgba(255,255,255,0.12)"}`,
                        background: hasImage ? "transparent" : "rgba(255,255,255,0.02)",
                        cursor: isRunning ? "default" : "pointer",
                        position: "relative",
                        overflow: "hidden",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "border-color 0.15s",
                      }}
                    >
                      {hasImage ? (
                        <>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={identityPack[key]}
                            alt={label}
                            style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          />
                          {!isRunning && (
                            <button
                              onClick={(e) => { e.stopPropagation(); removeIdentityImage(key); }}
                              style={{
                                position: "absolute", top: 2, right: 2,
                                width: 14, height: 14, borderRadius: "50%",
                                background: "rgba(0,0,0,0.7)", border: "none",
                                color: "#fff", fontSize: 9, cursor: "pointer",
                                display: "flex", alignItems: "center", justifyContent: "center",
                              }}
                            >×</button>
                          )}
                        </>
                      ) : (
                        <span style={{ color: "#444", fontSize: 10 }}>+</span>
                      )}
                    </div>
                    <input
                      ref={(el) => { angleInputRefs.current[key] = el; }}
                      type="file"
                      accept="image/*"
                      style={{ display: "none" }}
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) handleIdentityImageUpload(key, file);
                        e.target.value = "";
                      }}
                    />
                    <div style={{ color: "#555", fontSize: 10, textAlign: "center", marginTop: 4 }}>
                      {label}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Tail frame lock */}
            <button
              onClick={() => !isRunning && setUseTailImage(!useTailImage)}
              disabled={isRunning}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginTop: 12,
                background: "none",
                border: "none",
                cursor: isRunning ? "default" : "pointer",
                padding: 0,
                width: "100%",
              }}
            >
              <div
                style={{
                  width: 14, height: 14, borderRadius: 3, flexShrink: 0,
                  border: `1px solid ${useTailImage ? "#a855f7" : "rgba(255,255,255,0.2)"}`,
                  background: useTailImage ? "#a855f7" : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "all 0.15s",
                }}
              >
                {useTailImage && <span style={{ color: "#fff", fontSize: 9, lineHeight: 1 }}>✓</span>}
              </div>
              <span style={{ color: "#888", fontSize: 12 }}>Tail frame lock</span>
              <span style={{ color: "#444", fontSize: 11, marginLeft: "auto" }}>forces end = start</span>
            </button>

            <div style={{ marginTop: 10, color: "#444", fontSize: 11, lineHeight: 1.5 }}>
              Model locked to <span style={{ color: "#a855f7" }}>kling-v3</span> · Identity selector
              picks angles from video analysis context
            </div>
          </>
        )}
      </div>

      {/* Fal API Key */}
      <div>
        <label style={labelStyle}>Fal API Key</label>
        <input
          type="password"
          placeholder="key_xxxxxxxx…"
          value={falKey}
          onChange={(e) => setFalKey(e.target.value)}
          disabled={isRunning}
          style={{ ...inputStyle, opacity: isRunning ? 0.5 : 1, fontFamily: "monospace" }}
          onFocus={(e) => { e.target.style.borderColor = "rgba(255,255,255,0.2)"; }}
          onBlur={(e) => { e.target.style.borderColor = "rgba(255,255,255,0.09)"; }}
        />
      </div>

      {/* Video Model */}
      <div>
        <label style={labelStyle}>Video Model</label>
        <div style={{ display: "flex", gap: 8 }}>
          {(["sora", "kling", "kling-v3"] as const).map((m) => {
            const locked = useIdentityPack && m !== "kling-v3";
            return (
              <button
                key={m}
                onClick={() => !isRunning && !locked && setVideoModel(m)}
                disabled={isRunning || locked}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  borderRadius: 7,
                  border: `1px solid ${videoModel === m ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.07)"}`,
                  background: videoModel === m ? "rgba(255,255,255,0.06)" : "transparent",
                  color: locked ? "#333" : videoModel === m ? "#f0f0f0" : "#555",
                  fontSize: 12,
                  fontWeight: videoModel === m ? 500 : 400,
                  cursor: isRunning || locked ? "default" : "pointer",
                  transition: "all 0.15s",
                  opacity: locked ? 0.4 : isRunning ? 0.5 : 1,
                }}
              >
                {m}
              </button>
            );
          })}
        </div>
        {useIdentityPack && (
          <div style={{ color: "#555", fontSize: 11, marginTop: 6 }}>
            Locked to kling-v3 while Identity Pack is enabled
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.25)",
            borderRadius: 8, padding: "10px 12px",
            color: "#fca5a5", fontSize: 12,
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
            width: "100%", padding: "11px 0", borderRadius: 8,
            border: "1px solid rgba(255,255,255,0.1)",
            background: "rgba(255,255,255,0.04)",
            color: "#f0f0f0", fontSize: 13, fontWeight: 500,
            cursor: "pointer", transition: "all 0.15s",
          }}
        >
          Run Again
        </button>
      ) : isPaused ? (
        <div
          style={{
            width: "100%", padding: "11px 0", borderRadius: 8,
            border: "1px solid rgba(245,158,11,0.25)",
            background: "rgba(245,158,11,0.06)",
            color: "#fbbf24", fontSize: 13, fontWeight: 500,
            textAlign: "center",
          }}
        >
          Paused — review prompt to continue
        </div>
      ) : (
        <button
          onClick={startPipeline}
          disabled={isRunning || !videoUrl.trim()}
          style={{
            width: "100%", padding: "11px 0", borderRadius: 8, border: "none",
            background: isRunning || !videoUrl.trim() ? "rgba(59,130,246,0.2)" : "#3b82f6",
            color: isRunning || !videoUrl.trim() ? "rgba(255,255,255,0.4)" : "#fff",
            fontSize: 13, fontWeight: 600,
            cursor: isRunning || !videoUrl.trim() ? "default" : "pointer",
            transition: "all 0.15s", letterSpacing: "0.01em",
          }}
        >
          {isRunning ? "Running…" : "Run Pipeline"}
        </button>
      )}
    </div>
  );
}
