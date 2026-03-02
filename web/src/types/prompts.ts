export interface PromptVersion {
  id: string;
  version: number;
  prompt: string;
  negative_prompt: string;
  name: string | null;
  change_note: string | null;
  model_config: {
    duration?: number;
    aspect_ratio?: string;
    cfg_scale?: number;
    multi_prompt?: { prompt: string; duration: number }[];
    shot_type?: string;
  } | null;
  labels: string[];
  traces: GenerationTrace[];
  created_at: string;
}

export interface PromptVersionSummary {
  id: string;
  version: number;
  prompt_preview: string;
  name: string | null;
  trace_count: number;
  avg_rating: number | null;
  labels: string[];
  created_at: string;
}

export interface GenerationTrace {
  id: string;
  prompt_version_id: string;
  job_id: string | null;
  start_image_url: string | null;
  end_image_url: string | null;
  product_images: string[] | null;
  product_video_url: string | null;
  video_url: string | null;
  elapsed_seconds: number | null;
  status: "pending" | "success" | "error";
  error_message: string | null;
  rating: number | null;
  notes: string | null;
  created_at: string;
}
