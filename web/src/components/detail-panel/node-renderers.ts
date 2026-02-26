import type { ComponentType } from "react";
import type { NodeState, PipelineStatus } from "@/hooks/use-pipeline";
import { DownloadVideoOutput } from "./renderers/download-video";
import { ExtractFramesOutput } from "./renderers/extract-frames";
import { AnalyzeVideoOutput } from "./renderers/analyze-video";
import { GeneratePromptOutput } from "./renderers/generate-prompt";
import { ValidatePromptOutput } from "./renderers/validate-prompt";
import { GenerateSceneImageOutput } from "./renderers/generate-scene-image";
import { GenerateVideoOutput } from "./renderers/generate-video";

export interface NodeOutputRendererProps {
  output: Record<string, unknown>;
  nodeState: NodeState;
  pipelineStatus?: PipelineStatus;
  resumePipeline?: (editedPrompt?: string) => void;
}

export const NODE_RENDERERS: Record<string, ComponentType<NodeOutputRendererProps>> = {
  download_video: DownloadVideoOutput,
  extract_frames: ExtractFramesOutput,
  analyze_video: AnalyzeVideoOutput,
  generate_prompt: GeneratePromptOutput,
  validate_prompt: ValidatePromptOutput,
  generate_scene_image: GenerateSceneImageOutput,
  generate_video: GenerateVideoOutput,
};
