"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { PIPELINE_NODES } from "@/components/pipeline-flow";
import type { PipelineNodeId, VideoAnalysisData } from "@/types/pipeline";

interface NodeDetailDrawerProps {
  node: PipelineNodeId | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  videoAnalysis: VideoAnalysisData | null;
  videoPrompt: string;
  suggestedScript: string;
  sceneImageUrl: string;
  generatedVideoUrl: string;
}

export function NodeDetailDrawer({
  node,
  open,
  onOpenChange,
  videoAnalysis,
  videoPrompt,
  suggestedScript,
  sceneImageUrl,
  generatedVideoUrl,
}: NodeDetailDrawerProps) {
  const nodeDef = node ? PIPELINE_NODES.find((n) => n.id === node) : null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[480px] sm:max-w-[480px] bg-[hsl(220,6%,11%)] border-[hsl(220,4%,20%)] overflow-y-auto"
      >
        <SheetHeader>
          <SheetTitle className="font-mono text-sm uppercase tracking-[0.05em] text-[hsl(220,4%,88%)]">
            {nodeDef?.label ?? "Node"}
          </SheetTitle>
          <SheetDescription className="text-[hsl(220,4%,45%)]">
            {descriptionForNode(node)}
          </SheetDescription>
        </SheetHeader>

        <div className="px-4 pb-6">
          {node === "download_video" && (
            <ConfirmationBlock text="Video downloaded and saved to temporary storage." />
          )}

          {node === "extract_frames" && (
            <ConfirmationBlock text="Key frames extracted from the video for analysis." />
          )}

          {node === "analyze_video" && videoAnalysis && (
            <div className="rounded-md bg-[hsl(220,6%,9%)] p-4 overflow-auto">
              <pre className="font-mono text-xs text-[hsl(220,4%,75%)] whitespace-pre-wrap leading-relaxed">
                {JSON.stringify(videoAnalysis, null, 2)}
              </pre>
            </div>
          )}

          {node === "generate_prompt" && (
            <div className="space-y-4">
              {videoPrompt && (
                <div>
                  <Label>Video Prompt</Label>
                  <div className="mt-2 rounded-md bg-[hsl(220,6%,9%)] p-4 font-mono text-xs text-[hsl(220,4%,75%)] whitespace-pre-wrap leading-relaxed">
                    {videoPrompt}
                  </div>
                </div>
              )}
              {suggestedScript && (
                <div>
                  <Label>Suggested Script</Label>
                  <div className="mt-2 rounded-md bg-[hsl(210,80%,60%)]/5 border border-[hsl(210,80%,60%)]/20 p-4 text-sm text-[hsl(210,80%,75%)] italic leading-relaxed">
                    &ldquo;{suggestedScript}&rdquo;
                  </div>
                </div>
              )}
            </div>
          )}

          {node === "generate_scene_image" && sceneImageUrl && (
            <div className="space-y-3">
              <img
                src={sceneImageUrl}
                alt="Generated scene"
                className="w-full rounded-md border border-[hsl(220,4%,20%)]"
              />
              <p className="font-mono text-xs text-[hsl(220,4%,45%)]">
                Product composited into a TikTok-style scene (I2V starting frame)
              </p>
            </div>
          )}

          {node === "generate_scene_image" && !sceneImageUrl && (
            <ConfirmationBlock text="Scene image generation was skipped." />
          )}

          {node === "generate_video" && generatedVideoUrl && (
            <div className="space-y-4">
              <div className="aspect-[9/16] max-w-[280px] mx-auto bg-black rounded-md overflow-hidden">
                <video
                  src={generatedVideoUrl}
                  controls
                  autoPlay
                  loop
                  className="w-full h-full object-contain"
                />
              </div>
              <Button asChild className="w-full" variant="outline">
                <a href={generatedVideoUrl} download="ugc-video.mp4">
                  <Download className="mr-2 h-4 w-4" />
                  Download Video
                </a>
              </Button>
            </div>
          )}

          {node === "generate_video" && !generatedVideoUrl && (
            <ConfirmationBlock text="Video generation completed but no URL was returned." />
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="font-mono text-xs uppercase tracking-[0.05em] text-[hsl(220,4%,45%)]">
      {children}
    </div>
  );
}

function ConfirmationBlock({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3 rounded-md bg-[hsl(145,65%,42%)]/10 border border-[hsl(145,65%,42%)]/20 p-4">
      <span className="h-2 w-2 rounded-full bg-[hsl(145,65%,42%)] shrink-0" />
      <span className="text-sm text-[hsl(145,65%,60%)]">{text}</span>
    </div>
  );
}

function descriptionForNode(node: PipelineNodeId | null): string {
  switch (node) {
    case "download_video":
      return "Downloaded the TikTok video for processing";
    case "extract_frames":
      return "Extracted key frames for visual analysis";
    case "analyze_video":
      return "AI analysis of video style, framing, and content";
    case "generate_prompt":
      return "Generated video prompt and suggested script";
    case "generate_scene_image":
      return "Product scene image for video generation";
    case "generate_video":
      return "Final generated UGC-style video";
    default:
      return "";
  }
}
