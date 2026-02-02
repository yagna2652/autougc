"use client";

import { useState, useEffect } from "react";
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

type Status = "idle" | "running" | "completed" | "failed";

interface PipelineResult {
  jobId: string;
  status: Status;
  currentStep: string;
  error: string | null;
  videoAnalysis: Record<string, unknown> | null;
  ugcIntent: Record<string, unknown> | null;
  videoPrompt: string;
  suggestedScript: string;
  generatedVideoUrl: string;
}

export default function Home() {
  // Input state
  const [tiktokUrl, setTiktokUrl] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [videoModel, setVideoModel] = useState<"sora" | "kling">("sora");

  // Pipeline state
  const [status, setStatus] = useState<Status>("idle");
  const [currentStep, setCurrentStep] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  // Results
  const [videoAnalysis, setVideoAnalysis] = useState<Record<
    string,
    unknown
  > | null>(null);
  const [ugcIntent, setUgcIntent] = useState<Record<string, unknown> | null>(
    null
  );
  const [videoPrompt, setVideoPrompt] = useState("");
  const [suggestedScript, setSuggestedScript] = useState("");
  const [generatedVideoUrl, setGeneratedVideoUrl] = useState("");

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
          setUgcIntent(data.ugcIntent || null);
          setVideoPrompt(data.videoPrompt);
          setSuggestedScript(data.suggestedScript);
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

  const handleStart = async () => {
    if (!tiktokUrl) {
      setError("Please enter a TikTok URL");
      return;
    }

    // Reset state
    setStatus("running");
    setCurrentStep("Starting...");
    setError(null);
    setVideoAnalysis(null);
    setUgcIntent(null);
    setVideoPrompt("");
    setSuggestedScript("");
    setGeneratedVideoUrl("");

    try {
      const response = await fetch("/api/pipeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "start",
          videoUrl: tiktokUrl,
          productDescription,
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

  const handleReset = () => {
    setStatus("idle");
    setCurrentStep("");
    setError(null);
    setJobId(null);
    setVideoAnalysis(null);
    setUgcIntent(null);
    setVideoPrompt("");
    setSuggestedScript("");
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
                disabled={status === "running" || !tiktokUrl}
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
                  ✓ Pipeline completed successfully
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

            {/* UGC Classification */}
            {ugcIntent && Object.keys(ugcIntent).length > 0 && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>4. UGC Classification</CardTitle>
                  <CardDescription>
                    Semantic intent classification for this video
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-auto text-sm">
                    {JSON.stringify(ugcIntent, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}

            {/* Generated Prompt */}
            {videoPrompt && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>5. Generated Video Prompt</CardTitle>
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
