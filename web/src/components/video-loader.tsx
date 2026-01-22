"use client";

import { useEffect, useState, useMemo } from "react";

interface VideoGenerationLoaderProps {
  model: "sora2" | "kling";
  progress?: string;
}

const STAGES = [
  { id: "submit", label: "Submitting request", duration: 3 },
  { id: "queue", label: "Waiting in queue", duration: 10 },
  { id: "process", label: "Processing prompt", duration: 15 },
  { id: "generate", label: "Generating frames", duration: 60 },
  { id: "render", label: "Rendering video", duration: 30 },
  { id: "finalize", label: "Finalizing output", duration: 10 },
];

export function VideoGenerationLoader({
  model,
  progress,
}: VideoGenerationLoaderProps) {
  const [elapsedTime, setElapsedTime] = useState(0);

  // Elapsed time counter
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime((prev) => prev + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Derive current stage from elapsed time (no setState needed)
  const currentStageIndex = useMemo(() => {
    let totalDuration = 0;
    for (let i = 0; i < STAGES.length; i++) {
      totalDuration += STAGES[i].duration;
      if (elapsedTime < totalDuration) {
        return i;
      }
    }
    return STAGES.length - 1;
  }, [elapsedTime]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const modelName = model === "sora2" ? "Sora 2" : "Kling 2.5";
  const estimatedTime = model === "sora2" ? "2-3 minutes" : "1-2 minutes";

  return (
    <div className="rounded-xl border border-border bg-gradient-to-br from-muted/80 to-muted/40 p-6 shadow-lg">
      {/* Header with timer */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Animated loader icon */}
          <div className="relative">
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary/20 border-t-primary" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-4 w-4 animate-pulse rounded-full bg-primary/60" />
            </div>
          </div>
          <div>
            <h3 className="font-semibold text-foreground">
              Generating with {modelName}
            </h3>
            <p className="text-sm text-muted-foreground">
              Estimated time: {estimatedTime}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-2xl font-bold text-primary">
            {formatTime(elapsedTime)}
          </div>
          <p className="text-xs text-muted-foreground">elapsed</p>
        </div>
      </div>

      {/* Progress stages */}
      <div className="mb-4 space-y-2">
        {STAGES.map((stage, index) => {
          const isComplete = index < currentStageIndex;
          const isCurrent = index === currentStageIndex;

          return (
            <div
              key={stage.id}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 transition-all duration-300 ${
                isCurrent
                  ? "bg-primary/10 border border-primary/20"
                  : isComplete
                    ? "opacity-60"
                    : "opacity-30"
              }`}
            >
              {/* Status indicator */}
              <div className="flex h-6 w-6 items-center justify-center">
                {isComplete ? (
                  <svg
                    className="h-5 w-5 text-green-500"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : isCurrent ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                ) : (
                  <div className="h-3 w-3 rounded-full bg-muted-foreground/30" />
                )}
              </div>

              {/* Stage label */}
              <span
                className={`text-sm ${
                  isCurrent
                    ? "font-medium text-foreground"
                    : isComplete
                      ? "text-muted-foreground"
                      : "text-muted-foreground/50"
                }`}
              >
                {stage.label}
              </span>

              {/* Current stage indicator */}
              {isCurrent && (
                <div className="ml-auto flex items-center gap-1">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="h-2 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-1000 ease-out"
            style={{
              width: `${Math.min(((currentStageIndex + 1) / STAGES.length) * 100, 100)}%`,
            }}
          />
        </div>
      </div>

      {/* Custom progress message from API */}
      {progress && (
        <div className="rounded-lg bg-muted/50 px-3 py-2">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium">API:</span> {progress}
          </p>
        </div>
      )}

      {/* Tips */}
      <div className="mt-4 rounded-lg border border-border/50 bg-background/50 p-3">
        <p className="text-xs text-muted-foreground">
          💡 <strong>Tip:</strong> Video generation uses AI to create each frame
          individually. The process cannot be interrupted once started, so
          please wait for completion.
        </p>
      </div>
    </div>
  );
}
