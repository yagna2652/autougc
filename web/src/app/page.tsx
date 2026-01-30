"use client";

import { useState } from "react";
import { VideoGenerationLoader } from "@/components/video-loader";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

type Step = 1 | 2 | 3 | 4;

interface BlueprintData {
  transcript: string;
  hookStyle: string;
  bodyFramework: string;
  ctaUrgency: string;
  setting: string;
  lighting: string;
  energy: string;
  duration: number;
}

export default function Home() {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [tiktokUrl, setTiktokUrl] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [blueprintData, setBlueprintData] = useState<BlueprintData | null>(
    null,
  );
  const [productImages, setProductImages] = useState<File[]>([]);
  const [productDescription, setProductDescription] = useState("");
  const [selectedModel, setSelectedModel] = useState<"sora2" | "kling">(
    "sora2",
  );
  const [generatedPrompt, setGeneratedPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedVideoUrl, setGeneratedVideoUrl] = useState<string | null>(
    null,
  );
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationProgress, setGenerationProgress] = useState<string>("");
  const [generationCount, setGenerationCount] = useState(0);
  const [isAnalyzingProduct, setIsAnalyzingProduct] = useState(false);
  const [productAnalysis, setProductAnalysis] = useState<{
    type: string;
    description: string;
    keyFeatures: string[];
    suggestedShowcase: string;
  } | null>(null);
  const [suggestedScript, setSuggestedScript] = useState("");
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [useImageToVideo, setUseImageToVideo] = useState(true);
  const [analysisProgress, setAnalysisProgress] = useState<string>("");

  // Product Context fields for custom mechanics
  const [showAdvancedProduct, setShowAdvancedProduct] = useState(false);
  const [productType, setProductType] = useState("");
  const [productInteractions, setProductInteractions] = useState("");
  const [tactileFeatures, setTactileFeatures] = useState("");
  const [soundFeatures, setSoundFeatures] = useState("");
  const [sizeDescription, setSizeDescription] = useState("");
  const [highlightFeature, setHighlightFeature] = useState("");
  const [customInstructions, setCustomInstructions] = useState("");

  const handleAnalyzeTikTok = async () => {
    if (!tiktokUrl) return;

    setIsAnalyzing(true);
    setAnalysisProgress("Starting analysis...");
    setAnalysisError(null);

    try {
      // Start analysis job
      const response = await fetch("/api/analyze-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_url: tiktokUrl,
          options: {
            enhanced: true,
            whisper_mode: "local",
            num_frames: 5,
            scene_frames: 20,
          },
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || "Failed to start analysis");
      }

      const { job_id } = await response.json();

      // Poll for status
      pollJobStatus(job_id);
    } catch (error) {
      setIsAnalyzing(false);
      setAnalysisError(
        error instanceof Error ? error.message : "Failed to start analysis",
      );
    }
  };

  const pollJobStatus = async (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/analyze-video/${jobId}`);

        if (!response.ok) {
          throw new Error("Failed to get job status");
        }

        const data = await response.json();

        // Update progress
        if (data.progress?.current_step) {
          setAnalysisProgress(
            `${data.progress.current_step} (${data.progress.step_number}/${data.progress.total_steps})`,
          );
        }

        if (data.status === "completed") {
          clearInterval(pollInterval);

          // Map blueprint result to state
          const blueprint = data.result;
          setBlueprintData({
            transcript: blueprint.transcript.full_text,
            hookStyle: blueprint.structure.hook.style,
            bodyFramework: blueprint.structure.body.framework,
            ctaUrgency: blueprint.structure.cta.urgency,
            setting: blueprint.visual_style.setting,
            lighting: blueprint.visual_style.lighting,
            energy: blueprint.audio_style.energy,
            duration: blueprint.total_duration || 20,
          });

          setIsAnalyzing(false);
          setAnalysisProgress("");
          setCurrentStep(2);
        } else if (data.status === "failed") {
          clearInterval(pollInterval);
          setIsAnalyzing(false);
          setAnalysisProgress("");
          setAnalysisError(data.error || "Analysis failed");
        }
      } catch (error) {
        console.error("Polling error:", error);
        clearInterval(pollInterval);
        setIsAnalyzing(false);
        setAnalysisProgress("");
        setAnalysisError("Failed to check analysis status");
      }
    }, 3000); // Poll every 3 seconds
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setProductImages((prev) => [...prev, ...files].slice(0, 9));
      // Clear uploaded URL when images change so we re-upload
      setUploadedImageUrl(null);
    }
  };

  const removeImage = (index: number) => {
    setProductImages((prev) => prev.filter((_, i) => i !== index));
    // Clear uploaded URL when images change so we re-upload
    setUploadedImageUrl(null);
  };

  // Compress and resize image to reduce payload size for Claude API
  const compressImage = (
    file: File,
    maxWidth = 800,
    quality = 0.7,
  ): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement("canvas");
          let width = img.width;
          let height = img.height;

          // Scale down if larger than maxWidth
          if (width > maxWidth) {
            height = (height * maxWidth) / width;
            width = maxWidth;
          }

          canvas.width = width;
          canvas.height = height;

          const ctx = canvas.getContext("2d");
          if (!ctx) {
            reject(new Error("Failed to get canvas context"));
            return;
          }

          ctx.drawImage(img, 0, 0, width, height);

          // Convert to base64 with compression
          const base64 = canvas.toDataURL("image/jpeg", quality);
          resolve(base64);
        };
        img.onerror = () => reject(new Error("Failed to load image"));
        img.src = e.target?.result as string;
      };
      reader.onerror = () => reject(new Error("Failed to read file"));
      reader.readAsDataURL(file);
    });
  };

  const handleGeneratePrompt = async () => {
    if (!blueprintData) return;

    // If no product images, use template-based prompt
    if (productImages.length === 0) {
      const prompt = `iPhone 13 front facing camera video, filmed vertically for TikTok,
a real young woman not a model, mid-20s, average everyday appearance,
holding ${productDescription || "the product"} up to show the camera while talking excitedly,

CRITICAL - MUST LOOK REAL NOT AI:
- skin has visible pores especially on nose, natural sebum shine on t-zone
- slight dark circles under eyes, normal human imperfections
- eyes looking at the phone screen not the lens, that typical selfie video eye line
- natural asymmetrical face, one eye slightly different than other
- real hair with flyaways, not perfectly styled

CAMERA FEEL:
- handheld shake from her arm getting tired holding phone up
- slight focus hunting occasionally
- that iPhone front camera slight distortion
- NO stabilization, raw footage feel

ENVIRONMENT:
- ${blueprintData.setting}
- ${blueprintData.lighting}
- not aesthetically arranged, real life mess

ENERGY:
- ${blueprintData.energy} energy level
- genuinely likes the product, not acting
- talking like she's FaceTiming her best friend
- natural umms and pauses, not scripted delivery
- real smile that reaches her eyes

HOOK STYLE: ${blueprintData.hookStyle}
BODY FRAMEWORK: ${blueprintData.bodyFramework}
CTA: ${blueprintData.ctaUrgency}

SCRIPT REFERENCE:
"${blueprintData.transcript}"`;

      setGeneratedPrompt(prompt);
      setCurrentStep(4);
      return;
    }

    // Use Claude to analyze product images and generate smart prompt
    setIsAnalyzingProduct(true);
    setAnalysisError(null);

    try {
      // Convert images to base64 with compression (max 800px, 70% quality)
      const base64Images = await Promise.all(
        productImages.slice(0, 3).map((file) => compressImage(file, 800, 0.7)),
      );

      // Build product context if any advanced fields are filled
      const hasProductContext = productType || productInteractions || tactileFeatures ||
        soundFeatures || sizeDescription || highlightFeature || customInstructions;

      const productContext = hasProductContext ? {
        type: productType,
        interactions: productInteractions.split(",").map(s => s.trim()).filter(Boolean),
        tactileFeatures: tactileFeatures.split(",").map(s => s.trim()).filter(Boolean),
        soundFeatures: soundFeatures.split(",").map(s => s.trim()).filter(Boolean),
        sizeDescription,
        highlightFeature,
        customInstructions,
      } : undefined;

      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          productImages: base64Images,
          productDescription,
          blueprintData,
          productContext,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to analyze product");
      }

      if (data.success) {
        setProductAnalysis(data.analysis);
        setGeneratedPrompt(data.prompt);
        setSuggestedScript(data.suggestedScript || "");
        setCurrentStep(4);
      } else {
        throw new Error("Analysis failed");
      }
    } catch (error) {
      console.error("Analysis error:", error);
      setAnalysisError(
        error instanceof Error ? error.message : "Unknown error occurred",
      );
    } finally {
      setIsAnalyzingProduct(false);
    }
  };

  const handleGenerateVideo = async () => {
    setIsGenerating(true);
    setGenerationError(null);
    setGeneratedVideoUrl(null);
    setGenerationProgress("Preparing generation...");
    setGenerationCount((prev) => prev + 1);

    try {
      let imageUrl = uploadedImageUrl;

      // If using image-to-video and we have product images but no uploaded URL yet, upload first
      if (useImageToVideo && productImages.length > 0 && !uploadedImageUrl) {
        setGenerationProgress("Uploading product image...");

        // Compress the first product image and upload it
        const base64Image = await compressImage(productImages[0], 1024, 0.85);

        const uploadResponse = await fetch("/api/upload", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ base64Image }),
        });

        const uploadData = await uploadResponse.json();

        if (!uploadResponse.ok) {
          throw new Error(uploadData.error || "Failed to upload product image");
        }

        imageUrl = uploadData.url;
        setUploadedImageUrl(imageUrl);
      }

      setGenerationProgress("Submitting generation request...");

      // Build request body
      const requestBody: {
        prompt: string;
        model: string;
        duration: number;
        aspectRatio: string;
        imageUrl?: string;
      } = {
        prompt: generatedPrompt,
        model: selectedModel,
        duration: 5,
        aspectRatio: "9:16",
      };

      // Add image URL if using image-to-video mode
      if (useImageToVideo && imageUrl) {
        requestBody.imageUrl = imageUrl;
        setGenerationProgress("Generating video from product image...");
      } else {
        setGenerationProgress("Generating video from text prompt...");
      }

      const response = await fetch("/api/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const data = await response.json();

      if (!response.ok) {
        // Include details in error message if available
        let errorMsg = data.error || "Failed to generate video";
        if (data.details) {
          errorMsg += `: ${JSON.stringify(data.details)}`;
        }
        throw new Error(errorMsg);
      }

      if (data.success && data.videoUrl) {
        setGeneratedVideoUrl(data.videoUrl);
        const mode = data.usedProductImage ? "image-to-video" : "text-to-video";
        setGenerationProgress(`Video generated successfully! (${mode})`);
      } else {
        throw new Error("No video URL returned");
      }
    } catch (error) {
      console.error("Generation error:", error);
      setGenerationError(
        error instanceof Error ? error.message : "Unknown error occurred",
      );
      setGenerationProgress("");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownloadVideo = async () => {
    if (!generatedVideoUrl) return;

    try {
      const response = await fetch(generatedVideoUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ugc-video-${Date.now()}.mp4`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download error:", error);
      // Fallback: open in new tab
      window.open(generatedVideoUrl, "_blank");
    }
  };

  const steps = [
    { num: 1, title: "TikTok URL", description: "Paste source video" },
    { num: 2, title: "Product", description: "Upload product images" },
    { num: 3, title: "Generate Prompt", description: "Create UGC prompt" },
    { num: 4, title: "Generate Video", description: "Select model & generate" },
  ];

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">AutoUGC</h1>
          <p className="text-muted-foreground">
            Generate authentic UGC-style videos from TikTok blueprints
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex justify-between mb-8">
          {steps.map((step, index) => (
            <div
              key={step.num}
              className={`flex items-center ${
                index < steps.length - 1 ? "flex-1" : ""
              }`}
            >
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-medium ${
                    currentStep >= step.num
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {step.num}
                </div>
                <div className="mt-2 text-center">
                  <p className="text-sm font-medium">{step.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {step.description}
                  </p>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-4 mt-[-20px] ${
                    currentStep > step.num ? "bg-primary" : "bg-muted"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: TikTok URL */}
        {currentStep === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Step 1: Enter TikTok URL</CardTitle>
              <CardDescription>
                Paste the URL of a TikTok video to analyze its structure and
                style
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="tiktok-url">TikTok URL</Label>
                <Input
                  id="tiktok-url"
                  placeholder="https://www.tiktok.com/@username/video/..."
                  value={tiktokUrl}
                  onChange={(e) => setTiktokUrl(e.target.value)}
                />
              </div>
              <Button
                onClick={handleAnalyzeTikTok}
                disabled={!tiktokUrl || isAnalyzing}
                className="w-full"
              >
                {isAnalyzing ? "Analyzing..." : "Analyze TikTok"}
              </Button>

              {/* Progress indicator */}
              {isAnalyzing && analysisProgress && (
                <div className="mt-4 rounded-lg border border-border bg-muted/50 p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <div>
                      <p className="font-medium">{analysisProgress}</p>
                      <p className="text-sm text-muted-foreground">
                        This may take 2-5 minutes depending on video length
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{
                        width: analysisProgress.includes("/")
                          ? `${(parseInt(analysisProgress.split("(")[1]?.split("/")[0] || "0") / parseInt(analysisProgress.split("/")[1]?.split(")")[0] || "11")) * 100}%`
                          : "10%",
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Error display */}
              {analysisError && (
                <div className="mt-4 rounded-lg border border-destructive bg-destructive/10 p-4">
                  <p className="font-medium text-destructive">
                    Analysis Failed
                  </p>
                  <p className="text-sm text-destructive/80">
                    {analysisError}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 2: Product Images */}
        {currentStep === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Step 2: Upload Product Images</CardTitle>
              <CardDescription>
                Upload up to 9 product images from different angles
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Blueprint Summary */}
              {blueprintData && (
                <div className="bg-muted p-4 rounded-lg mb-4">
                  <h4 className="font-medium mb-2">Extracted Blueprint</h4>
                  <div className="flex flex-wrap gap-2">
                    <Badge variant="secondary">
                      Hook: {blueprintData.hookStyle}
                    </Badge>
                    <Badge variant="secondary">
                      Body: {blueprintData.bodyFramework}
                    </Badge>
                    <Badge variant="secondary">
                      CTA: {blueprintData.ctaUrgency}
                    </Badge>
                    <Badge variant="secondary">
                      Energy: {blueprintData.energy}
                    </Badge>
                    <Badge variant="secondary">{blueprintData.duration}s</Badge>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="product-images">Product Images (up to 9)</Label>
                <Input
                  id="product-images"
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageUpload}
                  disabled={productImages.length >= 9}
                />
              </div>

              {/* Image Preview Grid */}
              {productImages.length > 0 && (
                <div className="grid grid-cols-3 gap-4">
                  {productImages.map((file, index) => (
                    <div
                      key={index}
                      className="relative aspect-square bg-muted rounded-lg overflow-hidden"
                    >
                      <img
                        src={URL.createObjectURL(file)}
                        alt={`Product ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                      <button
                        onClick={() => removeImage(index)}
                        className="absolute top-1 right-1 bg-destructive text-destructive-foreground rounded-full w-6 h-6 flex items-center justify-center text-xs"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="product-description">Product Description</Label>
                <Textarea
                  id="product-description"
                  placeholder="Describe your product (e.g., 'green vitamin gummy bottle', 'wireless earbuds in charging case')"
                  value={productDescription}
                  onChange={(e) => setProductDescription(e.target.value)}
                  rows={3}
                />
              </div>

              {/* Advanced Product Details (Collapsible) */}
              <div className="border border-border rounded-lg overflow-hidden">
                <button
                  type="button"
                  onClick={() => setShowAdvancedProduct(!showAdvancedProduct)}
                  className="w-full px-4 py-3 flex items-center justify-between bg-muted/50 hover:bg-muted transition-colors"
                >
                  <span className="font-medium text-sm">Advanced Product Details</span>
                  <span className="text-muted-foreground text-xs">
                    {showAdvancedProduct ? "▲ Hide" : "▼ Show"} (for custom mechanics)
                  </span>
                </button>

                {showAdvancedProduct && (
                  <div className="p-4 space-y-4 bg-muted/20">
                    <p className="text-xs text-muted-foreground">
                      These fields help generate product-specific video mechanics (e.g., how to show tactile feedback, sounds, size).
                    </p>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="product-type">Product Type</Label>
                        <Input
                          id="product-type"
                          placeholder="e.g., mechanical keyboard fidget keychain"
                          value={productType}
                          onChange={(e) => setProductType(e.target.value)}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="size-description">Size Description</Label>
                        <Input
                          id="size-description"
                          placeholder="e.g., small palm-sized, handheld"
                          value={sizeDescription}
                          onChange={(e) => setSizeDescription(e.target.value)}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="product-interactions">Interactions</Label>
                      <Input
                        id="product-interactions"
                        placeholder="e.g., pressing keys, clicking switches, fidgeting (comma-separated)"
                        value={productInteractions}
                        onChange={(e) => setProductInteractions(e.target.value)}
                      />
                      <p className="text-xs text-muted-foreground">How users interact with the product</p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="tactile-features">Tactile Features</Label>
                        <Input
                          id="tactile-features"
                          placeholder="e.g., responsive keys, satisfying click"
                          value={tactileFeatures}
                          onChange={(e) => setTactileFeatures(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">Touch/feel qualities</p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="sound-features">Sound Features</Label>
                        <Input
                          id="sound-features"
                          placeholder="e.g., mechanical click sounds"
                          value={soundFeatures}
                          onChange={(e) => setSoundFeatures(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">Audio qualities to emphasize</p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="highlight-feature">Key Feature to Highlight</Label>
                      <Input
                        id="highlight-feature"
                        placeholder="e.g., the clicking/pressing fidget action"
                        value={highlightFeature}
                        onChange={(e) => setHighlightFeature(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="custom-instructions">Custom Instructions</Label>
                      <Textarea
                        id="custom-instructions"
                        placeholder="Any additional instructions for how to showcase the product..."
                        value={customInstructions}
                        onChange={(e) => setCustomInstructions(e.target.value)}
                        rows={2}
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setCurrentStep(1)}>
                  Back
                </Button>
                <Button onClick={() => setCurrentStep(3)} className="flex-1">
                  Continue
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Generate Prompt */}
        {currentStep === 3 && (
          <Card>
            <CardHeader>
              <CardTitle>Step 3: Generate UGC Prompt</CardTitle>
              <CardDescription>
                Review settings and generate the video prompt
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {blueprintData && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Hook Style</Label>
                    <Input value={blueprintData.hookStyle} readOnly />
                  </div>
                  <div className="space-y-2">
                    <Label>Body Framework</Label>
                    <Input value={blueprintData.bodyFramework} readOnly />
                  </div>
                  <div className="space-y-2">
                    <Label>CTA Urgency</Label>
                    <Input value={blueprintData.ctaUrgency} readOnly />
                  </div>
                  <div className="space-y-2">
                    <Label>Energy Level</Label>
                    <Input value={blueprintData.energy} readOnly />
                  </div>
                  <div className="col-span-2 space-y-2">
                    <Label>Setting</Label>
                    <Input value={blueprintData.setting} readOnly />
                  </div>
                  <div className="col-span-2 space-y-2">
                    <Label>Product</Label>
                    <Input
                      value={productDescription || "Not specified"}
                      readOnly
                    />
                  </div>
                </div>
              )}

              <Separator />

              {/* Analysis loading state */}
              {isAnalyzingProduct && (
                <div className="rounded-lg border border-border bg-muted/50 p-4">
                  <div className="flex items-center gap-3">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    <div>
                      <p className="font-medium">
                        Analyzing product images with Claude AI...
                      </p>
                      <p className="text-sm text-muted-foreground">
                        This will generate a smart, customized prompt for your
                        product.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Analysis error */}
              {analysisError && (
                <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
                  <p className="font-medium text-destructive">
                    Analysis Failed
                  </p>
                  <p className="text-sm text-destructive/80">{analysisError}</p>
                </div>
              )}

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setCurrentStep(2)}>
                  Back
                </Button>
                <Button
                  onClick={handleGeneratePrompt}
                  className="flex-1"
                  disabled={isAnalyzingProduct}
                >
                  {isAnalyzingProduct
                    ? "Analyzing..."
                    : productImages.length > 0
                      ? "Analyze & Generate Smart Prompt"
                      : "Generate Prompt"}
                </Button>
              </div>

              {productImages.length === 0 && (
                <p className="text-xs text-muted-foreground text-center">
                  💡 Tip: Go back and upload product images to enable AI-powered
                  prompt generation
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 4: Select Model & Generate */}
        {currentStep === 4 && (
          <Card>
            <CardHeader>
              <CardTitle>Step 4: Generate Video</CardTitle>
              <CardDescription>
                Review the prompt, select a model, and generate your UGC video
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Product Analysis Results */}
              {productAnalysis && (
                <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">AI Analysis</Badge>
                    <span className="text-sm font-medium">
                      {productAnalysis.type}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {productAnalysis.description}
                  </p>
                  {productAnalysis.keyFeatures.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {productAnalysis.keyFeatures.map((feature, i) => (
                        <Badge key={i} variant="outline" className="text-xs">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground italic">
                    💡 {productAnalysis.suggestedShowcase}
                  </p>
                </div>
              )}

              {/* Suggested Script */}
              {suggestedScript && (
                <div className="space-y-2">
                  <Label>Suggested Script</Label>
                  <div className="rounded-lg border border-border bg-muted/30 p-3">
                    <p className="text-sm italic">
                      &ldquo;{suggestedScript}&rdquo;
                    </p>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label>Generated Prompt</Label>
                <Textarea
                  value={generatedPrompt}
                  onChange={(e) => setGeneratedPrompt(e.target.value)}
                  rows={15}
                  className="font-mono text-sm"
                />
              </div>

              <Separator />

              <div className="space-y-2">
                <Label>Select Model</Label>
                <Select
                  value={selectedModel}
                  onValueChange={(v) =>
                    setSelectedModel(v as "sora2" | "kling")
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sora2">
                      <div className="flex items-center gap-2">
                        <span>Sora 2</span>
                        <Badge variant="secondary">$0.10/sec</Badge>
                      </div>
                    </SelectItem>
                    <SelectItem value="kling">
                      <div className="flex items-center gap-2">
                        <span>Kling 2.5 Turbo Pro</span>
                        <Badge variant="secondary">$0.07/sec</Badge>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {selectedModel === "sora2"
                    ? "Best for realistic UGC style. Higher cost but better quality."
                    : "30% cheaper, good quality. May need prompt tuning."}
                </p>
              </div>

              {/* Image-to-Video Toggle */}
              {productImages.length > 0 && (
                <div className="space-y-3">
                  <Separator />
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label htmlFor="use-i2v" className="text-base">
                        Use Product Image
                      </Label>
                      <p className="text-xs text-muted-foreground">
                        Use image-to-video mode for accurate product appearance
                      </p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        id="use-i2v"
                        checked={useImageToVideo}
                        onChange={(e) => setUseImageToVideo(e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                    </label>
                  </div>

                  {useImageToVideo && (
                    <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge variant="default" className="bg-green-600">
                          Image-to-Video
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Product image will be used as the starting frame
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-16 h-16 rounded-md overflow-hidden border border-border bg-background">
                          <img
                            src={URL.createObjectURL(productImages[0])}
                            alt="Product"
                            className="w-full h-full object-cover"
                          />
                        </div>
                        <div className="text-xs text-muted-foreground space-y-1">
                          <p>
                            <strong>File:</strong> {productImages[0].name}
                          </p>
                          <p>
                            <strong>Size:</strong>{" "}
                            {(productImages[0].size / 1024).toFixed(1)} KB
                          </p>
                          {uploadedImageUrl && (
                            <p className="text-green-600">
                              ✓ Uploaded to Fal storage
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {!useImageToVideo && (
                    <div className="rounded-lg border border-border bg-muted/30 p-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">Text-to-Video</Badge>
                        <span className="text-xs text-muted-foreground">
                          AI will imagine the product from the text description
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Progress indicator */}
              {isGenerating && (
                <VideoGenerationLoader
                  key={generationCount}
                  model={selectedModel}
                  progress={generationProgress}
                />
              )}

              {/* Error display */}
              {generationError && (
                <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
                  <p className="font-medium text-destructive">
                    Generation Failed
                  </p>
                  <p className="text-sm text-destructive/80">
                    {generationError}
                  </p>
                </div>
              )}

              {/* Video player */}
              {generatedVideoUrl && (
                <div className="space-y-4">
                  <Separator />
                  <div className="space-y-2">
                    <Label>Generated Video</Label>
                    <div className="overflow-hidden rounded-lg border border-border bg-black">
                      <video
                        src={generatedVideoUrl}
                        controls
                        autoPlay
                        loop
                        className="mx-auto max-h-[500px] w-auto"
                      >
                        Your browser does not support the video tag.
                      </video>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleDownloadVideo} className="flex-1">
                      Download Video
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => window.open(generatedVideoUrl, "_blank")}
                    >
                      Open in New Tab
                    </Button>
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setCurrentStep(3)}>
                  Back
                </Button>
                <Button
                  onClick={handleGenerateVideo}
                  disabled={isGenerating}
                  className="flex-1"
                >
                  {isGenerating
                    ? useImageToVideo && productImages.length > 0
                      ? "Generating from image..."
                      : "Generating..."
                    : generatedVideoUrl
                      ? "Regenerate Video"
                      : useImageToVideo && productImages.length > 0
                        ? `Generate from Image (~$${selectedModel === "sora2" ? "0.50" : "0.35"} for 5s)`
                        : `Generate Video (~$${selectedModel === "sora2" ? "0.50" : "0.35"} for 5s)`}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Reset Button */}
        {currentStep > 1 && (
          <div className="mt-4 text-center">
            <Button
              variant="ghost"
              onClick={() => {
                setCurrentStep(1);
                setTiktokUrl("");
                setBlueprintData(null);
                setProductImages([]);
                setProductDescription("");
                setGeneratedPrompt("");
                setGeneratedVideoUrl(null);
                setGenerationError(null);
                setGenerationProgress("");
                setProductAnalysis(null);
                setSuggestedScript("");
                setAnalysisError(null);
                // Reset product context fields
                setShowAdvancedProduct(false);
                setProductType("");
                setProductInteractions("");
                setTactileFeatures("");
                setSoundFeatures("");
                setSizeDescription("");
                setHighlightFeature("");
                setCustomInstructions("");
              }}
            >
              Start Over
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
