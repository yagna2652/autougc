"use client";

import { usePipeline } from "@/hooks/use-pipeline";
import { PipelineCanvas } from "./pipeline-canvas";
import { DetailPanel } from "./detail-panel";

export function PipelineApp() {
  const pipeline = usePipeline();
  const isPanelOpen = pipeline.selectedNode !== null;

  return (
    <div
      style={{
        background: "#080808",
        color: "#f0f0f0",
        minHeight: "100vh",
        display: "flex",
        overflow: "hidden",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif',
      }}
    >
      {/* Canvas area — shrinks when panel is open */}
      <div
        style={{
          flex: 1,
          overflow: "hidden",
          transition: "padding-right 0.28s cubic-bezier(0.4, 0, 0.2, 1)",
          paddingRight: isPanelOpen ? 380 : 0,
        }}
      >
        <PipelineCanvas
          nodeStates={pipeline.nodeStates}
          selectedNode={pipeline.selectedNode}
          pipelineStatus={pipeline.pipelineStatus}
          onSelectNode={pipeline.setSelectedNode}
        />
      </div>

      {/* Right detail panel */}
      <DetailPanel
        selectedNode={pipeline.selectedNode}
        nodeStates={pipeline.nodeStates}
        onClose={() => pipeline.setSelectedNode(null)}
        videoUrl={pipeline.videoUrl}
        setVideoUrl={pipeline.setVideoUrl}
        videoModel={pipeline.videoModel}
        setVideoModel={pipeline.setVideoModel}
        productImages={pipeline.productImages}
        handleImageUpload={pipeline.handleImageUpload}
        removeImage={pipeline.removeImage}
        identityPack={pipeline.identityPack}
        handleIdentityImageUpload={pipeline.handleIdentityImageUpload}
        removeIdentityImage={pipeline.removeIdentityImage}
        useIdentityPack={pipeline.useIdentityPack}
        toggleIdentityPack={pipeline.toggleIdentityPack}
        useTailImage={pipeline.useTailImage}
        setUseTailImage={pipeline.setUseTailImage}
        falKey={pipeline.falKey}
        setFalKey={pipeline.setFalKey}
        pipelineStatus={pipeline.pipelineStatus}
        startPipeline={pipeline.startPipeline}
        resetPipeline={pipeline.resetPipeline}
        error={pipeline.error}
      />
    </div>
  );
}
