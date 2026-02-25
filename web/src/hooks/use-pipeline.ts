"use client";

import { useState, useRef, useCallback } from "react";
import { NODE_DEFINITIONS, NODE_IDS } from "@/lib/nodes";
import type { RunHistoryEntry } from "@/types/pipeline";

export type NodeStatus = "idle" | "running" | "done" | "failed";

export interface NodeState {
  status: NodeStatus;
  output: Record<string, unknown> | null;
}

export type PipelineStatus = "idle" | "running" | "completed" | "failed";

function makeInitialNodeStates(): Record<string, NodeState> {
  return Object.fromEntries(
    NODE_DEFINITIONS.map((n) => [n.id, { status: "idle" as NodeStatus, output: null }])
  );
}

export interface PipelineCallbacks {
  onRunStart?: (info: { videoUrl: string; videoModel: "sora" | "kling" | "kling-v3" }) => string | void;
  onJobIdAssigned?: (runId: string, jobId: string) => void;
  onNodeUpdate?: (runId: string, nodeStates: Record<string, NodeState>) => void;
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
  const [videoModel, setVideoModel] = useState<"sora" | "kling" | "kling-v3">("sora");
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

      // Open SSE connection via the Next.js proxy
      const es = new EventSource(`/api/pipeline?jobId=${newJobId}`);
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
        } else if (eventType === "done") {
          const status = event.status as string;
          const finalStatus = status === "completed" ? "completed" : "failed";
          setPipelineStatus(finalStatus);
          const finalError = event.error ? (event.error as string) : null;
          if (finalError) setError(finalError);

          // Fire onRunComplete callback
          if (activeRunIdRef.current) {
            callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, finalStatus as "completed" | "failed", finalError);
          }

          es.close();
          eventSourceRef.current = null;
        }
        // ping events are intentionally ignored
      };

      es.onerror = () => {
        // EventSource readyState: 0=CONNECTING, 1=OPEN, 2=CLOSED
        if (es.readyState === EventSource.CLOSED) return;
        setError("SSE connection lost");
        setPipelineStatus("failed");

        // Fire onRunComplete on SSE error
        if (activeRunIdRef.current) {
          callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, "failed", "SSE connection lost");
        }

        es.close();
        eventSourceRef.current = null;
      };
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Unknown error";
      setError(errMsg);
      setPipelineStatus("failed");

      // Fire onRunComplete on fetch error
      if (activeRunIdRef.current) {
        callbacksRef.current?.onRunComplete?.(activeRunIdRef.current, "failed", errMsg);
      }
    }
  }, [videoUrl, videoModel, productImages, identityPack, useIdentityPack, useTailImage, pipelineStatus, falKey]);

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
    if (enabled) setVideoModel("kling-v3");
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
    setPipelineStatus(entry.status === "running" ? "idle" : entry.status);
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
    resetPipeline,
    restoreRun,
    activeRunId: activeRunIdRef.current,
  };
}
