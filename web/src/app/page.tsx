"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, X } from "lucide-react";
import type {
  PipelineResult,
  PipelineStatus,
  VideoAnalysisData,
} from "@/types/pipeline";

export default function Home() {
  // Input state
  const [tiktokUrl, setTiktokUrl] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [productImages, setProductImages] = useState<File[]>([]);
  const [productImagesBase64, setProductImagesBase64] = useState<string[]>([]);
  const [videoModel, setVideoModel] = useState<"sora" | "kling">("sora");
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
    setVideoAnalysis(null);
    setVideoPrompt("");
    setSuggestedScript("");
    setSceneImageUrl("");
    setGeneratedVideoUrl("");
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">AutoUGC</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Generate UGC-style videos from TikTok references
          </p>
        </div>

        {/* Input Section */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>1. Enter TikTok URL</CardTitle>
            <CardDescription>
              Paste a TikTok URL to analyze its style and generate a similar
              video
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="tiktok-url">TikTok URL</Label>
              <Input
                id="tiktok-url"
                placeholder="https://www.tiktok.com/@user/video/..."
                value={tiktokUrl}
                onChange={(e) => setTiktokUrl(e.target.value)}
                disabled={status === "running"}
              />
            </div>
            <div>
              <Label htmlFor="product">Product Description (optional)</Label>
              <Textarea
                id="product"
                placeholder="Describe your product to feature in the video..."
                value={productDescription}
                onChange={(e) => setProductDescription(e.target.value)}
                disabled={status === "running"}
                rows={3}
              />
            </div>
            <div>
              <Label>
                Product Images <span className="text-red-500">*</span>
              </Label>
              <p className="text-sm text-gray-500 mb-2">
                Upload images of your product (required)
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileSelect}
                disabled={status === "running"}
                className="hidden"
              />
              <div
                onClick={() =>
                  status !== "running" && fileInputRef.current?.click()
                }
                className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
                  status === "running"
                    ? "opacity-50 cursor-not-allowed"
                    : "hover:border-primary hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                <Upload className="mx-auto h-8 w-8 text-gray-400 mb-2" />
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Click to upload or drag and drop
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  PNG, JPG, WEBP up to 10MB each
                </p>
              </div>
              {productImages.length > 0 && (
                <div className="mt-3 grid grid-cols-4 gap-2">
                  {productImages.map((file, index) => (
                    <div key={index} className="relative group">
                      <img
                        src={productImagesBase64[index]}
                        alt={file.name}
                        className="w-full h-20 object-cover rounded-lg border"
                      />
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          removeImage(index);
                        }}
                        disabled={status === "running"}
                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
                      >
                        <X className="h-3 w-3" />
                      </button>
                      <p className="text-xs text-gray-500 truncate mt-1">
                        {file.name}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div>
              <Label htmlFor="video-model">Video Generation Model</Label>
              <Select
                value={videoModel}
                onValueChange={(value: "sora" | "kling") =>
                  setVideoModel(value)
                }
                disabled={status === "running"}
              >
                <SelectTrigger id="video-model" className="mt-1">
                  <SelectValue placeholder="Select model" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sora">Sora 2 (OpenAI)</SelectItem>
                  <SelectItem value="kling">Kling 2.5 (Kuaishou)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-gray-500 mt-1">
                {videoModel === "sora"
                  ? "Sora 2 - Best for realistic, cinematic videos (4/8/12s)"
                  : "Kling 2.5 - Fast generation with good quality (5s)"}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleStart}
                disabled={
                  status === "running" ||
                  !tiktokUrl ||
                  productImagesBase64.length === 0
                }
                className="flex-1"
              >
                {status === "running" ? "Processing..." : "Generate Video"}
              </Button>
              {status !== "idle" && (
                <Button variant="outline" onClick={handleReset}>
                  Reset
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Status Section */}
        {status !== "idle" && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                2. Pipeline Status
                <Badge
                  variant={
                    status === "completed"
                      ? "default"
                      : status === "failed"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {status}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {status === "running" && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
                    <span>{currentStep || "Processing..."}</span>
                  </div>
                  <div className="text-sm text-gray-500">
                    This may take a few minutes...
                  </div>
                </div>
              )}

              {status === "failed" && error && (
                <div className="text-red-600 dark:text-red-400">
                  Error: {error}
                </div>
              )}

              {status === "completed" && (
                <div className="text-green-600 dark:text-green-400">
                  Pipeline completed successfully
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Results Section */}
        {status === "completed" && (
          <>
            {/* Video Analysis */}
            {videoAnalysis && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>3. Video Analysis</CardTitle>
                  <CardDescription>
                    What we learned from the TikTok video
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-auto text-sm">
                    {JSON.stringify(videoAnalysis, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}

            {/* Generated Prompt */}
            {videoPrompt && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>4. Generated Video Prompt</CardTitle>
                  <CardDescription>
                    The prompt used for video generation
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg whitespace-pre-wrap">
                    {videoPrompt}
                  </div>
                  {suggestedScript && (
                    <div className="mt-4">
                      <Label>Suggested Script</Label>
                      <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg mt-2 italic">
                        "{suggestedScript}"
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Scene Image (Nano Banana Pro) */}
            {sceneImageUrl && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>5. Scene Image</CardTitle>
                  <CardDescription>
                    Product composited into a TikTok-style scene (used as I2V
                    starting frame)
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="max-w-sm mx-auto">
                    <img
                      src={sceneImageUrl}
                      alt="Generated scene"
                      className="w-full rounded-lg"
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Generated Video */}
            {generatedVideoUrl && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>6. Generated Video</CardTitle>
                  <CardDescription>
                    Your UGC-style video is ready!
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="aspect-[9/16] max-w-sm mx-auto bg-black rounded-lg overflow-hidden">
                    <video
                      src={generatedVideoUrl}
                      controls
                      className="w-full h-full object-contain"
                      autoPlay
                      loop
                    />
                  </div>
                  <div className="mt-4 flex justify-center">
                    <Button asChild>
                      <a href={generatedVideoUrl} download="ugc-video.mp4">
                        Download Video
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* No video but prompt exists */}
            {!generatedVideoUrl && videoPrompt && (
              <Card className="mb-6 border-yellow-500">
                <CardHeader>
                  <CardTitle>Video Generation</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-yellow-600 dark:text-yellow-400">
                    Video generation may have been skipped or is still
                    processing. You can use the prompt above with Sora, Kling,
                    or other video generation tools.
                  </p>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Footer */}
        <div className="text-center text-sm text-gray-500 mt-8">
          <p>Powered by Claude Vision, LangGraph, and Fal.ai</p>
        </div>
      </div>
    </main>
  );
}
