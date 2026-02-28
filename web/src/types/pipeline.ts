/**
 * Pipeline Type Definitions - Strongly typed data structures for the frontend.
 *
 * These types mirror the Python TypedDict definitions in src/pipeline/types.py
 * for type-safe data handling across the API boundary.
 */

// =============================================================================
// Video Analysis Types
// =============================================================================

export interface CameraInfo {
  framing?: "close-up" | "medium" | "full body" | string;
  angle?: "eye-level" | "above" | "below" | string;
  movement?: "handheld" | "stable" | "slight movement" | string;
}

export interface PersonInfo {
  age_range?: string;
  gender?: string;
  appearance?: string;
  vibe?: "casual" | "polished" | "energetic" | string;
}

export interface VideoAnalysisData {
  setting?: string;
  lighting?: string;
  camera?: CameraInfo;
  person?: PersonInfo;
  actions?: string;
  style?: string;
  energy?: "high" | "medium" | "low" | string;
  mood?: string;
  text_overlays?: string;
  what_makes_it_work?: string;
  raw_response?: string;
}

// =============================================================================
// Pipeline State and Result Types
// =============================================================================

export type VideoModel = "sora" | "kling" | "kling-v3" | "kling-o3-ref";

export type PipelineStatus = "idle" | "running" | "paused" | "completed" | "failed";

export type PipelineNodeId =
  | "download_video"
  | "extract_frames"
  | "analyze_video"
  | "generate_prompt"
  | "distill_prompt"
  | "validate_prompt"
  | "generate_scene_image"
  | "generate_video";

export interface PipelineResult {
  jobId: string;
  status: PipelineStatus;
  currentStep: string;
  error: string | null;

  // Analysis results
  videoAnalysis: VideoAnalysisData | null;

  // Generated content
  videoPrompt: string;
  suggestedScript: string;
  sceneImageUrl: string;
  generatedVideoUrl: string;
}

// =============================================================================
// API Request/Response Types
// =============================================================================

export interface StartPipelineRequest {
  action: "start";
  videoUrl: string;
  productDescription?: string;
  productMechanics?: string;
  productImages: string[];
  videoModel?: VideoModel;
  productIdentityPack?: {
    front?: string;
    side_45?: string;
    back?: string;
    top?: string;
    close_up_logo?: string;
    close_up_material?: string;
  };
  useIdentityPack?: boolean;
  useTailImage?: boolean;
  useAnchorFrames?: boolean;
  segmentDuration?: number;
}

export interface StatusPipelineRequest {
  action: "status";
  jobId: string;
}

export interface ResumePipelineRequest {
  action: "resume";
  jobId: string;
  videoPrompt?: string;
}

export type PipelineRequest = StartPipelineRequest | StatusPipelineRequest | ResumePipelineRequest;

export interface StartPipelineResponse {
  jobId: string;
  status: "started";
}

export interface StatusPipelineResponse extends PipelineResult {}

export interface ErrorResponse {
  error: string;
}

// =============================================================================
// Run History Types
// =============================================================================

export interface SerializedNodeState {
  status: "idle" | "running" | "done" | "failed";
  output: Record<string, unknown> | null;
}

export interface RunHistoryEntry {
  id: string;
  jobId: string | null;
  videoUrl: string;
  videoModel: VideoModel;
  status: "running" | "paused" | "completed" | "failed";
  startedAt: number;
  updatedAt: number;
  error: string | null;
  nodeStates: Record<string, SerializedNodeState>;
  sceneImageUrl: string | null;
  generatedVideoUrl: string | null;
  templateVersion: number | null;
}
