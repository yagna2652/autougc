"use client";

import { useState, useRef, useCallback } from "react";
import { NODE_DEFINITIONS, NODE_IDS } from "@/lib/nodes";
import type { RunHistoryEntry, VideoModel } from "@/types/pipeline";

export type NodeStatus = "idle" | "running" | "done" | "failed";

export interface NodeState {
  status: NodeStatus;
  output: Record<string, unknown> | null;
}

export type PipelineStatus = "idle" | "running" | "paused" | "completed" | "failed";

function makeInitialNodeStates(): Record<string, NodeState> {
  return Object.fromEntries(
    NODE_DEFINITIONS.map((n) => [n.id, { status: "idle" as NodeStatus, output: null }])
  );
}

export interface PipelineCallbacks {
  onRunStart?: (info: { videoUrl: string; videoModel: VideoModel }) => string | void;
  onJobIdAssigned?: (runId: string, jobId: string) => void;
  onNodeUpdate?: (runId: string, nodeStates: Record<string, NodeState>) => void;
  onPaused?: (runId: string) => void;
  onRunComplete?: (runId: string, status: "completed" | "failed", error: string | null) => void;
}

export function usePipeline(callbacks?: PipelineCallbacks) {
  const [nodeStates, setNodeStates] = useState<Record<string, NodeState>>(
    makeInitialNodeStates
  );
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>("input");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoModel, setVideoModel] = useState<VideoModel>("sora");
  const [productImages, setProductImages] = useState<string[]>([]);
  const [identityPack, setIdentityPack] = useState<Record<string, string>>({});
  const [useIdentityPack, setUseIdentityPack] = useState(false);
  const [useTailImage, setUseTailImage] = useState(false);
  const [falKey, setFalKey] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("fal_key") ?? "";
    }
    return "";
  });
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const activeRunIdRef = useRef<string | null>(null);
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  const persistFalKey = useCallback((key: string) => {
    setFalKey(key);
    if (typeof window !== "undefined") {
      if (key.trim()) {
        localStorage.setItem("fal_key", key);
      } else {
        localStorage.removeItem("fal_key");
      }
    }
  }, []);

  // ---------------------------------------------------------------------------
  // checkJobStatus — asks backend if a job is still alive
  // ---------------------------------------------------------------------------
  const checkJobStatus = useCallback(async (targetJobId: string): Promise<boolean> => {
    try {
      const response = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "status", jobId: targetJobId }),
      });
      if (!response.ok) return false;
      const data = await response.json();
      const status = data.status as string;
      return status === "running" || status === "paused";
    } catch {
      return false;
    }
  }, []);

  // ---------------------------------------------------------------------------
  // connectSSE — opens an EventSource for a given jobId and wires all handlers
  // ---------------------------------------------------------------------------
  const connectSSE = useCallback((targetJobId: string) => {
    // Close any existing SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    const es = new EventSource(`/api/pipeline?jobId=${targetJobId}`);
    eventSourceRef.current = es;

    es.onmessage = (e: MessageEvent) => {
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(e.data as string);
      } catch {
        return;
      }

      const eventType = event.type as string;

      if (eventType === "node_start") {
        const node = event.node as string;
        setNodeStates((prev) => ({
          ...prev,
          [node]: { status: "running", output: null },
        }));
        setSelectedNode(node);
      } else if (eventType === "node_done") {
        const node = event.node as string;
        const output = (event.output as Record<string, unknown>) ?? null;
        setNodeStates((prev) => {
          const next = {
            ...prev,
            [node]: { status: "done" as const, output },
          };
          // Fire onNodeUpdate callback with latest state
          if (activeRunIdRef.current) {
            callbacksRef.current?.onNodeUpdate?.(activeRunIdRef.current, next);
          }
          return next;
        });
        setSelectedNode(node);
      } else if (eventType === "paused") {
        setPipelineStatus("paused");
        setSelectedNode("validate_prompt");
        if (activeRunIdRef.current) {
          callbacksRef.current?.onPaused?.(activeRunIdRef.current);
        }
        // Do NOT close EventSource — resume will push more events
      } else if (eventType === "done") {
        const status = event.status as string;
        const finalStatus = status === "completed" ? "completed" : "failed";
        setPipelineStatus(finalStatus);
        const finalError = event.error ? (event.error as string) : null;
        if (finalError) setError(finalError);

        if (activeRunIdRef.current) {
          callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, finalStatus as "completed" | "failed", finalError);
        }

        es.close();
        eventSourceRef.current = null;
      }
      // ping events are intentionally ignored
    };

    es.onerror = async () => {
      if (es.readyState === EventSource.CLOSED) return;
      es.close();
      eventSourceRef.current = null;

      // Check if the backend job is still alive before marking as failed
      const alive = await checkJobStatus(targetJobId);
      if (alive) {
        // Backend is still running — try reconnecting once
        connectSSE(targetJobId);
        return;
      }

      setError("SSE connection lost");
      setPipelineStatus("failed");
      if (activeRunIdRef.current) {
        callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, "failed", "SSE connection lost");
      }
    };
  }, [checkJobStatus]);

  // ---------------------------------------------------------------------------
  // startPipeline — kicks off a new run
  // ---------------------------------------------------------------------------
  const startPipeline = useCallback(async () => {
    if (!videoUrl.trim()) return;
    if (pipelineStatus === "running") return;

    // Close any existing SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setError(null);
    setPipelineStatus("running");
    setNodeStates(makeInitialNodeStates());

    // Fire onRunStart callback
    const runId = callbacksRef.current?.onRunStart?.({ videoUrl, videoModel }) ?? null;
    activeRunIdRef.current = runId ?? null;

    try {
      const response = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "start",
          videoUrl: videoUrl.trim(),
          videoModel,
          productImages,
          productIdentityPack: Object.keys(identityPack).length > 0 ? identityPack : undefined,
          useIdentityPack,
          useTailImage,
          falKey: falKey.trim() || undefined,
        }),
      });

      const data = await response.json();
      if (!response.ok || data.error) {
        throw new Error(data.error || "Failed to start pipeline");
      }

      const newJobId: string = data.jobId;
      setJobId(newJobId);

      // Fire onJobIdAssigned callback
      if (activeRunIdRef.current) {
        callbacksRef.current?.onJobIdAssigned?.(activeRunIdRef.current, newJobId);
      }

      connectSSE(newJobId);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      setError(errMsg);
      setPipelineStatus("failed");

      if (activeRunIdRef.current) {
        callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, "failed", errMsg);
      }
    }
  }, [videoUrl, videoModel, productImages, identityPack, useIdentityPack, useTailImage, pipelineStatus, falKey, connectSSE]);

  const resumePipeline = useCallback(async (editedPrompt?: string) => {
    if (pipelineStatus !== "paused" || !jobId) return;

    setError(null);
    setPipelineStatus("running");

    try {
      const response = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "resume",
          jobId,
          videoPrompt: editedPrompt,
        }),
      });

      const data = await response.json();
      if (!response.ok || data.error) {
        throw new Error(data.error || "Failed to resume pipeline");
      }
      // The SSE connection is still open — new events will flow through automatically
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      setError(errMsg);
      setPipelineStatus("failed");

      if (activeRunIdRef.current) {
        callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, "failed", errMsg);
      }
    }
  }, [pipelineStatus, jobId]);

  const resetPipeline = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setNodeStates(makeInitialNodeStates());
    setPipelineStatus("idle");
    setJobId(null);
    setSelectedNode("input");
    setError(null);
    setVideoUrl("");
    setProductImages([]);
    setIdentityPack({});
    setUseIdentityPack(false);
    setUseTailImage(false);
    // intentionally keep falKey — user shouldn't have to re-paste it
  }, []);

  const handleImageUpload = useCallback((files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const base64 = e.target?.result as string;
        if (base64) setProductImages((prev) => [...prev, base64]);
      };
      reader.readAsDataURL(file);
    });
  }, []);

  const removeImage = useCallback((index: number) => {
    setProductImages((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleIdentityImageUpload = useCallback((angle: string, file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const base64 = e.target?.result as string;
      if (base64) setIdentityPack((prev) => ({ ...prev, [angle]: base64 }));
    };
    reader.readAsDataURL(file);
  }, []);

  const removeIdentityImage = useCallback((angle: string) => {
    setIdentityPack((prev) => {
      const next = { ...prev };
      delete next[angle];
      return next;
    });
  }, []);

  const toggleIdentityPack = useCallback((enabled: boolean) => {
    setUseIdentityPack(enabled);
    if (enabled) setVideoModel(prev => prev === "kling-v3" || prev === "kling-o3-ref" ? prev : "kling-v3");
  }, []);

  const restoreRun = useCallback((entry: RunHistoryEntry) => {
    // Close any active SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Restore all state from the saved entry
    setNodeStates(
      Object.keys(entry.nodeStates).length > 0
        ? (entry.nodeStates as Record<string, NodeState>)
        : makeInitialNodeStates()
    );
    setPipelineStatus(entry.status === "running" ? "idle" : (entry.status as PipelineStatus));
    setJobId(entry.jobId);
    setVideoUrl(entry.videoUrl);
    setVideoModel(entry.videoModel);
    setError(entry.error);
    activeRunIdRef.current = null;

    // Auto-select the last completed node
    const lastDone = [...NODE_IDS].reverse().find(
      (nid) => entry.nodeStates[nid]?.status === "done"
    );
    setSelectedNode(lastDone ?? "input");
  }, []);

  // ---------------------------------------------------------------------------
  // reconnectToJob — restore state from history snapshot then open SSE
  // ---------------------------------------------------------------------------
  const reconnectToJob = useCallback(async (entry: RunHistoryEntry) => {
    if (!entry.jobId) return;

    // Close any existing SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // Restore state from history snapshot
    setNodeStates(
      Object.keys(entry.nodeStates).length > 0
        ? (entry.nodeStates as Record<string, NodeState>)
        : makeInitialNodeStates()
    );
    setPipelineStatus(entry.status as PipelineStatus);
    setJobId(entry.jobId);
    setVideoUrl(entry.videoUrl);
    setVideoModel(entry.videoModel);
    setError(entry.error);

    // Route callbacks to existing history entry (no onRunStart call)
    activeRunIdRef.current = entry.id;

    // Auto-select last completed node
    const lastDone = [...NODE_IDS].reverse().find(
      (nid) => entry.nodeStates[nid]?.status === "done"
    );
    setSelectedNode(lastDone ?? "input");

    // Verify backend still has this job
    const alive = await checkJobStatus(entry.jobId);
    if (!alive) {
      setError("Backend connection lost");
      setPipelineStatus("failed");
      if (activeRunIdRef.current) {
        callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, "failed", "Backend connection lost");
      }
      return;
    }

    // Open SSE for live updates (backend replays all events from cursor=0)
    connectSSE(entry.jobId);
  }, [checkJobStatus, connectSSE]);

  return {
    nodeStates,
    pipelineStatus,
    jobId,
    selectedNode,
    setSelectedNode,
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
    setFalKey: persistFalKey,
    error,
    startPipeline,
    resumePipeline,
    resetPipeline,
    restoreRun,
    reconnectToJob,
    activeRunId: activeRunIdRef.current,
  };
}
