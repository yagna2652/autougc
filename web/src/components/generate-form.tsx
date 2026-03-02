"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Loader2, Play, X, Plus, Trash2, Video, Upload, Package, Save } from "lucide-react";
import { useGenerate, type GenerateStatus } from "@/hooks/use-generate";
import { usePrompts } from "@/hooks/use-prompts";
import { PromptSidebar } from "@/components/prompt-sidebar";
import { GenerationCard } from "@/components/generation-card";

const ASPECT_OPTIONS = ["9:16", "16:9", "1:1"] as const;
const DURATION_OPTIONS = [3, 5, 8, 10] as const;
const SHOT_DURATION_OPTIONS = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15] as const;

const PRESETS = {
  keychain: {
    label: "Keychain",
    startImage: "/video-generation-frames/start_screen.png",
    endImage: "/video-generation-frames/end_frame.png",
    productImages: [
      "/products/keychain/front.png",
      "/products/keychain/side_45.png",
      "/products/keychain/Horizontal.png",
      "/products/keychain/top.png",
      "/products/keychain/Sideview.png",
    ],
    productVideo: "",
  },
} as const;

export function GenerateForm() {
  const { status, message, videoUrl, elapsed, traceId, promptVersionId, generate, cancel, rateGeneration, annotateGeneration } = useGenerate();
  const { versions, loading: versionsLoading, refresh: refreshVersions, loadVersion, saveVersion, setLabel, removeLabel } = usePrompts();

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
  const [multiShotMode, setMultiShotMode] = useState(false);
  const shotIdRef = useRef(1);
  const [shots, setShots] = useState<{ id: number; prompt: string; duration: number }[]>([
    { id: -2, prompt: "", duration: 5 },
    { id: -1, prompt: "", duration: 5 },
  ]);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [activeVersionId, setActiveVersionId] = useState<string | null>(null);
  const [activeVersionNum, setActiveVersionNum] = useState<number | null>(null);
  const [saveFeedback, setSaveFeedback] = useState<string | null>(null);

  const isRunning = status !== "idle" && status !== "done" && status !== "error";

  // Refresh version list when generation completes
  useEffect(() => {
    if (status === "done" && promptVersionId) {
      refreshVersions();
      setActiveVersionId(promptVersionId);
    }
  }, [status, promptVersionId, refreshVersions]);

  function loadPreset(key: keyof typeof PRESETS) {
    const p = PRESETS[key];
    setStartImageUrl(p.startImage);
    setEndImageUrl(p.endImage);
    setProductImages(p.productImages.map((url, i) => ({ id: nextId.current++, url })));
    setProductVideoUrl(p.productVideo);
    setActivePreset(key);
  }

  async function handleSelectVersion(id: string) {
    const version = await loadVersion(id);
    if (version) {
      setNegativePrompt(version.negative_prompt || "blur, distort, and low quality");
      setActiveVersionId(version.id);
      setActiveVersionNum(version.version);
      if (version.model_config) {
        if (version.model_config.duration) setDuration(version.model_config.duration);
        if (version.model_config.aspect_ratio) setAspectRatio(version.model_config.aspect_ratio);
        if (version.model_config.cfg_scale !== undefined) setCfgScale(version.model_config.cfg_scale);

        // Restore multi-shot state if present
        if (version.model_config.multi_prompt && version.model_config.multi_prompt.length > 0) {
          setMultiShotMode(true);
          setShots(version.model_config.multi_prompt.map((s) => ({
            id: shotIdRef.current++,
            prompt: s.prompt,
            duration: s.duration,
          })));
          setPrompt("");
        } else {
          setMultiShotMode(false);
          setPrompt(version.prompt);
        }
      } else {
        setMultiShotMode(false);
        setPrompt(version.prompt);
      }
    }
  }

  async function handleSavePrompt() {
    const textToSave = multiShotMode
      ? shots.map((s) => s.prompt).join("\n---\n")
      : prompt;
    if (!textToSave.trim()) return;
    const result = await saveVersion(textToSave, negativePrompt);
    if (result) {
      setActiveVersionId(result.id);
      setActiveVersionNum(result.version);
      setSaveFeedback(result.is_new ? `Saved as v${result.version}` : `Already saved (v${result.version})`);
      setTimeout(() => setSaveFeedback(null), 2000);
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const images = productImages.map((p) => p.url).filter((u) => u.trim() !== "");
    const base = {
      start_image_url: startImageUrl,
      product_images: images,
      duration,
      aspect_ratio: aspectRatio,
      cfg_scale: cfgScale,
      ...(endImageUrl.trim() && { end_image_url: endImageUrl.trim() }),
      ...(productVideoUrl.trim() && { product_video_url: productVideoUrl.trim() }),
      ...(negativePrompt.trim() && { negative_prompt: negativePrompt.trim() }),
    };

    if (multiShotMode) {
      generate({
        ...base,
        multi_prompt: shots.map((s) => ({ prompt: s.prompt, duration: s.duration })),
        shot_type: "customize",
      });
    } else {
      generate({ ...base, prompt });
    }
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

  function addShot() {
    setShots((prev) => [...prev, { id: shotIdRef.current++, prompt: "", duration: 5 }]);
  }

  function removeShot(id: number) {
    setShots((prev) => (prev.length <= 2 ? prev : prev.filter((s) => s.id !== id)));
  }

  function updateShot(id: number, field: "prompt" | "duration", val: string | number) {
    setShots((prev) =>
      prev.map((s) => (s.id === id ? { ...s, [field]: val } : s))
    );
  }

  const totalShotDuration = shots.reduce((sum, s) => sum + s.duration, 0);
  const canSubmitMultiShot = multiShotMode && shots.length >= 2 && shots.every((s) => s.prompt.trim());

  return (
    <div className="min-h-screen bg-background flex items-start justify-center p-4 pt-12">
      <div className="w-full max-w-4xl flex gap-6">
        {/* Sidebar */}
        <PromptSidebar
          versions={versions}
          loading={versionsLoading}
          activeVersionId={activeVersionId}
          onSelect={handleSelectVersion}
          onAddLabel={setLabel}
          onRemoveLabel={removeLabel}
        />

        {/* Main content */}
        <div className="flex-1 min-w-0 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">AutoUGC</h1>
          <p className="text-sm text-muted-foreground mt-1">
            O3 Reference-to-Video — paste images, write a prompt, get a video.
          </p>
        </div>

        {/* Preset loader */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">Presets</span>
          {Object.entries(PRESETS).map(([key, preset]) => (
            <button
              key={key}
              type="button"
              onClick={() => loadPreset(key as keyof typeof PRESETS)}
              disabled={isRunning}
              className={`text-xs px-3 py-1.5 rounded-md border flex items-center gap-1.5 transition-colors ${
                activePreset === key
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:text-foreground hover:bg-secondary"
              }`}
            >
              <Package size={12} />
              {preset.label}
            </button>
          ))}
          {activePreset && (
            <span className="text-xs text-muted-foreground">
              Assets loaded — edit prompt below
            </span>
          )}
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

          {/* End Image — hidden in multi-shot (Fal rejects end_image_url with multi_prompt) */}
          {!multiShotMode && (
            <Field label="End Image" hint="Anchors the last frame — leave empty to loop back to start">
              <FileOrUrlInput
                value={endImageUrl}
                onChange={setEndImageUrl}
                accept="image/*"
                placeholder="https://... (optional end frame)"
                disabled={isRunning}
              />
            </Field>
          )}

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

          {/* Prompt mode toggle */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Prompt</span>
            <span className="text-destructive ml-0.5">*</span>
            <div className="ml-auto flex items-center gap-1 text-xs">
              <button
                type="button"
                onClick={() => { setMultiShotMode(false); setActiveVersionId(null); setActiveVersionNum(null); }}
                disabled={isRunning}
                className={`px-2.5 py-1 rounded-l-md border transition-colors ${
                  !multiShotMode
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground border-border hover:text-foreground"
                }`}
              >
                Single shot
              </button>
              <button
                type="button"
                onClick={() => { setMultiShotMode(true); setEndImageUrl(""); setActiveVersionId(null); setActiveVersionNum(null); }}
                disabled={isRunning}
                className={`px-2.5 py-1 rounded-r-md border transition-colors ${
                  multiShotMode
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background text-muted-foreground border-border hover:text-foreground"
                }`}
              >
                Multi-shot
              </button>
            </div>
          </div>

          {!multiShotMode ? (
            /* Single-shot prompt */
            <Field label="" hint="Use @Element1 to reference the product">
              <div className="relative">
                <textarea
                  required
                  rows={4}
                  placeholder="Close-up of a hand holding @Element1 vertically. The index finger presses down on one keycap of @Element1, it clicks down and springs back..."
                  value={prompt}
                  onChange={(e) => {
                    setPrompt(e.target.value);
                    setActiveVersionId(null);
                    setActiveVersionNum(null);
                  }}
                  className="input-field resize-y min-h-[100px]"
                  disabled={isRunning}
                />
                {activeVersionNum && (
                  <span className="absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">
                    v{activeVersionNum}
                  </span>
                )}
              </div>
            </Field>
          ) : (
            /* Multi-shot prompt editor */
            <div className="space-y-3">
              <span className="block text-xs text-muted-foreground">
                Define individual shots with their own prompt and duration. Min 2 shots.
              </span>
              {shots.map((shot, idx) => (
                <div key={shot.id} className="border border-border rounded-lg overflow-hidden">
                  <div className="flex items-center gap-2 px-3 py-2 bg-secondary/30 border-b border-border">
                    <span className="text-xs font-medium">Shot {idx + 1}</span>
                    <div className="ml-auto flex items-center gap-2">
                      <label className="text-xs text-muted-foreground">Duration</label>
                      <select
                        value={shot.duration}
                        onChange={(e) => updateShot(shot.id, "duration", Number(e.target.value))}
                        className="input-field !py-1 !px-2 !text-xs w-16"
                        disabled={isRunning}
                      >
                        {SHOT_DURATION_OPTIONS.map((d) => (
                          <option key={d} value={d}>{d}s</option>
                        ))}
                      </select>
                      {shots.length > 2 && (
                        <button
                          type="button"
                          onClick={() => removeShot(shot.id)}
                          className="p-1 text-muted-foreground hover:text-destructive transition-colors"
                          disabled={isRunning}
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                  <textarea
                    rows={3}
                    maxLength={512}
                    placeholder={`Shot ${idx + 1} prompt — e.g. "Hand holds @Element1 steady, camera zooms in..."`}
                    value={shot.prompt}
                    onChange={(e) => {
                      updateShot(shot.id, "prompt", e.target.value);
                      setActiveVersionId(null);
                      setActiveVersionNum(null);
                    }}
                    className="w-full bg-transparent px-3 py-2.5 text-sm resize-y min-h-[80px] focus:outline-none placeholder:text-muted-foreground/50"
                    disabled={isRunning}
                  />
                  <div className="px-3 pb-1.5 flex justify-end">
                    <span className={`text-[10px] ${shot.prompt.length > 480 ? "text-destructive" : "text-muted-foreground/50"}`}>
                      {shot.prompt.length}/512
                    </span>
                  </div>
                </div>
              ))}
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  onClick={addShot}
                  className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
                  disabled={isRunning}
                >
                  <Plus size={14} /> Add shot
                </button>
                <span className="text-xs text-muted-foreground">
                  {shots.length} shots &middot; {totalShotDuration}s total
                  {activeVersionNum && (
                    <span className="ml-2 px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">
                      v{activeVersionNum}
                    </span>
                  )}
                </span>
              </div>
            </div>
          )}

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

          {/* Config row — Duration hidden in multi-shot (each shot has its own) */}
          <div className={`grid gap-4 ${multiShotMode ? "grid-cols-2" : "grid-cols-3"}`}>
            {!multiShotMode && (
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
            )}

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

          {/* Submit / Cancel / Save */}
          <div className="flex gap-3 items-center">
            <button
              type="submit"
              disabled={isRunning || !startImageUrl || (multiShotMode ? !canSubmitMultiShot : !prompt)}
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
            <button
              type="button"
              onClick={handleSavePrompt}
              disabled={isRunning || (multiShotMode ? !canSubmitMultiShot : !prompt.trim())}
              className="btn-secondary flex items-center gap-2"
            >
              <Save size={16} />
              Save Prompt
            </button>
            {isRunning && (
              <button type="button" onClick={cancel} className="btn-secondary flex items-center gap-2">
                <X size={16} /> Cancel
              </button>
            )}
            {saveFeedback && (
              <span className="text-xs text-green-600">{saveFeedback}</span>
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
            <div className="p-3 border-t flex items-center justify-between">
              <a
                href={videoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-foreground underline transition-colors"
              >
                Open in new tab
              </a>
              <GenerationCard
                traceId={traceId}
                onRate={rateGeneration}
                onAnnotate={annotateGeneration}
              />
            </div>
          </div>
        )}
        </div>{/* end main content */}
      </div>{/* end flex row */}
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
