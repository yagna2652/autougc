import type { NodeOutputRendererProps } from "../node-renderers";

export function GenerateSceneImageOutput({ output }: NodeOutputRendererProps) {
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
