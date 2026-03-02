"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Tag, X, Plus } from "lucide-react";
import type { PromptVersionSummary } from "@/types/prompts";

interface PromptSidebarProps {
  versions: PromptVersionSummary[];
  loading: boolean;
  activeVersionId: string | null;
  onSelect: (id: string) => void;
  onAddLabel: (versionId: string, label: string) => void;
  onRemoveLabel: (versionId: string, label: string) => void;
}

export function PromptSidebar({
  versions,
  loading,
  activeVersionId,
  onSelect,
  onAddLabel,
  onRemoveLabel,
}: PromptSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [labelInput, setLabelInput] = useState<string | null>(null);
  const [labelText, setLabelText] = useState("");

  if (collapsed) {
    return (
      <div className="flex flex-col items-center pt-4">
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          title="Show prompt history"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    );
  }

  function handleAddLabel(versionId: string) {
    if (labelText.trim()) {
      onAddLabel(versionId, labelText.trim());
      setLabelText("");
      setLabelInput(null);
    }
  }

  return (
    <div className="w-64 shrink-0 border-r pr-4 space-y-3 overflow-y-auto max-h-[calc(100vh-6rem)]">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Prompt History</span>
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          className="p-1 text-muted-foreground hover:text-foreground transition-colors"
        >
          <ChevronLeft size={14} />
        </button>
      </div>

      {loading && versions.length === 0 && (
        <p className="text-xs text-muted-foreground">Loading...</p>
      )}

      {versions.length === 0 && !loading && (
        <p className="text-xs text-muted-foreground">No saved prompts yet. Generate or save a prompt to start.</p>
      )}

      <div className="space-y-1.5">
        {versions.map((v) => (
          <div
            key={v.id}
            onClick={() => onSelect(v.id)}
            className={`p-2.5 rounded-lg cursor-pointer transition-colors text-left ${
              activeVersionId === v.id
                ? "bg-primary/10 border border-primary/30"
                : "hover:bg-secondary border border-transparent"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium">
                v{v.version}
                {v.name && <span className="ml-1 text-muted-foreground font-normal">· {v.name}</span>}
              </span>
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                {v.trace_count > 0 && <span>{v.trace_count} run{v.trace_count !== 1 ? "s" : ""}</span>}
                {v.avg_rating !== null && (
                  <span className={v.avg_rating > 0 ? "text-green-500" : v.avg_rating < 0 ? "text-red-500" : ""}>
                    {v.avg_rating > 0 ? "+" : ""}{v.avg_rating.toFixed(1)}
                  </span>
                )}
              </div>
            </div>
            <p className="text-xs text-muted-foreground line-clamp-2">{v.prompt_preview}</p>

            {/* Labels */}
            {v.labels.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {v.labels.map((label) => (
                  <span
                    key={label}
                    className="inline-flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded-full bg-accent text-accent-foreground"
                  >
                    <Tag size={8} />
                    {label}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRemoveLabel(v.id, label);
                      }}
                      className="ml-0.5 hover:text-destructive"
                    >
                      <X size={8} />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Add label */}
            {labelInput === v.id ? (
              <div className="flex gap-1 mt-1.5" onClick={(e) => e.stopPropagation()}>
                <input
                  type="text"
                  value={labelText}
                  onChange={(e) => setLabelText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleAddLabel(v.id);
                    if (e.key === "Escape") { setLabelInput(null); setLabelText(""); }
                  }}
                  placeholder="label name"
                  className="input-field !py-0.5 !px-1.5 !text-[10px] flex-1"
                  autoFocus
                />
                <button
                  type="button"
                  onClick={() => handleAddLabel(v.id)}
                  className="text-[10px] px-1.5 rounded bg-primary text-primary-foreground"
                >
                  Add
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setLabelInput(v.id);
                }}
                className="mt-1 text-[10px] text-muted-foreground hover:text-foreground flex items-center gap-0.5 transition-colors"
              >
                <Plus size={8} /> label
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
