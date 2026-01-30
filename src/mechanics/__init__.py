"""
Mechanics Engine - Auto-inject human mechanics into Sora 2 prompts.

This module translates extracted TikTok mechanics (gestures, expressions,
product interactions) into Sora 2-optimized prompt instructions for
realistic human movement and expressions.
"""

from src.mechanics.engine import MechanicsEngine
from src.mechanics.models import (
    MechanicsTimeline,
    SceneMechanics,
    HandMechanics,
    ExpressionMechanics,
    BodyMechanics,
    EyeMechanics,
    ProductMechanics,
    ProductContext,
    VideoConfig,
)

__all__ = [
    "MechanicsEngine",
    "MechanicsTimeline",
    "SceneMechanics",
    "HandMechanics",
    "ExpressionMechanics",
    "BodyMechanics",
    "EyeMechanics",
    "ProductMechanics",
    "ProductContext",
    "VideoConfig",
]
