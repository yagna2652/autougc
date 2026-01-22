"""
AutoUGC CLI - Command-line interface for TikTok/Reel analysis.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Load environment variables
load_dotenv()

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """AutoUGC - TikTok/Reel Analyzer and UGC Ad Generator"""
    pass


@main.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output path for the blueprint JSON",
)
@click.option(
    "--whisper-mode",
    type=click.Choice(["local", "api"]),
    default="local",
    help="Whisper transcription mode",
)
@click.option(
    "--whisper-model",
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
    default="base",
    help="Whisper model size (for local mode)",
)
@click.option(
    "--num-frames",
    type=int,
    default=5,
    help="Number of frames to extract for visual analysis",
)
@click.option(
    "--keep-temp",
    is_flag=True,
    default=False,
    help="Keep temporary audio and frame files",
)
def analyze(
    video_path: str,
    output: str | None,
    whisper_mode: str,
    whisper_model: str,
    num_frames: int,
    keep_temp: bool,
):
    """
    Analyze a TikTok/Reel video and generate a blueprint.

    VIDEO_PATH: Path to the video file to analyze
    """
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        console.print(
            "[bold red]Error:[/bold red] ANTHROPIC_API_KEY environment variable not set."
        )
        console.print("Please set it in your .env file or environment.")
        sys.exit(1)

    # Import here to avoid slow startup
    from src.analyzer.blueprint_generator import BlueprintGenerator

    video_path = Path(video_path)

    # Generate default output path if not provided
    if output is None:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = output_dir / f"{video_path.stem}_{timestamp}_blueprint.json"

    console.print()
    console.print(
        Panel.fit(
            "[bold blue]AutoUGC Video Analyzer[/bold blue]\n"
            f"Video: [green]{video_path.name}[/green]",
            border_style="blue",
        )
    )
    console.print()

    try:
        # Initialize generator
        generator = BlueprintGenerator(
            anthropic_api_key=api_key,
            whisper_mode=whisper_mode,
            whisper_model=whisper_model,
        )

        # Run analysis
        blueprint = generator.generate(
            video_path=video_path,
            output_path=output,
            num_frames=num_frames,
            keep_temp_files=keep_temp,
        )

        # Display results summary
        console.print()
        console.print(
            Panel.fit(
                "[bold green]Analysis Complete![/bold green]",
                border_style="green",
            )
        )

        # Summary table
        table = Table(title="Blueprint Summary", show_header=False, border_style="dim")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Source", video_path.name)
        table.add_row("Duration", f"{blueprint.structure.total_duration:.1f}s")
        table.add_row("Hook Style", blueprint.structure.hook.style.value)
        table.add_row("Body Framework", blueprint.structure.body.framework.value)
        table.add_row("CTA Urgency", blueprint.structure.cta.urgency.value)
        table.add_row(
            "Setting",
            blueprint.visual_style.setting[:50] + "..."
            if len(blueprint.visual_style.setting) > 50
            else blueprint.visual_style.setting,
        )
        table.add_row("Output", str(output))

        console.print(table)

        # Show transcript preview
        console.print()
        console.print("[bold]Transcript Preview:[/bold]")
        transcript_preview = blueprint.transcript.full_text[:200]
        if len(blueprint.transcript.full_text) > 200:
            transcript_preview += "..."
        console.print(f"[dim]{transcript_preview}[/dim]")

        # Show key engagement factors
        if blueprint.engagement_analysis.hook_technique:
            console.print()
            console.print("[bold]Hook Technique:[/bold]")
            console.print(f"[dim]{blueprint.engagement_analysis.hook_technique}[/dim]")

        if blueprint.recreation_notes:
            console.print()
            console.print("[bold]Recreation Notes:[/bold]")
            for i, note in enumerate(blueprint.recreation_notes[:5], 1):
                console.print(f"  [dim]{i}. {note}[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print_exception()
        sys.exit(1)


@main.command()
@click.argument("blueprint_path", type=click.Path(exists=True))
def show(blueprint_path: str):
    """
    Display a previously generated blueprint.

    BLUEPRINT_PATH: Path to the blueprint JSON file
    """
    from src.models.blueprint import VideoBlueprint

    try:
        blueprint = VideoBlueprint.load(blueprint_path)

        console.print()
        console.print(
            Panel.fit(
                f"[bold blue]Video Blueprint[/bold blue]\n"
                f"Source: [green]{blueprint.source_video}[/green]",
                border_style="blue",
            )
        )

        # Structure breakdown
        console.print()
        console.print("[bold]Video Structure:[/bold]")

        structure_table = Table(show_header=True, border_style="dim")
        structure_table.add_column("Section", style="cyan")
        structure_table.add_column("Time", style="yellow")
        structure_table.add_column("Type", style="green")
        structure_table.add_column("Text", style="white", max_width=50)

        structure_table.add_row(
            "Hook",
            f"{blueprint.structure.hook.start:.1f}s - {blueprint.structure.hook.end:.1f}s",
            blueprint.structure.hook.style.value,
            blueprint.structure.hook.text[:50] + "..."
            if len(blueprint.structure.hook.text) > 50
            else blueprint.structure.hook.text,
        )
        structure_table.add_row(
            "Body",
            f"{blueprint.structure.body.start:.1f}s - {blueprint.structure.body.end:.1f}s",
            blueprint.structure.body.framework.value,
            blueprint.structure.body.text[:50] + "..."
            if len(blueprint.structure.body.text) > 50
            else blueprint.structure.body.text,
        )
        structure_table.add_row(
            "CTA",
            f"{blueprint.structure.cta.start:.1f}s - {blueprint.structure.cta.end:.1f}s",
            blueprint.structure.cta.urgency.value,
            blueprint.structure.cta.text[:50] + "..."
            if len(blueprint.structure.cta.text) > 50
            else blueprint.structure.cta.text,
        )

        console.print(structure_table)

        # Visual style
        console.print()
        console.print("[bold]Visual Style:[/bold]")
        console.print(f"  Setting: {blueprint.visual_style.setting}")
        console.print(f"  Lighting: {blueprint.visual_style.lighting}")
        console.print(f"  Framing: {blueprint.visual_style.framing}")
        console.print(f"  Background: {blueprint.visual_style.background}")

        # Audio style
        console.print()
        console.print("[bold]Audio Style:[/bold]")
        console.print(f"  Voice tone: {blueprint.audio_style.voice_tone}")
        console.print(f"  Pacing: {blueprint.audio_style.pacing}")
        console.print(f"  Energy: {blueprint.audio_style.energy_level}")

        # Engagement
        console.print()
        console.print("[bold]Engagement Analysis:[/bold]")
        console.print(
            f"  Hook technique: {blueprint.engagement_analysis.hook_technique}"
        )
        console.print(f"  CTA approach: {blueprint.engagement_analysis.cta_approach}")

        if blueprint.engagement_analysis.emotional_triggers:
            console.print(
                f"  Emotional triggers: {', '.join(blueprint.engagement_analysis.emotional_triggers)}"
            )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command()
def version():
    """Show version information"""
    console.print("[bold]AutoUGC[/bold] v0.1.0")
    console.print("Phase 1: TikTok Analyzer")
    console.print()
    console.print("Components:")
    console.print("  - Audio extraction (ffmpeg)")
    console.print("  - Transcription (Whisper)")
    console.print("  - Visual analysis (Claude Vision)")
    console.print("  - Structure parsing (Claude)")


if __name__ == "__main__":
    main()
