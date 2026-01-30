"""
Job manager for handling long-running video analysis tasks.

Since video analysis can take 2-5 minutes, we need to run jobs in the background
and allow clients to poll for status updates.
"""

import asyncio
import logging
from threading import Lock
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer.blueprint_generator import BlueprintGenerator


class JobStatus(str, Enum):
    """Job status enumeration."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Represents a video analysis job."""
    job_id: str
    status: JobStatus
    progress: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class JobManager:
    """Manages background video analysis jobs with thread-safe operations."""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self._lock = Lock()
        self.generator = BlueprintGenerator(whisper_mode="local")

    async def create_job(self, job_id: str) -> Job:
        """Create and queue a new job."""
        job = Job(
            job_id=job_id,
            status=JobStatus.QUEUED,
            progress={
                "current_step": "Queued",
                "step_number": 0,
                "total_steps": 11,
            },
        )
        with self._lock:
            self.jobs[job_id] = job
        return job

    def _progress_callback(self, job_id: str, step_name: str, step_number: int, total_steps: int):
        """Update job progress."""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].progress = {
                    "current_step": step_name,
                    "step_number": step_number,
                    "total_steps": total_steps,
                }
                self.jobs[job_id].updated_at = datetime.now()

    async def process_job(self, job_id: str, video_path: str, options: Dict[str, Any]):
        """
        Process video analysis in background.

        Args:
            job_id: Unique job identifier
            video_path: Path to downloaded video file
            options: Analysis options (enhanced, whisper_mode, num_frames, scene_frames)
        """
        try:
            # Update status to processing
            with self._lock:
                if job_id not in self.jobs:
                    return
                self.jobs[job_id].status = JobStatus.PROCESSING
                self.jobs[job_id].updated_at = datetime.now()

            # Run analysis with progress callback
            def progress_cb(step_name: str, step_num: int, total: int):
                self._progress_callback(job_id, step_name, step_num, total)

            # Run the generator synchronously (it's CPU-bound)
            loop = asyncio.get_event_loop()
            blueprint = await loop.run_in_executor(
                None,
                lambda: self.generator.generate(
                    video_path=video_path,
                    output_path=None,  # Don't save to file
                    num_frames=options.get("num_frames", 5),
                    num_frames_for_scenes=options.get("scene_frames", 20),
                    keep_temp_files=False,
                    progress_callback=progress_cb,
                )
            )

            # Convert blueprint to dict using only valid model attributes
            # HookSection, BodySection, CTASection have: start, end, text, style/framework/urgency
            # Duration must be calculated from end - start

            result = {
                "transcript": {
                    "full_text": blueprint.transcript.full_text,
                    "language": blueprint.transcript.language,
                    "segment_count": len(blueprint.transcript.segments),
                },
                "structure": {
                    "hook": {
                        "style": blueprint.structure.hook.style.value if hasattr(blueprint.structure.hook.style, 'value') else str(blueprint.structure.hook.style),
                        "text": blueprint.structure.hook.text,
                        "start": blueprint.structure.hook.start,
                        "end": blueprint.structure.hook.end,
                    },
                    "body": {
                        "framework": blueprint.structure.body.framework.value if hasattr(blueprint.structure.body.framework, 'value') else str(blueprint.structure.body.framework),
                        "text": blueprint.structure.body.text,
                        "start": blueprint.structure.body.start,
                        "end": blueprint.structure.body.end,
                    },
                    "cta": {
                        "urgency": blueprint.structure.cta.urgency.value if hasattr(blueprint.structure.cta.urgency, 'value') else str(blueprint.structure.cta.urgency),
                        "text": blueprint.structure.cta.text,
                        "start": blueprint.structure.cta.start,
                        "end": blueprint.structure.cta.end,
                    },
                },
                "visual_style": {
                    "setting": blueprint.visual_style.setting,
                    "lighting": blueprint.visual_style.lighting,
                    "camera_movement": blueprint.visual_style.camera_movement,
                    "framing": blueprint.visual_style.framing,
                },
                "audio_style": {
                    "energy": blueprint.audio_style.energy_level,
                    "tone": blueprint.audio_style.voice_tone,
                    "pacing": blueprint.audio_style.pacing,
                    "music_present": blueprint.audio_style.has_background_music,
                },
                "total_duration": blueprint.structure.total_duration,
            }

            # Update job with results
            with self._lock:
                self.jobs[job_id].status = JobStatus.COMPLETED
                self.jobs[job_id].result = result
                self.jobs[job_id].progress = {
                    "current_step": "Complete",
                    "step_number": 11,
                    "total_steps": 11,
                }
                self.jobs[job_id].updated_at = datetime.now()

        except Exception as e:
            # Update job with error
            logger.exception("Job %s failed", job_id)
            with self._lock:
                if job_id in self.jobs:
                    self.jobs[job_id].status = JobStatus.FAILED
                    self.jobs[job_id].error = str(e)
                    self.jobs[job_id].updated_at = datetime.now()

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job status and result."""
        with self._lock:
            return self.jobs.get(job_id)

    def delete_job(self, job_id: str) -> bool:
        """Delete a job from memory."""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                return True
            return False


# Global job manager instance
job_manager = JobManager()
