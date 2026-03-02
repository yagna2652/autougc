/** A single shot in a multi-shot prompt */
export interface ShotPrompt {
  prompt: string;
  duration: number;
}

/** Request body for POST /api/generate */
export interface GenerateRequest {
  prompt?: string;
  multi_prompt?: ShotPrompt[];
  shot_type?: string;
  start_image_url: string;
  product_images: string[];
  duration: number;
  aspect_ratio: string;
  cfg_scale: number;
  end_image_url?: string;
  negative_prompt?: string;
  product_video_url?: string;
}

/** SSE event types from the generate endpoint */
export type GenerateEventType = "job_start" | "status" | "done" | "error";

export interface JobStartEvent {
  job_id: string;
  prompt_version_id: string | null;
  trace_id: string | null;
}

export interface StatusEvent {
  step: string;
  message: string;
}

export interface DoneEvent {
  video_url: string;
  elapsed_seconds: number;
  job_id: string;
  prompt_version_id: string | null;
  trace_id: string | null;
}

export interface ErrorEvent {
  message: string;
}

export type GenerateEvent =
  | { event: "job_start"; data: JobStartEvent }
  | { event: "status"; data: StatusEvent }
  | { event: "done"; data: DoneEvent }
  | { event: "error"; data: ErrorEvent };
