import { FieldRow } from "../field-row";
import type { NodeOutputRendererProps } from "../node-renderers";

export function DownloadVideoOutput({ output }: NodeOutputRendererProps) {
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
