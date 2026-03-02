"use client";

import { useCallback, useRef, useState } from "react";
import type { GenerateRequest, GenerateEvent } from "@/types/generate";

export type GenerateStatus = "idle" | "uploading" | "elements" | "generating" | "done" | "error";

interface GenerateState {
  status: GenerateStatus;
  message: string;
  videoUrl: string | null;
  elapsed: number | null;
  jobId: string | null;
  promptVersionId: string | null;
  traceId: string | null;
}

export function useGenerate() {
  const [state, setState] = useState<GenerateState>({
    status: "idle",
    message: "",
    videoUrl: null,
    elapsed: null,
    jobId: null,
    promptVersionId: null,
    traceId: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const generate = useCallback(async (req: GenerateRequest) => {
    // Reset
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ status: "uploading", message: "Starting...", videoUrl: null, elapsed: null, jobId: null, promptVersionId: null, traceId: null });

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        setState((s) => ({ ...s, status: "error", message: `HTTP ${res.status}` }));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let eventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ") && eventType) {
            try {
              const data = JSON.parse(line.slice(6));
              const event = { event: eventType, data } as GenerateEvent;

              switch (event.event) {
                case "job_start":
                  setState((s) => ({
                    ...s,
                    jobId: event.data.job_id,
                    promptVersionId: event.data.prompt_version_id ?? null,
                    traceId: event.data.trace_id ?? null,
                  }));
                  break;
                case "status":
                  setState((s) => ({
                    ...s,
                    status: event.data.step as GenerateStatus,
                    message: event.data.message,
                  }));
                  break;
                case "done":
                  setState({
                    status: "done",
                    message: `Done in ${event.data.elapsed_seconds}s`,
                    videoUrl: event.data.video_url,
                    elapsed: event.data.elapsed_seconds,
                    jobId: event.data.job_id,
                    promptVersionId: event.data.prompt_version_id ?? null,
                    traceId: event.data.trace_id ?? null,
                  });
                  break;
                case "error":
                  setState((s) => ({ ...s, status: "error", message: event.data.message }));
                  break;
              }
            } catch {
              // skip malformed JSON
            }
            eventType = "";
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setState((s) => ({ ...s, status: "error", message: String(err) }));
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, status: "idle", message: "Cancelled" }));
  }, []);

  const updateTrace = useCallback(async (traceId: string, data: Record<string, unknown>) => {
    try {
      await fetch(`/api/traces/${traceId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
    } catch {
      // silent
    }
  }, []);

  const rateGeneration = useCallback(
    (traceId: string, rating: number) => updateTrace(traceId, { rating }),
    [updateTrace],
  );

  const annotateGeneration = useCallback(
    (traceId: string, notes: string) => updateTrace(traceId, { notes }),
    [updateTrace],
  );

  return { ...state, generate, cancel, rateGeneration, annotateGeneration };
}
