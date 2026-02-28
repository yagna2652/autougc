"use client";

import { useState, useCallback, useEffect } from "react";
import type { RunHistoryEntry, SerializedNodeState, VideoModel } from "@/types/pipeline";

const STORAGE_KEY = "autougc_run_history";
const MAX_RUNS = 50;

function loadRuns(): RunHistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRuns(runs: RunHistoryEntry[]) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(runs));
  } catch {
    // Quota exceeded — evict oldest half and retry
    const trimmed = runs.slice(0, Math.ceil(runs.length / 2));
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      // Give up silently
    }
  }
}

function generateId(): string {
  return `run_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function useRunHistory() {
  const [runs, setRuns] = useState<RunHistoryEntry[]>([]);
  const [isHydrated, setIsHydrated] = useState(false);

  // Load from localStorage after hydration so server/client initial render match
  useEffect(() => {
    setRuns(loadRuns());
    setIsHydrated(true);
  }, []);

  // Sync to localStorage only after hydration (avoids wiping storage on first mount)
  useEffect(() => {
    if (isHydrated) saveRuns(runs);
  }, [runs, isHydrated]);

  const createRun = useCallback(
    ({ videoUrl, videoModel }: { videoUrl: string; videoModel: VideoModel }): string => {
      const id = generateId();
      const entry: RunHistoryEntry = {
        id,
        jobId: null,
        videoUrl,
        videoModel,
        status: "running",
        startedAt: Date.now(),
        updatedAt: Date.now(),
        error: null,
        nodeStates: {},
        sceneImageUrl: null,
        generatedVideoUrl: null,
        templateVersion: null,
      };
      setRuns((prev) => [entry, ...prev].slice(0, MAX_RUNS));
      return id;
    },
    []
  );

  const updateRun = useCallback(
    (id: string, patch: Partial<Omit<RunHistoryEntry, "id">>) => {
      setRuns((prev) =>
        prev.map((r) =>
          r.id === id ? { ...r, ...patch, updatedAt: Date.now() } : r
        )
      );
    },
    []
  );

  const deleteRun = useCallback((id: string) => {
    setRuns((prev) => prev.filter((r) => r.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setRuns([]);
  }, []);

  const getRun = useCallback(
    (id: string): RunHistoryEntry | undefined => {
      return runs.find((r) => r.id === id);
    },
    [runs]
  );

  return { runs, isHydrated, createRun, updateRun, deleteRun, clearAll, getRun };
}
