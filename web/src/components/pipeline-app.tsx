"use client";

import { useCallback, useRef } from "react";
import { usePipeline, type PipelineCallbacks, type NodeState } from "@/hooks/use-pipeline";
import { useRunHistory } from "@/hooks/use-run-history";
import { PipelineCanvas } from "./pipeline-canvas";
import { DetailPanel } from "./detail-panel";
import { RunHistoryPanel } from "./run-history";

export function PipelineApp() {
  const history = useRunHistory();
  const historyRef = useRef(history);
  historyRef.current = history;

  const callbacks: PipelineCallbacks = {
    onRunStart: ({ videoUrl, videoModel }) => {
      return historyRef.current.createRun({ videoUrl, videoModel });
    },
    onJobIdAssigned: (runId, jobId) => {
      historyRef.current.updateRun(runId, { jobId });
    },
    onNodeUpdate: (runId, nodeStates: Record<string, NodeState>) => {
      // Extract scene image + video URLs from node outputs for quick access
      const sceneImageUrl =
        (nodeStates.generate_scene_image?.output?.image_url as string) ?? null;
      const generatedVideoUrl =
        (nodeStates.generate_video?.output?.video_url as string) ?? null;

      historyRef.current.updateRun(runId, {
        nodeStates,
        sceneImageUrl,
        generatedVideoUrl,
      });
    },
    onRunComplete: (runId, status, error) => {
      historyRef.current.updateRun(runId, { status, error });
    },
  };

  const pipeline = usePipeline(callbacks);
  const isPanelOpen = pipeline.selectedNode !== null;

  const handleSelectRun = useCallback(
    (id: string) => {
      const entry = historyRef.current.getRun(id);
      if (!entry) return;

      // Only restore terminal runs (completed/failed)
      if (entry.status !== "running") {
        pipeline.restoreRun(entry);
      }
    },
    [pipeline]
  );

  const handleNewRun = useCallback(() => {
    pipeline.resetPipeline();
  }, [pipeline]);

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
      {/* Left history panel */}
      <RunHistoryPanel
        runs={history.runs}
        activeRunId={pipeline.activeRunId}
        onSelectRun={handleSelectRun}
        onDeleteRun={history.deleteRun}
        onClearAll={history.clearAll}
        onNewRun={handleNewRun}
      />

      {/* Canvas area — shrinks when detail panel is open */}
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
