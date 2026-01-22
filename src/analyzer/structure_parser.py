"""
Structure parser for identifying Hook/Body/CTA sections in video transcripts.

Uses Claude API to analyze transcript and identify video structure.
"""

import json

import anthropic

from src.models.blueprint import (
    AudioStyle,
    BodyFramework,
    BodySection,
    CTASection,
    CTAUrgency,
    EngagementAnalysis,
    HookSection,
    HookStyle,
    Transcript,
    VideoStructure,
)


class StructureParser:
    """Parses video transcripts to identify Hook/Body/CTA structure."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        """
        Initialize the structure parser.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def parse_structure(
        self,
        transcript: Transcript,
        duration: float,
        visual_context: str = "",
    ) -> tuple[VideoStructure, AudioStyle, EngagementAnalysis]:
        """
        Parse transcript to identify video structure and analyze engagement.

        Args:
            transcript: Transcript object with full text and segments
            duration: Total video duration in seconds
            visual_context: Optional visual context from frame analysis

        Returns:
            Tuple of (VideoStructure, AudioStyle, EngagementAnalysis)
        """
        # Build the analysis prompt
        prompt = self._build_analysis_prompt(transcript, duration, visual_context)

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the response
        response_text = response.content[0].text

        # Extract JSON from response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            raise ValueError(f"Could not find JSON in response: {response_text}")

        json_str = response_text[json_start:json_end]
        data = json.loads(json_str)

        # Build objects from parsed data
        structure = self._build_video_structure(data, duration)
        audio_style = self._build_audio_style(data)
        engagement = self._build_engagement_analysis(data)

        return structure, audio_style, engagement

    def _build_analysis_prompt(
        self,
        transcript: Transcript,
        duration: float,
        visual_context: str,
    ) -> str:
        """Build the prompt for Claude analysis."""
        # Format transcript segments for analysis
        segments_text = ""
        for seg in transcript.segments:
            segments_text += f"[{seg.start:.1f}s - {seg.end:.1f}s]: {seg.text}\n"

        prompt = f"""Analyze this TikTok/Reels video transcript and identify its structure.

## Video Information
- Duration: {duration:.1f} seconds
- Language: {transcript.language}

## Full Transcript
{transcript.full_text}

## Transcript with Timestamps
{segments_text}

{f"## Visual Context{chr(10)}{visual_context}" if visual_context else ""}

## Your Task
Analyze this video and identify:

1. **HOOK** (typically first 1-5 seconds): The attention-grabbing opening
   - Identify which segment(s) form the hook
   - Classify the hook style

2. **BODY** (middle section): The main content
   - Identify which segment(s) form the body
   - Classify the content framework
   - Extract key points made

3. **CTA** (typically last 2-5 seconds): The call-to-action
   - Identify which segment(s) form the CTA
   - Classify the urgency level

4. **AUDIO STYLE**: How the person speaks
   - Voice tone
   - Pacing
   - Energy level
   - Background music (if mentioned or implied)

5. **ENGAGEMENT ANALYSIS**: What makes this video work
   - Hook technique
   - Retention tactics
   - Emotional triggers
   - Target audience signals
   - Virality factors

## Hook Styles
- pov_trend: "POV: you..." format
- revelation: "I was today years old..." or revealing hidden info
- question: Starts with a direct question
- controversial: Bold/controversial statement
- story_start: "So this happened..." narrative opening
- curiosity_gap: Creates curiosity without revealing
- pattern_interrupt: Unexpected/attention-grabbing
- relatable: Instantly relatable situation
- shock: Shocking statement or visual
- other: Doesn't fit standard patterns

## Body Frameworks
- testimonial: Personal experience/review
- education: Teaching/explaining something
- problem_agitation: Highlighting pain points
- demonstration: Showing how something works
- social_proof: Reviews, numbers, endorsements
- storytelling: Narrative format
- comparison: Before/after or vs competitors
- tutorial: Step-by-step instructions
- behind_the_scenes: BTS content
- other: Doesn't fit standard patterns

## CTA Urgency Levels
- soft: Gentle suggestion ("check it out")
- medium: Clear ask with reason
- urgent: Time-sensitive language
- fomo: Fear of missing out
- discount: Price/deal focused
- curiosity: Teasing more content
- direct: Straightforward command

## Output Format
Respond with ONLY this JSON structure:

```json
{{
    "hook": {{
        "start": 0.0,
        "end": 3.0,
        "text": "the hook text",
        "style": "hook_style_enum",
        "style_reasoning": "why this style was identified"
    }},
    "body": {{
        "start": 3.0,
        "end": 25.0,
        "text": "the body text",
        "framework": "framework_enum",
        "framework_reasoning": "why this framework was identified",
        "key_points": ["point 1", "point 2", "point 3"]
    }},
    "cta": {{
        "start": 25.0,
        "end": 28.0,
        "text": "the cta text",
        "urgency": "urgency_enum",
        "action_requested": "what action is being requested"
    }},
    "audio_style": {{
        "voice_tone": "description of voice tone",
        "pacing": "slow/medium/fast/varied",
        "energy_level": "low/medium/high",
        "has_background_music": true,
        "music_description": "description if music present",
        "has_sound_effects": false,
        "sound_effects": []
    }},
    "engagement_analysis": {{
        "hook_technique": "what technique grabs attention",
        "retention_tactics": ["tactic 1", "tactic 2"],
        "cta_approach": "how the CTA is delivered",
        "emotional_triggers": ["trigger 1", "trigger 2"],
        "target_audience_signals": ["signal 1", "signal 2"],
        "virality_factors": ["factor 1", "factor 2"]
    }},
    "recreation_notes": [
        "note 1 for recreating this style",
        "note 2 for recreating this style"
    ]
}}
```

Return ONLY the JSON, no additional text."""

        return prompt

    def _build_video_structure(self, data: dict, duration: float) -> VideoStructure:
        """Build VideoStructure object from parsed data."""
        hook_data = data.get("hook", {})
        body_data = data.get("body", {})
        cta_data = data.get("cta", {})

        # Parse hook style
        hook_style_str = hook_data.get("style", "other").lower().replace("-", "_")
        try:
            hook_style = HookStyle(hook_style_str)
        except ValueError:
            hook_style = HookStyle.OTHER

        # Parse body framework
        framework_str = body_data.get("framework", "other").lower().replace("-", "_")
        try:
            body_framework = BodyFramework(framework_str)
        except ValueError:
            body_framework = BodyFramework.OTHER

        # Parse CTA urgency
        urgency_str = cta_data.get("urgency", "soft").lower().replace("-", "_")
        try:
            cta_urgency = CTAUrgency(urgency_str)
        except ValueError:
            cta_urgency = CTAUrgency.SOFT

        hook = HookSection(
            start=float(hook_data.get("start", 0)),
            end=float(hook_data.get("end", 3)),
            text=hook_data.get("text", ""),
            style=hook_style,
            style_reasoning=hook_data.get("style_reasoning", ""),
        )

        body = BodySection(
            start=float(body_data.get("start", 3)),
            end=float(body_data.get("end", duration - 3)),
            text=body_data.get("text", ""),
            framework=body_framework,
            framework_reasoning=body_data.get("framework_reasoning", ""),
            key_points=body_data.get("key_points", []),
        )

        cta = CTASection(
            start=float(cta_data.get("start", duration - 3)),
            end=float(cta_data.get("end", duration)),
            text=cta_data.get("text", ""),
            urgency=cta_urgency,
            action_requested=cta_data.get("action_requested", ""),
        )

        return VideoStructure(
            hook=hook,
            body=body,
            cta=cta,
            total_duration=duration,
        )

    def _build_audio_style(self, data: dict) -> AudioStyle:
        """Build AudioStyle object from parsed data."""
        audio_data = data.get("audio_style", {})

        return AudioStyle(
            voice_tone=audio_data.get("voice_tone", "conversational"),
            pacing=audio_data.get("pacing", "medium"),
            energy_level=audio_data.get("energy_level", "medium"),
            has_background_music=audio_data.get("has_background_music", False),
            music_description=audio_data.get("music_description"),
            has_sound_effects=audio_data.get("has_sound_effects", False),
            sound_effects=audio_data.get("sound_effects", []),
        )

    def _build_engagement_analysis(self, data: dict) -> EngagementAnalysis:
        """Build EngagementAnalysis object from parsed data."""
        engagement_data = data.get("engagement_analysis", {})

        return EngagementAnalysis(
            hook_technique=engagement_data.get("hook_technique", ""),
            retention_tactics=engagement_data.get("retention_tactics", []),
            cta_approach=engagement_data.get("cta_approach", ""),
            emotional_triggers=engagement_data.get("emotional_triggers", []),
            target_audience_signals=engagement_data.get("target_audience_signals", []),
            virality_factors=engagement_data.get("virality_factors", []),
        )

    def get_recreation_notes(self, data: dict) -> list[str]:
        """Extract recreation notes from parsed data."""
        return data.get("recreation_notes", [])
