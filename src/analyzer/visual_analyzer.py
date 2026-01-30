"""
Visual analysis of video frames using Claude Vision API.

Analyzes extracted frames to understand visual style, setting, and content.
"""

import base64
import json
from pathlib import Path

import anthropic

from src.models.blueprint import (
    AvatarAppearance,
    TextOverlay,
    VisualStyle,
)


class VisualAnalyzer:
    """Analyzes video frames using Claude Vision API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the visual analyzer.

        Args:
            api_key: Anthropic API key
            model: Claude model to use (must support vision)
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _encode_image(self, image_path: Path) -> tuple[str, str]:
        """
        Encode an image file to base64.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (base64_data, media_type)
        """
        image_path = Path(image_path)

        # Determine media type
        suffix = image_path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/jpeg")

        # Read and encode
        with open(image_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")

        return data, media_type

    def analyze_frames(
        self,
        frames: list[tuple[float, Path]],
        transcript_summary: str = "",
    ) -> VisualStyle:
        """
        Analyze multiple frames to extract visual style information.

        Args:
            frames: List of (timestamp, frame_path) tuples
            transcript_summary: Brief summary of what's being said (for context)

        Returns:
            VisualStyle object with complete visual analysis
        """
        if not frames:
            raise ValueError("No frames provided for analysis")

        # Build the message content with all frames
        content = []

        # Add context
        context_text = """Analyze these frames from a TikTok/Reels video.
These frames are extracted at different timestamps throughout the video.

Please analyze and describe:
1. **Setting/Environment**: Where is this filmed? (bedroom, studio, outdoors, office, etc.)
2. **Lighting**: What type of lighting? (natural daylight, ring light, dramatic, soft, etc.)
3. **Camera Framing**: How is the shot framed? (close-up face, medium shot, full body, etc.)
4. **Person Description**: Describe the person in the video (if present)
5. **Avatar Appearance Details**: Age range, gender, hair, clothing, makeup, accessories
6. **Background**: What's visible in the background?
7. **Camera Movement**: Static, handheld, panning, zooming?
8. **Color Palette**: What are the dominant colors and overall mood?
9. **Text Overlays**: Any on-screen text visible? Describe content, position, and style
10. **Visual Effects**: Any transitions, filters, or effects visible?

"""
        if transcript_summary:
            context_text += (
                f'\nContext - The person is saying: "{transcript_summary}"\n'
            )

        content.append({"type": "text", "text": context_text})

        # Add each frame with its timestamp
        for timestamp, frame_path in frames:
            # Add timestamp label
            content.append(
                {"type": "text", "text": f"\n--- Frame at {timestamp:.1f} seconds ---"}
            )

            # Add the image
            image_data, media_type = self._encode_image(frame_path)
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )

        # Add output format instructions
        content.append(
            {
                "type": "text",
                "text": """

Based on all the frames above, provide a comprehensive analysis in the following JSON format:

```json
{
    "setting": "description of the location/environment",
    "lighting": "description of lighting style",
    "framing": "description of camera framing",
    "avatar_description": "overall description of the person",
    "avatar_appearance": {
        "age_range": "estimated age range (e.g., '22-28')",
        "gender": "perceived gender",
        "ethnicity": "perceived ethnicity if discernible",
        "hair": "hair description",
        "clothing": "clothing description",
        "makeup": "makeup description",
        "accessories": "accessories worn"
    },
    "background": "description of background",
    "camera_movement": "static/handheld/panning/etc",
    "color_palette": "dominant colors and mood",
    "text_overlays": [
        {
            "text": "the text content",
            "timestamp": 0.0,
            "position": "top/center/bottom",
            "style_description": "font style, color, effects"
        }
    ],
    "visual_effects": ["list", "of", "effects", "or", "transitions"]
}
```

Return ONLY the JSON, no additional text.""",
            }
        )

        # Call Claude Vision API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": content}],
        )

        # Parse the response
        response_text = response.content[0].text

        # Try to find JSON in the response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            raise ValueError(f"Could not find JSON in response: {response_text}")

        json_str = response_text[json_start:json_end]
        data = json.loads(json_str)

        # Build VisualStyle object
        text_overlays = []
        for overlay in data.get("text_overlays", []):
            text_overlays.append(
                TextOverlay(
                    text=overlay.get("text", ""),
                    timestamp=overlay.get("timestamp", 0.0),
                    position=overlay.get("position", "center"),
                    style_description=overlay.get("style_description", ""),
                )
            )

        avatar_data = data.get("avatar_appearance", {})
        avatar_appearance = AvatarAppearance(
            age_range=avatar_data.get("age_range", ""),
            gender=avatar_data.get("gender", ""),
            ethnicity=avatar_data.get("ethnicity", ""),
            hair=avatar_data.get("hair", ""),
            clothing=avatar_data.get("clothing", ""),
            makeup=avatar_data.get("makeup", ""),
            accessories=avatar_data.get("accessories", ""),
        )

        return VisualStyle(
            setting=data.get("setting", ""),
            lighting=data.get("lighting", ""),
            framing=data.get("framing", ""),
            avatar_description=data.get("avatar_description", ""),
            avatar_appearance=avatar_appearance,
            background=data.get("background", ""),
            camera_movement=data.get("camera_movement", "static"),
            color_palette=data.get("color_palette", ""),
            text_overlays=text_overlays,
            visual_effects=data.get("visual_effects", []),
        )

    def analyze_single_frame(
        self,
        frame_path: Path,
        timestamp: float = 0.0,
        context: str = "",
    ) -> dict:
        """
        Analyze a single frame for quick insights.

        Args:
            frame_path: Path to the frame image
            timestamp: Timestamp of the frame in the video
            context: Additional context about the video

        Returns:
            Dictionary with analysis results
        """
        image_data, media_type = self._encode_image(frame_path)

        prompt = f"""Analyze this frame from a TikTok video (at {timestamp:.1f}s).

{f"Context: {context}" if context else ""}

Briefly describe:
1. What's happening in the frame
2. The person (if visible)
3. Any text overlays
4. The overall vibe/aesthetic

Be concise but specific."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                    ],
                }
            ],
        )

        return {
            "timestamp": timestamp,
            "analysis": response.content[0].text,
        }
