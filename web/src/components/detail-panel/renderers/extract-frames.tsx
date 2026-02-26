import { FieldRow } from "../field-row";
import type { NodeOutputRendererProps } from "../node-renderers";

export function ExtractFramesOutput({ output }: NodeOutputRendererProps) {
  const count = output.frame_count as number;
  return (
    <div>
      <FieldRow label="Frames Extracted" value={count} />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginTop: 4,
        }}
      >
        {Array.from({ length: Math.min(count || 0, 8) }).map((_, i) => (
          <div
            key={i}
            style={{
              width: 28,
              height: 20,
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 3,
            }}
          />
        ))}
        {(count || 0) > 8 && (
          <span style={{ color: "#555", fontSize: 11 }}>+{count - 8} more</span>
        )}
      </div>
    </div>
  );
}
