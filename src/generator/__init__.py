"""
Generator module for AI video generation.

Components:
- SoraClient: Interface with OpenAI's Sora API for video generation
- PromptGenerator: Convert blueprints into optimized Sora prompts
- VideoAssembler: Stitch generated scenes together
- AudioGenerator: Generate voiceover and add audio
"""

from src.generator.prompt_generator import PromptGenerator
from src.generator.sora_client import SoraClient
from src.generator.video_assembler import VideoAssembler

__all__ = [
    "SoraClient",
    "PromptGenerator",
    "VideoAssembler",
]
