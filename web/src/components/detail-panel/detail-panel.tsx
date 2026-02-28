"use client";

import { X } from "lucide-react";
import { NODE_DEFINITIONS, INPUT_NODE } from "@/lib/nodes";
import type { VideoModel } from "@/types/pipeline";
import { InputForm } from "../left-sidebar";
import type { NodeState, PipelineStatus } from "@/hooks/use-pipeline";
import { NodeOutputContent } from "./node-output-content";

interface DetailPanelProps {
  selectedNode: string | null;
  nodeStates: Record<string, NodeState>;
  onClose: () => void;
  // Input form props
  videoUrl: string;
  setVideoUrl: (url: string) => void;
  videoModel: VideoModel;
  setVideoModel: (model: VideoModel) => void;
  productImages: string[];
  handleImageUpload: (files: FileList | null) => void;
  removeImage: (index: number) => void;
  identityPack: Record<string, string>;
  handleIdentityImageUpload: (angle: string, file: File) => void;
  removeIdentityImage: (angle: string) => void;
  useIdentityPack: boolean;
  toggleIdentityPack: (enabled: boolean) => void;
  useTailImage: boolean;
  setUseTailImage: (v: boolean) => void;
  falKey: string;
  setFalKey: (key: string) => void;
  pipelineStatus: PipelineStatus;
  startPipeline: () => void;
  resumePipeline: (editedPrompt?: string) => void;
  resetPipeline: () => void;
  error: string | null;
}

export function DetailPanel({
  selectedNode,
  nodeStates,
  onClose,
  videoUrl,
  setVideoUrl,
  videoModel,
  setVideoModel,
  productImages,
  handleImageUpload,
  removeImage,
  identityPack,
  handleIdentityImageUpload,
  removeIdentityImage,
  useIdentityPack,
  toggleIdentityPack,
  useTailImage,
  setUseTailImage,
  falKey,
  setFalKey,
  pipelineStatus,
  startPipeline,
  resumePipeline,
  resetPipeline,
  error,
}: DetailPanelProps) {
  const isOpen = selectedNode !== null;

  const allNodes = [INPUT_NODE, ...NODE_DEFINITIONS];
  const nodeDef = allNodes.find((n) => n.id === selectedNode);
  const nodeState = selectedNode ? nodeStates[selectedNode] : undefined;

  return (
    <div
      style={{
        width: 380,
        flexShrink: 0,
        height: "100vh",
        background: "#141414",
        borderLeft: "1px solid rgba(255,255,255,0.07)",
        display: "flex",
        flexDirection: "column",
        transform: isOpen ? "translateX(0)" : "translateX(100%)",
        transition: "transform 0.28s cubic-bezier(0.4, 0, 0.2, 1)",
        position: "fixed",
        right: 0,
        top: 0,
        zIndex: 10,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          flexShrink: 0,
        }}
      >
        <div>
          <div style={{ color: "#f0f0f0", fontSize: 14, fontWeight: 600 }}>
            {nodeDef?.label ?? "Details"}
          </div>
          {nodeDef && selectedNode !== "input" && nodeState && (
            <div
              style={{
                color:
                  nodeState.status === "running"
                    ? "#93c5fd"
                    : nodeState.status === "done"
                    ? "#86efac"
                    : nodeState.status === "failed"
                    ? "#fca5a5"
                    : "#555",
                fontSize: 11,
                marginTop: 2,
                textTransform: "capitalize",
              }}
            >
              {nodeState.status}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#555",
            cursor: "pointer",
            padding: 4,
            borderRadius: 6,
            display: "flex",
            alignItems: "center",
            transition: "color 0.15s",
          }}
          onMouseEnter={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.color = "#f0f0f0")
          }
          onMouseLeave={(e) =>
            ((e.currentTarget as HTMLButtonElement).style.color = "#555")
          }
        >
          <X size={16} />
        </button>
      </div>

      {/* Body */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "20px",
        }}
      >
        {selectedNode === "input" ? (
          <InputForm
            videoUrl={videoUrl}
            setVideoUrl={setVideoUrl}
            videoModel={videoModel}
            setVideoModel={setVideoModel}
            productImages={productImages}
            handleImageUpload={handleImageUpload}
            removeImage={removeImage}
            identityPack={identityPack}
            handleIdentityImageUpload={handleIdentityImageUpload}
            removeIdentityImage={removeIdentityImage}
            useIdentityPack={useIdentityPack}
            toggleIdentityPack={toggleIdentityPack}
            useTailImage={useTailImage}
            setUseTailImage={setUseTailImage}
            falKey={falKey}
            setFalKey={setFalKey}
            pipelineStatus={pipelineStatus}
            startPipeline={startPipeline}
            resetPipeline={resetPipeline}
            error={error}
          />
        ) : selectedNode ? (
          <NodeOutputContent
            nodeId={selectedNode}
            nodeState={nodeState}
            pipelineStatus={pipelineStatus}
            resumePipeline={resumePipeline}
          />
        ) : null}
      </div>
    </div>
  );
}
