import type { NodeOutputRendererProps } from "../node-renderers";

export function GenerateVideoOutput({ output }: NodeOutputRendererProps) {
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
