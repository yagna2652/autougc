"use client";

import { useState, useRef, useCallback } from "react";
import { NODE_DEFINITIONS } from "@/lib/nodes";

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

export function usePipeline() {
  const [nodeStates, setNodeStates] = useState<Record<string, NodeState>>(
    makeInitialNodeStates
  );
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus>("idle");
  const [jobId, setJobId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>("input");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoModel, setVideoModel] = useState<"sora" | "kling" | "kling-v3">("sora");
  const [productImages, setProductImages] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);

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

    try {
      const response = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "start",
          videoUrl: videoUrl.trim(),
          videoModel,
          productImages,
        }),
      });

      const data = await response.json();
      if (!response.ok || data.error) {
        throw new Error(data.error || "Failed to start pipeline");
      }

      const newJobId: string = data.jobId;
      setJobId(newJobId);

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
          setNodeStates((prev) => ({
            ...prev,
            [node]: { status: "done", output },
          }));
          setSelectedNode(node);
        } else if (eventType === "done") {
          const status = event.status as string;
          setPipelineStatus(status === "completed" ? "completed" : "failed");
          if (event.error) setError(event.error as string);
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
        es.close();
        eventSourceRef.current = null;
      };
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setPipelineStatus("failed");
    }
  }, [videoUrl, videoModel, productImages, pipelineStatus]);

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
    error,
    startPipeline,
    resetPipeline,
  };
}
