"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Loader2, Play, X, Plus, Trash2, Video, Upload } from "lucide-react";
import { useGenerate, type GenerateStatus } from "@/hooks/use-generate";

const ASPECT_OPTIONS = ["9:16", "16:9", "1:1"] as const;
const DURATION_OPTIONS = [3, 5, 8, 10] as const;

export function GenerateForm() {
  const { status, message, videoUrl, elapsed, generate, cancel } = useGenerate();

  const [prompt, setPrompt] = useState("");
  const [startImageUrl, setStartImageUrl] = useState("");
  const [endImageUrl, setEndImageUrl] = useState("");
  const nextId = useRef(1);
  const [productImages, setProductImages] = useState<{ id: number; url: string }[]>([
    { id: 0, url: "" },
  ]);
  const [productVideoUrl, setProductVideoUrl] = useState("");
  const [negativePrompt, setNegativePrompt] = useState("blur, distort, and low quality");
  const [duration, setDuration] = useState(5);
  const [aspectRatio, setAspectRatio] = useState<string>("9:16");
  const [cfgScale, setCfgScale] = useState(0.5);

  const isRunning = status !== "idle" && status !== "done" && status !== "error";

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const images = productImages.map((p) => p.url).filter((u) => u.trim() !== "");
    generate({
      prompt,
      start_image_url: startImageUrl,
      product_images: images,
      duration,
      aspect_ratio: aspectRatio,
      cfg_scale: cfgScale,
      ...(endImageUrl.trim() && { end_image_url: endImageUrl.trim() }),
      ...(productVideoUrl.trim() && { product_video_url: productVideoUrl.trim() }),
      ...(negativePrompt.trim() && { negative_prompt: negativePrompt.trim() }),
    });
  }

  function addProductImage() {
    setProductImages((prev) => [...prev, { id: nextId.current++, url: "" }]);
  }

  function removeProductImage(id: number) {
    setProductImages((prev) => prev.filter((p) => p.id !== id));
  }

  function updateProductImage(id: number, val: string) {
    setProductImages((prev) => prev.map((p) => (p.id === id ? { ...p, url: val } : p)));
  }

  return (
    <div className="min-h-screen bg-background flex items-start justify-center p-4 pt-12">
      <div className="w-full max-w-2xl space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">AutoUGC</h1>
          <p className="text-sm text-muted-foreground mt-1">
            O3 Reference-to-Video — paste images, write a prompt, get a video.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Start Image */}
          <Field label="Start Image" required>
            <FileOrUrlInput
              value={startImageUrl}
              onChange={setStartImageUrl}
              accept="image/*"
              placeholder="https://... (photo of product in hand)"
              disabled={isRunning}
            />
          </Field>

          {/* End Image */}
          <Field label="End Image" hint="Anchors the last frame — leave empty to loop back to start">
            <FileOrUrlInput
              value={endImageUrl}
              onChange={setEndImageUrl}
              accept="image/*"
              placeholder="https://... (optional end frame)"
              disabled={isRunning}
            />
          </Field>

          {/* Product Reference Images */}
          <Field label="Product Reference Images" hint="Multi-angle photos for identity element (@Element1)">
            <div className="space-y-2">
              {productImages.map((img, idx) => (
                <div key={img.id} className="flex gap-2 items-start">
                  <div className="flex-1">
                    <FileOrUrlInput
                      value={img.url}
                      onChange={(val) => updateProductImage(img.id, val)}
                      accept="image/*"
                      placeholder={`Product image ${idx + 1} URL`}
                      disabled={isRunning}
                    />
                  </div>
                  {productImages.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeProductImage(img.id)}
                      className="p-2 text-muted-foreground hover:text-destructive transition-colors"
                      disabled={isRunning}
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}
              {productImages.length < 5 && (
                <button
                  type="button"
                  onClick={addProductImage}
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
                  disabled={isRunning}
                >
                  <Plus size={14} /> Add image
                </button>
              )}
            </div>
          </Field>

          {/* Product Motion Video */}
          <Field label="Product Motion Video" hint="Short clip showing how to interact with the product">
            <FileOrUrlInput
              value={productVideoUrl}
              onChange={setProductVideoUrl}
              accept="video/*"
              placeholder="https://... (pressing, clicking, turning)"
              disabled={isRunning}
            />
          </Field>

          {/* Prompt */}
          <Field label="Prompt" required hint="Use @Element1 to reference the product">
            <textarea
              required
              rows={4}
              placeholder="Close-up of a hand holding @Element1 vertically. The index finger presses down on one keycap of @Element1, it clicks down and springs back..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="input-field resize-y min-h-[100px]"
              disabled={isRunning}
            />
          </Field>

          {/* Negative Prompt */}
          <Field label="Negative Prompt" hint="What to avoid in the generated video">
            <textarea
              rows={2}
              placeholder="blur, distort, extra objects..."
              value={negativePrompt}
              onChange={(e) => setNegativePrompt(e.target.value)}
              className="input-field resize-y min-h-[60px]"
              disabled={isRunning}
            />
          </Field>

          {/* Config row */}
          <div className="grid grid-cols-3 gap-4">
            <Field label="Duration">
              <select
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                className="input-field"
                disabled={isRunning}
              >
                {DURATION_OPTIONS.map((d) => (
                  <option key={d} value={d}>{d}s</option>
                ))}
              </select>
            </Field>

            <Field label="Aspect Ratio">
              <select
                value={aspectRatio}
                onChange={(e) => setAspectRatio(e.target.value)}
                className="input-field"
                disabled={isRunning}
              >
                {ASPECT_OPTIONS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </Field>

            <Field label="CFG Scale">
              <input
                type="number"
                min={0}
                max={1}
                step={0.1}
                value={cfgScale}
                onChange={(e) => setCfgScale(Number(e.target.value))}
                className="input-field"
                disabled={isRunning}
              />
            </Field>
          </div>

          {/* Submit / Cancel */}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={isRunning || !prompt || !startImageUrl}
              className="btn-primary flex items-center gap-2"
            >
              {isRunning ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Play size={16} />
                  Generate
                </>
              )}
            </button>
            {isRunning && (
              <button type="button" onClick={cancel} className="btn-secondary flex items-center gap-2">
                <X size={16} /> Cancel
              </button>
            )}
          </div>
        </form>

        {/* Status / Progress */}
        {status !== "idle" && (
          <StatusBar status={status} message={message} />
        )}

        {/* Video Output */}
        {videoUrl && (
          <div className="rounded-lg border bg-secondary/30 overflow-hidden">
            <div className="p-3 border-b flex items-center justify-between">
              <span className="text-sm font-medium flex items-center gap-2">
                <Video size={16} /> Generated Video
              </span>
              {elapsed && <span className="text-xs text-muted-foreground">{elapsed}s</span>}
            </div>
            <video
              src={videoUrl}
              controls
              autoPlay
              loop
              className="w-full"
            />
            <div className="p-3 border-t">
              <a
                href={videoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-foreground underline transition-colors"
              >
                Open in new tab
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="block space-y-1.5">
      <span className="text-sm font-medium">
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
      </span>
      {hint && <span className="block text-xs text-muted-foreground">{hint}</span>}
      {children}
    </div>
  );
}


function FileOrUrlInput({
  value,
  onChange,
  accept,
  placeholder,
  disabled,
}: {
  value: string;
  onChange: (val: string) => void;
  accept: "image/*" | "video/*";
  placeholder?: string;
  disabled?: boolean;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  // Clear fileName if parent resets value externally
  useEffect(() => {
    if (!value) setFileName(null);
  }, [value]);

  function handleFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      onChange(reader.result as string);
      setFileName(file.name);
    };
    reader.readAsDataURL(file);
  }

  function clear() {
    onChange("");
    setFileName(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  if (fileName) {
    return (
      <div className="input-field flex items-center gap-2">
        <span className="flex-1 truncate text-sm">{fileName}</span>
        <button
          type="button"
          onClick={clear}
          disabled={disabled}
          className="p-0.5 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="flex gap-2">
      <input
        type="url"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input-field flex-1"
        disabled={disabled}
      />
      <input
        ref={fileRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        disabled={disabled}
        className="p-2 rounded-md border border-border text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
        title="Upload file"
      >
        <Upload size={16} />
      </button>
    </div>
  );
}


function StatusBar({ status, message }: { status: GenerateStatus; message: string }) {
  const colors: Record<GenerateStatus, string> = {
    idle: "border-border",
    uploading: "border-blue-500/50 bg-blue-500/5",
    elements: "border-blue-500/50 bg-blue-500/5",
    generating: "border-amber-500/50 bg-amber-500/5",
    done: "border-green-500/50 bg-green-500/5",
    error: "border-destructive/50 bg-destructive/5",
  };

  return (
    <div className={`rounded-lg border px-4 py-3 text-sm ${colors[status]}`}>
      <div className="flex items-center gap-2">
        {(status === "uploading" || status === "elements" || status === "generating") && (
          <Loader2 size={14} className="animate-spin" />
        )}
        <span>{message}</span>
      </div>
    </div>
  );
}
