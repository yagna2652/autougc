/**
 * usePipeline - React hook for managing the LangGraph pipeline.
 *
 * This hook provides a clean interface for:
 * - Starting pipeline jobs
 * - Generating prompts from blueprints
 * - Polling for job status
 * - Managing loading/error states
 *
 * The hook ensures the mechanics-enhanced prompt is properly used.
 */

import { useState, useCallback, useRef } from "react";

// Types
export interface ProductContext {
  type?: string;
  interactions?: string[];
  tactileFeatures?: string[];
  soundFeatures?: string[];
  sizeDescription?: string;
  highlightFeature?: string;
  customInstructions?: string;
}

export interface PipelineConfig {
  enableMechanics?: boolean;
  productCategory?: string;
  targetDuration?: number;
  energyLevel?: string;
  videoModel?: string;
  videoDuration?: number;
  aspectRatio?: string;
  useImageToVideo?: boolean;
}

export interface BlueprintSummary {
  transcript: string;
  hookStyle: string;
  bodyFramework: string;
  ctaUrgency: string;
  setting: string;
  lighting: string;
  energy: string;
  duration: number;
}

export interface PipelineResult {
  jobId: string;
  status: "pending" | "running" | "completed" | "failed";
  currentStep: string;
  progress: {
    stepNumber: number;
    totalSteps: number;
    currentStep: string;
    percentage: number;
  };
  error?: string;
  // Results
  blueprint?: Record<string, unknown>;
  blueprintSummary?: BlueprintSummary;
  basePrompt?: string;
  mechanicsPrompt?: string;
  finalPrompt?: string;
  promptSource?: "mechanics" | "base" | "fallback";
  generatedVideoUrl?: string;
  // Metadata
  createdAt?: string;
  completedAt?: string;
}

interface UsePipelineOptions {
  pollInterval?: number;
  onProgress?: (result: PipelineResult) => void;
  onComplete?: (result: PipelineResult) => void;
  onError?: (error: string) => void;
}

interface UsePipelineReturn {
  // State
  isLoading: boolean;
  isPolling: boolean;
  result: PipelineResult | null;
  error: string | null;

  // Actions
  startPipeline: (params: StartPipelineParams) => Promise<string | null>;
  generatePrompt: (params: GeneratePromptParams) => Promise<string | null>;
  pollStatus: (jobId: string) => Promise<PipelineResult | null>;
  stopPolling: () => void;
  reset: () => void;
}

interface StartPipelineParams {
  videoUrl: string;
  productImages?: string[];
  productDescription?: string;
  productContext?: ProductContext;
  config?: PipelineConfig;
  skipVideoGeneration?: boolean;
}

interface GeneratePromptParams {
  blueprint: Record<string, unknown>;
  blueprintSummary?: BlueprintSummary;
  productImages?: string[];
  productDescription?: string;
  productContext?: ProductContext;
  config?: PipelineConfig;
}

export function usePipeline(options: UsePipelineOptions = {}): UsePipelineReturn {
  const { pollInterval = 2000, onProgress, onComplete, onError } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Reset state
  const reset = useCallback(() => {
    stopPolling();
    setIsLoading(false);
    setResult(null);
    setError(null);
  }, [stopPolling]);

  // Poll for job status
  const pollStatus = useCallback(
    async (jobId: string): Promise<PipelineResult | null> => {
      try {
        const response = await fetch("/api/pipeline", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "status", jobId }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to get job status");
        }

        const pipelineResult: PipelineResult = {
          jobId: data.jobId,
          status: data.status,
          currentStep: data.currentStep,
          progress: data.progress || {
            stepNumber: 0,
            totalSteps: 12,
            currentStep: "",
            percentage: 0,
          },
          error: data.error,
          blueprint: data.blueprint,
          blueprintSummary: data.blueprintSummary,
          basePrompt: data.basePrompt,
          mechanicsPrompt: data.mechanicsPrompt,
          finalPrompt: data.finalPrompt,
          promptSource: data.promptSource,
          generatedVideoUrl: data.generatedVideoUrl,
          createdAt: data.createdAt,
          completedAt: data.completedAt,
        };

        setResult(pipelineResult);

        return pipelineResult;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        setError(errorMessage);
        onError?.(errorMessage);
        return null;
      }
    },
    [onError]
  );

  // Start polling for a job
  const startPolling = useCallback(
    (jobId: string) => {
      setIsPolling(true);

      const poll = async () => {
        const result = await pollStatus(jobId);

        if (result) {
          onProgress?.(result);

          if (result.status === "completed") {
            stopPolling();
            setIsLoading(false);
            onComplete?.(result);
          } else if (result.status === "failed") {
            stopPolling();
            setIsLoading(false);
            setError(result.error || "Pipeline failed");
            onError?.(result.error || "Pipeline failed");
          }
        }
      };

      // Initial poll
      poll();

      // Set up interval
      pollIntervalRef.current = setInterval(poll, pollInterval);
    },
    [pollInterval, pollStatus, stopPolling, onProgress, onComplete, onError]
  );

  // Start the full pipeline
  const startPipeline = useCallback(
    async (params: StartPipelineParams): Promise<string | null> => {
      reset();
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch("/api/pipeline", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "start",
            videoUrl: params.videoUrl,
            productImages: params.productImages,
            productDescription: params.productDescription,
            productContext: params.productContext,
            config: params.config,
            skipVideoGeneration: params.skipVideoGeneration,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to start pipeline");
        }

        const jobId = data.jobId;

        // Start polling for status
        startPolling(jobId);

        return jobId;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        setError(errorMessage);
        setIsLoading(false);
        onError?.(errorMessage);
        return null;
      }
    },
    [reset, startPolling, onError]
  );

  // Generate prompt from blueprint
  const generatePrompt = useCallback(
    async (params: GeneratePromptParams): Promise<string | null> => {
      reset();
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch("/api/pipeline", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "generate-prompt",
            blueprint: params.blueprint,
            blueprintSummary: params.blueprintSummary,
            productImages: params.productImages,
            productDescription: params.productDescription,
            productContext: params.productContext,
            config: params.config,
          }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to generate prompt");
        }

        const jobId = data.jobId;

        // Start polling for status
        startPolling(jobId);

        return jobId;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : "Unknown error";
        setError(errorMessage);
        setIsLoading(false);
        onError?.(errorMessage);
        return null;
      }
    },
    [reset, startPolling, onError]
  );

  return {
    isLoading,
    isPolling,
    result,
    error,
    startPipeline,
    generatePrompt,
    pollStatus,
    stopPolling,
    reset,
  };
}

export default usePipeline;
