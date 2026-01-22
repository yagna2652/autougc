"""
Analyzer module for TikTok/Reel video analysis.

Components:
- AudioExtractor: Extract audio from video files using ffmpeg
- Transcriber: Transcribe audio to text with timestamps using Whisper
- FrameExtractor: Extract key frames from video for visual analysis
- VisualAnalyzer: Analyze visual style using Claude Vision
- StructureParser: Parse transcript into Hook/Body/CTA structure
- BlueprintGenerator: Orchestrate all components to generate a complete blueprint

Enhanced Analysis (v2.0):
- SceneSegmenter: Detect and analyze individual scenes with actions/expressions
- PacingAnalyzer: Calculate WPM, pauses, and emphasis points
- ProductTracker: Track product appearances and demo moments
"""

from src.analyzer.audio_extractor import AudioExtractor
from src.analyzer.blueprint_generator import BlueprintGenerator, analyze_video
from src.analyzer.frame_extractor import FrameExtractor
from src.analyzer.pacing_analyzer import PacingAnalyzer, calculate_ideal_pacing
from src.analyzer.product_tracker import (
    ProductTracker,
    calculate_product_metrics,
    create_product_timeline,
)
from src.analyzer.scene_segmenter import SceneSegmenter
from src.analyzer.structure_parser import StructureParser
from src.analyzer.transcriber import Transcriber
from src.analyzer.visual_analyzer import VisualAnalyzer

__all__ = [
    # Core analyzers
    "AudioExtractor",
    "Transcriber",
    "FrameExtractor",
    "VisualAnalyzer",
    "StructureParser",
    "BlueprintGenerator",
    # Enhanced analyzers (v2.0)
    "SceneSegmenter",
    "PacingAnalyzer",
    "ProductTracker",
    # Convenience functions
    "analyze_video",
    "calculate_ideal_pacing",
    "create_product_timeline",
    "calculate_product_metrics",
]
