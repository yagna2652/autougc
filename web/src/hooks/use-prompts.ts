"use client";

import { useCallback, useEffect, useState } from "react";
import type { PromptVersionSummary, PromptVersion } from "@/types/prompts";

export function usePrompts() {
  const [versions, setVersions] = useState<PromptVersionSummary[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/prompts");
      if (res.ok) {
        setVersions(await res.json());
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const loadVersion = useCallback(async (id: string): Promise<PromptVersion | null> => {
    try {
      const res = await fetch(`/api/prompts/${id}`);
      if (res.ok) return await res.json();
    } catch {
      // silent
    }
    return null;
  }, []);

  const saveVersion = useCallback(
    async (prompt: string, negativePrompt: string = "", name?: string, changeNote?: string) => {
      try {
        const res = await fetch("/api/prompts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            negative_prompt: negativePrompt,
            name: name || undefined,
            change_note: changeNote || undefined,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          await refresh();
          return data as { id: string; version: number; is_new: boolean };
        }
      } catch {
        // silent
      }
      return null;
    },
    [refresh],
  );

  const setLabel = useCallback(
    async (versionId: string, labelName: string) => {
      try {
        await fetch(`/api/prompts/${versionId}/labels`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: labelName }),
        });
        await refresh();
      } catch {
        // silent
      }
    },
    [refresh],
  );

  const removeLabel = useCallback(
    async (versionId: string, labelName: string) => {
      try {
        await fetch(`/api/prompts/${versionId}/labels?name=${encodeURIComponent(labelName)}`, {
          method: "DELETE",
        });
        await refresh();
      } catch {
        // silent
      }
    },
    [refresh],
  );

  return { versions, loading, refresh, loadVersion, saveVersion, setLabel, removeLabel };
}
