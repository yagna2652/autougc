"""
Pacing Analyzer - Analyzes speech pacing, pauses, and emphasis in videos.

Calculates:
1. Words per minute (WPM) overall and per section
2. Pause detection and analysis
3. Emphasis point identification
4. Speaking vs silence ratio
5. Scene cut frequency
"""

from src.models.blueprint import (
    PacingMetrics,
    SceneBreakdown,
    TranscriptSegment,
    VideoStructure,
)


class PacingAnalyzer:
    """
    Analyzes pacing metrics from transcript and scene data.
    """

    # Standard pause thresholds (in seconds)
    MICRO_PAUSE = 0.3  # Brief pause for breath
    SHORT_PAUSE = 0.5  # Normal pause between phrases
    MEDIUM_PAUSE = 1.0  # Pause for emphasis
    LONG_PAUSE = 2.0  # Dramatic pause or scene break

    def __init__(self):
        """Initialize the pacing analyzer."""
        pass

    def analyze(
        self,
        transcript_segments: list[TranscriptSegment],
        structure: VideoStructure,
        scene_breakdown: SceneBreakdown | None = None,
        total_duration: float = 0.0,
    ) -> PacingMetrics:
        """
        Analyze pacing from transcript and structure.

        Args:
            transcript_segments: List of transcript segments with timing
            structure: Video structure (hook/body/cta)
            scene_breakdown: Optional scene breakdown for cut analysis
            total_duration: Total video duration

        Returns:
            PacingMetrics with detailed pacing analysis
        """
        # Calculate basic word metrics
        total_words = 0
        for segment in transcript_segments:
            word_count = len(segment.text.split())
            segment.word_count = word_count
            total_words += word_count

        # Calculate speaking time and WPM
        speaking_time = sum(seg.end - seg.start for seg in transcript_segments)

        # Use total_duration if not provided
        if total_duration == 0.0:
            total_duration = structure.total_duration

        silence_time = total_duration - speaking_time
        if silence_time < 0:
            silence_time = 0

        speaking_ratio = speaking_time / total_duration if total_duration > 0 else 0

        # Words per minute calculation
        wpm = (total_words / speaking_time * 60) if speaking_time > 0 else 0

        # Detect pauses between segments
        pauses = self._detect_pauses(transcript_segments)
        avg_pause = sum(p["duration"] for p in pauses) / len(pauses) if pauses else 0
        longest_pause = max((p["duration"] for p in pauses), default=0)

        # Calculate WPM per section
        hook_wpm = self._calculate_section_wpm(
            transcript_segments, structure.hook.start, structure.hook.end
        )
        body_wpm = self._calculate_section_wpm(
            transcript_segments, structure.body.start, structure.body.end
        )
        cta_wpm = self._calculate_section_wpm(
            transcript_segments, structure.cta.start, structure.cta.end
        )

        # Identify emphasis points
        emphasis_points = self._identify_emphasis_points(transcript_segments, pauses)

        # Update segments with emphasis words
        for segment in transcript_segments:
            segment.emphasis_words = self._find_emphasis_words_in_segment(
                segment, emphasis_points
            )

        # Calculate scene cut metrics
        cuts_per_minute = 0.0
        fastest_scene = 0.0
        slowest_scene = 0.0

        if scene_breakdown and scene_breakdown.scenes:
            scene_durations = [s.duration for s in scene_breakdown.scenes]
            cuts_per_minute = (
                (len(scene_breakdown.scenes) - 1) / total_duration * 60
                if total_duration > 0
                else 0
            )
            fastest_scene = min(scene_durations)
            slowest_scene = max(scene_durations)

        return PacingMetrics(
            total_word_count=total_words,
            words_per_minute=round(wpm, 1),
            speaking_time=round(speaking_time, 2),
            silence_time=round(silence_time, 2),
            speaking_ratio=round(speaking_ratio, 3),
            pauses=pauses,
            avg_pause_duration=round(avg_pause, 2),
            longest_pause=round(longest_pause, 2),
            hook_wpm=round(hook_wpm, 1),
            body_wpm=round(body_wpm, 1),
            cta_wpm=round(cta_wpm, 1),
            emphasis_points=emphasis_points,
            cuts_per_minute=round(cuts_per_minute, 1),
            fastest_scene=round(fastest_scene, 2),
            slowest_scene=round(slowest_scene, 2),
        )

    def _detect_pauses(self, segments: list[TranscriptSegment]) -> list[dict]:
        """
        Detect pauses between transcript segments.

        Returns list of pause info dicts with:
        - start: pause start time
        - end: pause end time
        - duration: pause length
        - type: micro, short, medium, long, dramatic
        - after_text: what was said before the pause
        """
        pauses = []

        for i in range(len(segments) - 1):
            current_end = segments[i].end
            next_start = segments[i + 1].start
            gap = next_start - current_end

            if gap >= self.MICRO_PAUSE:
                pause_type = self._classify_pause(gap)
                pauses.append(
                    {
                        "start": round(current_end, 2),
                        "end": round(next_start, 2),
                        "duration": round(gap, 2),
                        "type": pause_type,
                        "after_text": segments[i].text.strip().split()[-3:]
                        if segments[i].text
                        else [],
                    }
                )

        return pauses

    def _classify_pause(self, duration: float) -> str:
        """Classify a pause by its duration."""
        if duration >= self.LONG_PAUSE:
            return "dramatic"
        elif duration >= self.MEDIUM_PAUSE:
            return "long"
        elif duration >= self.SHORT_PAUSE:
            return "medium"
        elif duration >= self.MICRO_PAUSE:
            return "short"
        else:
            return "micro"

    def _calculate_section_wpm(
        self,
        segments: list[TranscriptSegment],
        section_start: float,
        section_end: float,
    ) -> float:
        """
        Calculate WPM for a specific section of the video.
        """
        section_words = 0
        section_time = 0.0

        for segment in segments:
            # Check if segment overlaps with section
            if segment.start < section_end and segment.end > section_start:
                # Calculate overlap
                overlap_start = max(segment.start, section_start)
                overlap_end = min(segment.end, section_end)
                overlap_duration = overlap_end - overlap_start

                # Estimate words in overlap based on proportion
                segment_duration = segment.end - segment.start
                if segment_duration > 0:
                    word_count = len(segment.text.split())
                    proportion = overlap_duration / segment_duration
                    section_words += int(word_count * proportion)
                    section_time += overlap_duration

        if section_time > 0:
            return section_words / section_time * 60
        return 0.0

    def _identify_emphasis_points(
        self,
        segments: list[TranscriptSegment],
        pauses: list[dict],
    ) -> list[dict]:
        """
        Identify words/phrases that should be emphasized.

        Emphasis indicators:
        1. Words/phrases before significant pauses
        2. First words after long pauses
        3. Repetition of words
        4. Common emphasis patterns (superlatives, power words)
        """
        emphasis_points = []

        # Power words that often receive emphasis
        power_words = {
            "amazing",
            "incredible",
            "best",
            "worst",
            "never",
            "always",
            "only",
            "first",
            "last",
            "free",
            "new",
            "now",
            "today",
            "love",
            "hate",
            "need",
            "must",
            "secret",
            "finally",
            "actually",
            "literally",
            "seriously",
            "honestly",
            "obsessed",
            "favorite",
            "game-changer",
            "life-changing",
        }

        # Track word frequency for repetition detection
        all_words = []
        for segment in segments:
            words = segment.text.lower().split()
            all_words.extend(words)

        word_freq = {}
        for word in all_words:
            clean_word = "".join(c for c in word if c.isalnum())
            if len(clean_word) > 3:  # Ignore short words
                word_freq[clean_word] = word_freq.get(clean_word, 0) + 1

        # Find repeated words (said 2+ times)
        repeated_words = {w for w, count in word_freq.items() if count >= 2}

        # Analyze each segment for emphasis
        for segment in segments:
            words = segment.text.split()
            segment_duration = segment.end - segment.start
            words_per_second = (
                len(words) / segment_duration if segment_duration > 0 else 0
            )

            for i, word in enumerate(words):
                clean_word = "".join(c for c in word.lower() if c.isalnum())

                # Check if this is a power word
                if clean_word in power_words:
                    # Estimate timestamp within segment
                    word_position = i / len(words) if words else 0
                    timestamp = segment.start + (segment_duration * word_position)

                    emphasis_points.append(
                        {
                            "timestamp": round(timestamp, 2),
                            "word": word,
                            "reason": "power_word",
                            "intensity": "medium",
                        }
                    )

                # Check if this is a repeated word (first occurrence only)
                elif clean_word in repeated_words:
                    word_position = i / len(words) if words else 0
                    timestamp = segment.start + (segment_duration * word_position)

                    # Only add first occurrence
                    already_added = any(
                        p["word"].lower().strip(",.!?") == clean_word
                        for p in emphasis_points
                    )
                    if not already_added:
                        emphasis_points.append(
                            {
                                "timestamp": round(timestamp, 2),
                                "word": word,
                                "reason": "repetition",
                                "intensity": "light",
                            }
                        )

        # Add emphasis before significant pauses
        for pause in pauses:
            if pause["type"] in ["medium", "long", "dramatic"]:
                if pause["after_text"]:
                    emphasis_points.append(
                        {
                            "timestamp": round(pause["start"] - 0.5, 2),
                            "word": " ".join(pause["after_text"]),
                            "reason": "pre_pause",
                            "intensity": "strong"
                            if pause["type"] == "dramatic"
                            else "medium",
                        }
                    )

        # Sort by timestamp
        emphasis_points.sort(key=lambda x: x["timestamp"])

        return emphasis_points

    def _find_emphasis_words_in_segment(
        self,
        segment: TranscriptSegment,
        emphasis_points: list[dict],
    ) -> list[str]:
        """
        Find which emphasis words fall within a segment.
        """
        emphasis_words = []

        for point in emphasis_points:
            if segment.start <= point["timestamp"] <= segment.end:
                emphasis_words.append(point["word"])

        return emphasis_words


def calculate_ideal_pacing(
    target_duration: float,
    word_count: int,
    scene_count: int,
    energy_level: str = "medium",
) -> dict:
    """
    Calculate ideal pacing parameters for recreating a video.

    Args:
        target_duration: Desired video length in seconds
        word_count: Number of words in script
        scene_count: Number of planned scenes
        energy_level: low, medium, or high

    Returns:
        Dictionary with recommended pacing parameters
    """
    # Base WPM ranges by energy
    wpm_ranges = {
        "low": (100, 130),
        "medium": (130, 160),
        "high": (160, 200),
    }

    min_wpm, max_wpm = wpm_ranges.get(energy_level, (130, 160))

    # Calculate based on word count and duration
    speaking_time = target_duration * 0.75  # Assume 75% speaking
    actual_wpm = word_count / speaking_time * 60 if speaking_time > 0 else 140

    # Adjust if outside range
    if actual_wpm < min_wpm:
        recommended_wpm = min_wpm
        suggested_words = int(speaking_time / 60 * min_wpm)
    elif actual_wpm > max_wpm:
        recommended_wpm = max_wpm
        suggested_words = int(speaking_time / 60 * max_wpm)
    else:
        recommended_wpm = actual_wpm
        suggested_words = word_count

    # Scene timing
    avg_scene_duration = (
        target_duration / scene_count if scene_count > 0 else target_duration
    )

    return {
        "recommended_wpm": round(recommended_wpm, 0),
        "suggested_word_count": suggested_words,
        "speaking_time_seconds": round(speaking_time, 1),
        "pause_time_seconds": round(target_duration - speaking_time, 1),
        "avg_scene_duration": round(avg_scene_duration, 1),
        "suggested_pause_count": max(1, scene_count - 1),
        "cuts_per_minute": round(scene_count / target_duration * 60, 1)
        if target_duration > 0
        else 0,
    }
