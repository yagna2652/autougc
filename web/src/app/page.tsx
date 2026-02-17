"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, X } from "lucide-react";
import { PipelineFlow } from "@/components/pipeline-flow";
import { NodeDetailDrawer } from "@/components/node-detail-drawer";
import type {
  PipelineNodeId,
  PipelineResult,
  PipelineStatus,
  VideoAnalysisData,
} from "@/types/pipeline";

type IdentityKey =
  | "front"
  | "side_45"
  | "back"
  | "close_up_logo"
  | "close_up_material";

const IDENTITY_SLOTS: { key: IdentityKey; label: string }[] = [
  { key: "front", label: "Front" },
  { key: "side_45", label: "Side 45" },
  { key: "back", label: "Back" },
  { key: "close_up_logo", label: "Close-up Logo" },
  { key: "close_up_material", label: "Close-up Material" },
];

export default function Home() {
  // Input state
  const [tiktokUrl, setTiktokUrl] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [productImages, setProductImages] = useState<File[]>([]);
  const [productImagesBase64, setProductImagesBase64] = useState<string[]>([]);
  const [videoModel, setVideoModel] = useState<"sora" | "kling" | "kling-v3">("sora");
  const [useIdentityPack, setUseIdentityPack] = useState(false);
  const [useTailImage, setUseTailImage] = useState(false);
  const [useAnchorFrames, setUseAnchorFrames] = useState(false);
  const [segmentDuration, setSegmentDuration] = useState(2);
  const [identityPack, setIdentityPack] = useState<{
    [K in IdentityKey]?: string;
  }>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Pipeline state
  const [status, setStatus] = useState<PipelineStatus>("idle");
  const [currentStep, setCurrentStep] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  // Results
  const [videoAnalysis, setVideoAnalysis] = useState<VideoAnalysisData | null>(
    null
  );
  const [videoPrompt, setVideoPrompt] = useState("");
  const [suggestedScript, setSuggestedScript] = useState("");
  const [sceneImageUrl, setSceneImageUrl] = useState("");
  const [generatedVideoUrl, setGeneratedVideoUrl] = useState("");

  // Drawer state
  const [selectedNode, setSelectedNode] = useState<PipelineNodeId | null>(null);

  // Convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
    });
  };

  // Handle file selection
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    // Add new files to existing ones
    const newFiles = [...productImages, ...files];
    setProductImages(newFiles);

    // Convert all files to base64
    const base64Promises = newFiles.map(fileToBase64);
    const base64Results = await Promise.all(base64Promises);
    setProductImagesBase64(base64Results);

    // Reset the input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Remove an image
  const removeImage = (index: number): void => {
    const newFiles = productImages.filter((_, i) => i !== index);
    const newBase64 = productImagesBase64.filter((_, i) => i !== index);
    setProductImages(newFiles);
    setProductImagesBase64(newBase64);
  };

  const handleIdentityFileSelect = async (
    key: IdentityKey,
    file: File | null
  ): Promise<void> => {
    if (!file) return;
    const base64 = await fileToBase64(file);
    setIdentityPack((prev) => ({ ...prev, [key]: base64 }));
  };

  // Poll for job status
  useEffect(() => {
    if (!jobId || status === "completed" || status === "failed") return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch("/api/pipeline", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "status", jobId }),
        });

        const data: PipelineResult = await response.json();

        setCurrentStep(data.currentStep);

        if (data.status === "completed") {
          setStatus("completed");
          setVideoAnalysis(data.videoAnalysis);
          setVideoPrompt(data.videoPrompt);
          setSuggestedScript(data.suggestedScript);
          setSceneImageUrl(data.sceneImageUrl);
          setGeneratedVideoUrl(data.generatedVideoUrl);
          clearInterval(interval);
        } else if (data.status === "failed") {
          setStatus("failed");
          setError(data.error || "Pipeline failed");
          clearInterval(interval);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, status]);

  const handleStart = async (): Promise<void> => {
    if (!tiktokUrl) {
      setError("Please enter a TikTok URL");
      return;
    }

    if (productImagesBase64.length === 0) {
      setError("Please upload at least one product image");
      return;
    }

    // Reset state
    setStatus("running");
    setCurrentStep("Starting...");
    setError(null);
    setVideoAnalysis(null);
    setVideoPrompt("");
    setSuggestedScript("");
    setSceneImageUrl("");
    setGeneratedVideoUrl("");

    try {
      const response = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            action: "start",
            videoUrl: tiktokUrl,
            productDescription,
            productImages: productImagesBase64,
            videoModel,
            productIdentityPack: Object.keys(identityPack).length ? identityPack : undefined,
            useIdentityPack,
            useTailImage,
            useAnchorFrames,
            segmentDuration,
          }),
        });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to start pipeline");
      }

      setJobId(data.jobId);
    } catch (err) {
      setStatus("failed");
      setError(err instanceof Error ? err.message : "Failed to start");
    }
  };

  const handleReset = (): void => {
    setStatus("idle");
    setCurrentStep("");
    setError(null);
    setJobId(null);
    setProductImages([]);
    setProductImagesBase64([]);
    setUseIdentityPack(false);
    setUseTailImage(false);
    setUseAnchorFrames(false);
    setSegmentDuration(2);
    setIdentityPack({});
    setVideoAnalysis(null);
    setVideoPrompt("");
    setSuggestedScript("");
    setSceneImageUrl("");
    setGeneratedVideoUrl("");
    setSelectedNode(null);
  };

  return (
    <main className="min-h-screen bg-[hsl(220,6%,9%)]">
      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Header */}
        <div className="mb-6 flex items-baseline justify-between">
          <div>
            <h1 className="font-mono text-2xl font-bold tracking-tight text-[hsl(220,4%,88%)]">
              AutoUGC
            </h1>
            <p className="text-xs text-[hsl(220,4%,45%)] font-mono">
              TikTok reference → UGC video
            </p>
          </div>
          {status !== "idle" && (
            <button
              onClick={handleReset}
              className="font-mono text-xs uppercase tracking-[0.05em] text-[hsl(220,4%,45%)] hover:text-[hsl(220,4%,70%)] transition-colors"
            >
              Reset
            </button>
          )}
        </div>

        {/* Pipeline Flow — always visible */}
        <PipelineFlow
          currentStep={currentStep}
          status={status}
          selectedNode={selectedNode}
          onNodeClick={(nodeId) =>
            setSelectedNode(selectedNode === nodeId ? null : nodeId)
          }
        />

        {/* Inputs — flat, no card wrapper */}
        <div className="mt-8 space-y-5">
          {/* Row 1: URL + Model */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_200px]">
            <div>
              <Label htmlFor="tiktok-url" className="text-[hsl(220,4%,45%)] font-mono text-xs uppercase tracking-[0.05em]">
                TikTok URL
              </Label>
              <Input
                id="tiktok-url"
                placeholder="https://www.tiktok.com/@user/video/..."
                value={tiktokUrl}
                onChange={(e) => setTiktokUrl(e.target.value)}
                disabled={status === "running"}
                className="mt-1.5 bg-[hsl(220,6%,13%)] border-[hsl(220,4%,18%)] text-[hsl(220,4%,88%)] placeholder:text-[hsl(220,4%,28%)] font-mono text-sm"
              />
            </div>
            <div>
              <Label htmlFor="video-model" className="text-[hsl(220,4%,45%)] font-mono text-xs uppercase tracking-[0.05em]">
                Model
              </Label>
              <Select
                value={videoModel}
                onValueChange={(value: "sora" | "kling" | "kling-v3") => setVideoModel(value)}
                disabled={status === "running"}
              >
                <SelectTrigger id="video-model" className="mt-1.5 bg-[hsl(220,6%,13%)] border-[hsl(220,4%,18%)] text-[hsl(220,4%,88%)] font-mono text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[hsl(220,6%,13%)] border-[hsl(220,4%,18%)]">
                  <SelectItem value="sora">Sora 2</SelectItem>
                  <SelectItem value="kling">Kling 2.5</SelectItem>
                  <SelectItem value="kling-v3">Kling V3</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Row 2: Description + Images side by side */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="product" className="text-[hsl(220,4%,45%)] font-mono text-xs uppercase tracking-[0.05em]">
                Product Description <span className="text-[hsl(220,4%,30%)]">(optional)</span>
              </Label>
              <Textarea
                id="product"
                placeholder="Describe your product..."
                value={productDescription}
                onChange={(e) => setProductDescription(e.target.value)}
                disabled={status === "running"}
                rows={3}
                className="mt-1.5 bg-[hsl(220,6%,13%)] border-[hsl(220,4%,18%)] text-[hsl(220,4%,88%)] placeholder:text-[hsl(220,4%,28%)] text-sm resize-none"
              />
            </div>
            <div>
              <Label className="text-[hsl(220,4%,45%)] font-mono text-xs uppercase tracking-[0.05em]">
                Product Images <span className="text-[hsl(0,70%,55%)]">*</span>
              </Label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileSelect}
                disabled={status === "running"}
                className="hidden"
              />
              {productImages.length === 0 ? (
                <div
                  onClick={() => status !== "running" && fileInputRef.current?.click()}
                  className={`mt-1.5 flex items-center justify-center gap-2 rounded-md border border-dashed border-[hsl(220,4%,18%)] p-6 cursor-pointer transition-colors ${
                    status === "running"
                      ? "opacity-50 cursor-not-allowed"
                      : "hover:border-[hsl(220,4%,30%)] hover:bg-[hsl(220,6%,11%)]"
                  }`}
                >
                  <Upload className="h-4 w-4 text-[hsl(220,4%,30%)]" />
                  <span className="text-sm text-[hsl(220,4%,35%)]">Upload images</span>
                </div>
              ) : (
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {productImages.map((file, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={productImagesBase64[index]}
                        alt={file.name}
                        className="h-16 w-16 object-cover rounded-md border border-[hsl(220,4%,18%)]"
                      />
                      <button
                        onClick={() => removeImage(index)}
                        disabled={status === "running"}
                        className="absolute -top-1.5 -right-1.5 bg-[hsl(220,6%,20%)] text-[hsl(220,4%,60%)] rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => status !== "running" && fileInputRef.current?.click()}
                    disabled={status === "running"}
                    className="flex h-16 w-16 items-center justify-center rounded-md border border-dashed border-[hsl(220,4%,18%)] text-[hsl(220,4%,30%)] hover:border-[hsl(220,4%,30%)] hover:text-[hsl(220,4%,45%)] transition-colors"
                  >
                    <Upload className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Advanced fidelity controls */}
          <div className="rounded-md border border-[hsl(220,4%,18%)] bg-[hsl(220,6%,11%)] p-4 space-y-4">
            <div className="text-[hsl(220,4%,45%)] font-mono text-xs uppercase tracking-[0.05em]">
              Advanced Fidelity
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="flex items-center gap-2 text-sm text-[hsl(220,4%,75%)]">
                <input
                  type="checkbox"
                  checked={useIdentityPack}
                  onChange={(e) => setUseIdentityPack(e.target.checked)}
                  disabled={status === "running"}
                />
                Use Identity Pack
              </label>
              <label className="flex items-center gap-2 text-sm text-[hsl(220,4%,75%)]">
                <input
                  type="checkbox"
                  checked={useTailImage}
                  onChange={(e) => setUseTailImage(e.target.checked)}
                  disabled={status === "running"}
                />
                Use Tail Image
              </label>
              <label className="flex items-center gap-2 text-sm text-[hsl(220,4%,75%)]">
                <input
                  type="checkbox"
                  checked={useAnchorFrames}
                  onChange={(e) => setUseAnchorFrames(e.target.checked)}
                  disabled={status === "running"}
                />
                Use Anchor Frames
              </label>
              <div className="flex items-center gap-2 text-sm text-[hsl(220,4%,75%)]">
                <span>Segment Seconds</span>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={segmentDuration}
                  onChange={(e) => setSegmentDuration(Number(e.target.value || 2))}
                  disabled={status === "running" || !useAnchorFrames}
                  className="h-8 w-20 bg-[hsl(220,6%,13%)] border-[hsl(220,4%,18%)] text-[hsl(220,4%,88%)]"
                />
              </div>
            </div>

            {useIdentityPack && (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {IDENTITY_SLOTS.map((slot) => (
                  <div key={slot.key}>
                    <Label className="text-[hsl(220,4%,45%)] font-mono text-xs uppercase tracking-[0.05em]">
                      {slot.label}
                    </Label>
                    <input
                      type="file"
                      accept="image/*"
                      disabled={status === "running"}
                      onChange={(e) =>
                        handleIdentityFileSelect(slot.key, e.target.files?.[0] || null)
                      }
                      className="mt-1.5 block w-full text-xs text-[hsl(220,4%,70%)]"
                    />
                    <div className="mt-1 text-xs text-[hsl(220,4%,40%)]">
                      {identityPack[slot.key] ? "Loaded" : "Not set"}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action row */}
          <div className="flex items-center gap-3">
            <Button
              onClick={handleStart}
              disabled={status === "running" || !tiktokUrl || productImagesBase64.length === 0}
              className="px-8"
            >
              {status === "running" ? "Processing..." : "Generate"}
            </Button>
            {error && status !== "running" && (
              <span className="text-sm font-mono text-[hsl(0,70%,55%)]">{error}</span>
            )}
          </div>
        </div>

        {/* Node Detail Drawer */}
        <NodeDetailDrawer
          node={selectedNode}
          open={selectedNode !== null}
          onOpenChange={(open) => {
            if (!open) setSelectedNode(null);
          }}
          videoAnalysis={videoAnalysis}
          videoPrompt={videoPrompt}
          suggestedScript={suggestedScript}
          sceneImageUrl={sceneImageUrl}
          generatedVideoUrl={generatedVideoUrl}
        />

        {/* Footer */}
        <div className="mt-12 text-center text-xs text-[hsl(220,4%,25%)] font-mono">
          Powered by Claude Vision, LangGraph, and Fal.ai
        </div>
      </div>
    </main>
  );
}
