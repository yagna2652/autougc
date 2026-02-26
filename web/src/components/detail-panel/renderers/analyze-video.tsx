import { FieldRow } from "../field-row";
import type { NodeOutputRendererProps } from "../node-renderers";

export function AnalyzeVideoOutput({ output }: NodeOutputRendererProps) {
  const analysis = output.video_analysis as Record<string, unknown> | null;
  if (!analysis) return <div style={{ color: "#444", fontSize: 13 }}>No analysis data</div>;
  return (
    <div>
      <FieldRow label="Setting" value={analysis.setting as string} />
      <FieldRow label="Lighting" value={analysis.lighting as string} />
      <FieldRow label="Style" value={analysis.style as string} />
      <FieldRow label="Energy" value={analysis.energy as string} />
      <FieldRow label="Mood" value={analysis.mood as string} />
      <FieldRow label="Actions" value={analysis.actions as string} />
      {!!analysis.camera && (
        <div style={{ marginBottom: 12 }}>
          <div
            style={{
              color: "#555",
              fontSize: 10,
              fontWeight: 600,
              letterSpacing: "0.07em",
              textTransform: "uppercase",
              marginBottom: 4,
            }}
          >
            Camera
          </div>
          <div style={{ color: "#d4d4d4", fontSize: 13, lineHeight: 1.5 }}>
            {Object.entries(analysis.camera as Record<string, string>)
              .map(([k, v]) => `${k}: ${v}`)
              .join(" · ")}
          </div>
        </div>
      )}
      {!!analysis.what_makes_it_work && (
        <FieldRow label="What Makes It Work" value={analysis.what_makes_it_work as string} />
      )}
    </div>
  );
}
