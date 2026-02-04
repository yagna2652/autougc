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
// UGC Intent Classification Types
// =============================================================================

export type UGCArchetype =
  | "testimonial"
  | "problem_solution"
  | "casual_review"
  | "founder_rant"
  | "storytime"
  | "unboxing"
  | "comparison"
  | "educational_tip"
  | "other";

export type PrimaryIntent =
  | "build_trust"
  | "explain_value"
  | "spark_curiosity"
  | "normalize_product_use"
  | "social_proof"
  | "other";

export type HookType =
  | "relatable_problem"
  | "bold_claim"
  | "curiosity_gap"
  | "emotional_statement"
  | "none"
  | "other";

export type NarrativeStructure =
  | "hook_then_story"
  | "story_then_reveal"
  | "linear_explanation"
  | "moment_in_time"
  | "list_format"
  | "other";

export type EnergyLevel = "low" | "medium" | "high";
export type Pacing = "slow" | "medium" | "fast";
export type ScriptDependency = "high" | "medium" | "low";

export interface UGCIntentData {
  ugc_archetype?: UGCArchetype | string;
  primary_intent?: PrimaryIntent | string;
  hook_type?: HookType | string;
  narrative_structure?: NarrativeStructure | string;
  trust_mechanism?: string;
  cta_style?: string;
  energy_level?: EnergyLevel | string;
  authenticity_style?: string;
  pacing?: Pacing | string;
  script_dependency?: ScriptDependency | string;
}

// =============================================================================
// Interaction Planning Types
// =============================================================================

export type InteractionPrimitive =
  | "closeup_click_loop"
  | "selfie_click_while_talking"
  | "pocket_pull_and_click"
  | "desk_idle_click"
  | "anxiety_relief_click"
  | "sound_showcase_asmr"
  | "keychain_dangle_then_click"
  | "compare_clicks_variation";

export type InteractionFraming =
  | "macro_closeup"
  | "selfie_medium"
  | "close"
  | "desk_topdown";

export interface InteractionBeat {
  primitive?: InteractionPrimitive | string;
  duration_s?: number;
  framing?: InteractionFraming | string;
  audio_emphasis?: boolean;
  notes?: string;
}

export interface InteractionPlanData {
  sequence?: InteractionBeat[];
  total_duration_s?: number;
  key_mechanics_notes?: string;
  validation_warnings?: string[];
}

// =============================================================================
// Selected Interaction Types
// =============================================================================

export interface InteractionClip {
  id?: string;
  path?: string;
  primitive?: string;
  framing?: string;
  duration_s?: number;
  description?: string;
}

export interface SelectedInteraction {
  beat_index?: number;
  primitive?: string;
  match_status?: "matched" | "fallback" | "no_match" | string;
  clip?: InteractionClip | null;
  fallback_reason?: string;
}

// =============================================================================
// Product Analysis Types
// =============================================================================

export interface ProductVisualFeatures {
  colors?: string[];
  materials?: string[];
  finish?: "matte" | "glossy" | "translucent" | "mixed" | string;
  size_reference?: string;
  key_components?: string[];
  unique_features?: string[];
  best_angles?: string[];
}

// =============================================================================
// Pipeline State and Result Types
// =============================================================================

export type PipelineStatus = "idle" | "running" | "completed" | "failed";

export interface PipelineResult {
  jobId: string;
  status: PipelineStatus;
  currentStep: string;
  error: string | null;

  // Analysis results
  videoAnalysis: VideoAnalysisData | null;
  ugcIntent: UGCIntentData | null;
  interactionPlan: InteractionPlanData | null;
  selectedInteractions: SelectedInteraction[];

  // Generated content
  videoPrompt: string;
  suggestedScript: string;
  generatedVideoUrl: string;
}

// =============================================================================
// API Request/Response Types
// =============================================================================

export interface StartPipelineRequest {
  action: "start";
  videoUrl: string;
  productDescription?: string;
  productImages: string[];
  videoModel?: "sora" | "kling";
}

export interface StatusPipelineRequest {
  action: "status";
  jobId: string;
}

export type PipelineRequest = StartPipelineRequest | StatusPipelineRequest;

export interface StartPipelineResponse {
  jobId: string;
  status: "started";
}

export interface StatusPipelineResponse extends PipelineResult {}

export interface ErrorResponse {
  error: string;
}
