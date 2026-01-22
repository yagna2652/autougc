"""
AutoUGC CLI - Command-line interface for TikTok/Reel analysis.

Enhanced with:
- Scene-by-scene breakdown display
- Pacing metrics display
- Product tracking display
- Recreation script output
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Load environment variables
load_dotenv()

console = Console()


@click.group()
@click.version_option(version="0.2.0")
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
    help="Number of frames for basic visual analysis",
)
@click.option(
    "--scene-frames",
    type=int,
    default=20,
    help="Number of frames for scene segmentation (more = better detection)",
)
@click.option(
    "--enhanced/--basic",
    default=True,
    help="Enable enhanced analysis (scenes, pacing, products)",
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
    scene_frames: int,
    enhanced: bool,
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
    mode_str = "[cyan]Enhanced[/cyan]" if enhanced else "[yellow]Basic[/yellow]"
    console.print(
        Panel.fit(
            f"[bold blue]AutoUGC Video Analyzer[/bold blue] ({mode_str})\n"
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
            enable_enhanced_analysis=enhanced,
        )

        # Run analysis
        blueprint = generator.generate(
            video_path=video_path,
            output_path=output,
            num_frames=num_frames,
            num_frames_for_scenes=scene_frames,
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

        # Add enhanced metrics if available
        if blueprint.scene_breakdown:
            table.add_row("Scenes", str(blueprint.scene_breakdown.total_scenes))
            table.add_row(
                "Location Changes", str(blueprint.scene_breakdown.location_changes)
            )

        if blueprint.pacing_metrics:
            table.add_row("WPM", f"{blueprint.pacing_metrics.words_per_minute:.0f}")
            table.add_row(
                "Speaking Ratio", f"{blueprint.pacing_metrics.speaking_ratio:.0%}"
            )

        if blueprint.product_tracking and blueprint.product_tracking.primary_product:
            table.add_row(
                "Primary Product", blueprint.product_tracking.primary_product.name
            )
            table.add_row(
                "Product Screen Time",
                f"{blueprint.product_tracking.total_product_screen_time:.1f}s",
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

        # Show scene breakdown summary if available
        if blueprint.scene_breakdown and blueprint.scene_breakdown.scenes:
            console.print()
            console.print("[bold]Scene Breakdown:[/bold]")
            for scene in blueprint.scene_breakdown.scenes[:5]:  # Show first 5 scenes
                scene_info = (
                    f"  [{scene.start:.1f}s-{scene.end:.1f}s] "
                    f"[cyan]{scene.scene_type.value}[/cyan] | "
                    f"[yellow]{scene.shot_type.value}[/yellow]"
                )
                if scene.location:
                    scene_info += f" | {scene.location[:30]}"
                console.print(scene_info)

            if len(blueprint.scene_breakdown.scenes) > 5:
                console.print(
                    f"  [dim]... and {len(blueprint.scene_breakdown.scenes) - 5} more scenes[/dim]"
                )

        # Show product tracking if available
        if blueprint.product_tracking and blueprint.product_tracking.products:
            console.print()
            console.print("[bold]Products Detected:[/bold]")
            for product in blueprint.product_tracking.products[:3]:
                demo_str = (
                    f" ({len(product.demo_moments)} demos)"
                    if product.demo_moments
                    else ""
                )
                console.print(
                    f"  - {product.name}: {product.total_screen_time:.1f}s screen time{demo_str}"
                )

        # Show recreation notes
        if blueprint.recreation_notes:
            console.print()
            console.print("[bold]Recreation Notes:[/bold]")
            for i, note in enumerate(blueprint.recreation_notes[:7], 1):
                console.print(f"  [dim]{i}. {note}[/dim]")

        # Show recreation script preview if available
        if blueprint.recreation_script:
            console.print()
            console.print("[bold]Recreation Script Preview:[/bold]")
            console.print("[dim]" + "-" * 50 + "[/dim]")
            for instruction in blueprint.recreation_script[:3]:
                console.print(f"[dim]{instruction}[/dim]")
                console.print("[dim]" + "-" * 50 + "[/dim]")

            if len(blueprint.recreation_script) > 3:
                console.print(
                    f"[dim]... and {len(blueprint.recreation_script) - 3} more scene instructions[/dim]"
                )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print_exception()
        sys.exit(1)


@main.command()
@click.argument("blueprint_path", type=click.Path(exists=True))
@click.option(
    "--scenes",
    is_flag=True,
    default=False,
    help="Show detailed scene breakdown",
)
@click.option(
    "--script",
    is_flag=True,
    default=False,
    help="Show full recreation script",
)
@click.option(
    "--products",
    is_flag=True,
    default=False,
    help="Show detailed product tracking",
)
def show(blueprint_path: str, scenes: bool, script: bool, products: bool):
    """
    Display a previously generated blueprint.

    BLUEPRINT_PATH: Path to the blueprint JSON file
    """
    from src.models.blueprint import VideoBlueprint

    try:
        blueprint = VideoBlueprint.load(blueprint_path)

        console.print()
        version_str = f"v{blueprint.analysis_version}"
        console.print(
            Panel.fit(
                f"[bold blue]Video Blueprint[/bold blue] ({version_str})\n"
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

        # Pacing metrics (if available)
        if blueprint.pacing_metrics:
            console.print()
            console.print("[bold]Pacing Metrics:[/bold]")
            pm = blueprint.pacing_metrics
            console.print(f"  Words per minute: {pm.words_per_minute:.0f}")
            console.print(f"  Total words: {pm.total_word_count}")
            console.print(f"  Speaking time: {pm.speaking_time:.1f}s")
            console.print(f"  Silence time: {pm.silence_time:.1f}s")
            console.print(f"  Speaking ratio: {pm.speaking_ratio:.0%}")
            if pm.cuts_per_minute > 0:
                console.print(f"  Cuts per minute: {pm.cuts_per_minute:.1f}")
            console.print(f"  Hook WPM: {pm.hook_wpm:.0f}")
            console.print(f"  Body WPM: {pm.body_wpm:.0f}")
            console.print(f"  CTA WPM: {pm.cta_wpm:.0f}")

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

        # Detailed scene breakdown (if requested and available)
        if scenes and blueprint.scene_breakdown:
            console.print()
            console.print(
                Panel.fit(
                    f"[bold]Scene Breakdown[/bold] ({blueprint.scene_breakdown.total_scenes} scenes)",
                    border_style="cyan",
                )
            )

            for scene in blueprint.scene_breakdown.scenes:
                console.print()
                console.print(
                    f"[bold cyan]Scene {scene.scene_number}[/bold cyan] "
                    f"[dim]({scene.start:.1f}s - {scene.end:.1f}s, {scene.duration:.1f}s)[/dim]"
                )
                console.print(
                    f"  Type: [green]{scene.scene_type.value}[/green] | "
                    f"Shot: [yellow]{scene.shot_type.value}[/yellow]"
                )

                if scene.location:
                    loc_str = f"  Location: {scene.location}"
                    if scene.setting_change:
                        loc_str += " [red][NEW][/red]"
                    console.print(loc_str)

                if scene.transcript_text:
                    text_preview = scene.transcript_text[:80]
                    if len(scene.transcript_text) > 80:
                        text_preview += "..."
                    console.print(f'  Speech: [dim]"{text_preview}"[/dim]')

                if scene.actions:
                    action_strs = [
                        f"{a.gesture.value}: {a.description[:30]}"
                        for a in scene.actions[:2]
                    ]
                    console.print(f"  Actions: {'; '.join(action_strs)}")

                if scene.expressions:
                    expr_strs = [e.expression.value for e in scene.expressions[:3]]
                    console.print(f"  Expressions: {', '.join(expr_strs)}")

                if scene.product_appearances:
                    for prod in scene.product_appearances:
                        prod_str = f"  Product: {prod.product_name or 'visible'}"
                        prod_str += f" ({prod.interaction})"
                        if prod.is_demo:
                            prod_str += " [green][DEMO][/green]"
                        console.print(prod_str)

                if scene.recreation_instruction:
                    console.print(f"  [dim]→ {scene.recreation_instruction}[/dim]")

        # Detailed product tracking (if requested and available)
        if products and blueprint.product_tracking:
            console.print()
            console.print(
                Panel.fit(
                    f"[bold]Product Tracking[/bold] ({len(blueprint.product_tracking.products)} products)",
                    border_style="magenta",
                )
            )

            pt = blueprint.product_tracking
            console.print(f"  Total screen time: {pt.total_product_screen_time:.1f}s")
            console.print(
                f"  Product ratio: {pt.product_to_content_ratio:.1%} of video"
            )

            for product in pt.products:
                console.print()
                console.print(f"  [bold magenta]{product.name}[/bold magenta]")
                if product.brand:
                    console.print(f"    Brand: {product.brand}")
                console.print(f"    Category: {product.category}")
                console.print(f"    Screen time: {product.total_screen_time:.1f}s")
                console.print(f"    First appearance: {product.first_appearance:.1f}s")
                console.print(f"    Appearances: {product.appearance_count}")
                if product.demo_moments:
                    demo_times = [f"{t:.1f}s" for t in product.demo_moments]
                    console.print(f"    Demo moments: {', '.join(demo_times)}")
                if product.key_features_shown:
                    console.print(
                        f"    Features: {', '.join(product.key_features_shown[:5])}"
                    )

        # Full recreation script (if requested and available)
        if script and blueprint.recreation_script:
            console.print()
            console.print(
                Panel.fit(
                    "[bold]Full Recreation Script[/bold]",
                    border_style="green",
                )
            )

            for instruction in blueprint.recreation_script:
                console.print()
                console.print(f"[dim]{instruction}[/dim]")
                console.print("[dim]" + "─" * 60 + "[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print_exception()
        sys.exit(1)


@main.command()
def version():
    """Show version information"""
    console.print("[bold]AutoUGC[/bold] v0.2.0")
    console.print("Phase 1: TikTok Analyzer (Enhanced)")
    console.print()
    console.print("Core Components:")
    console.print("  - Audio extraction (ffmpeg)")
    console.print("  - Transcription (Whisper)")
    console.print("  - Visual analysis (Claude Vision)")
    console.print("  - Structure parsing (Claude)")
    console.print()
    console.print("Enhanced Analysis (v2.0):")
    console.print("  - Scene segmentation")
    console.print("  - Action/gesture detection")
    console.print("  - Product tracking")
    console.print("  - Pacing metrics (WPM, pauses)")
    console.print("  - Recreation script generation")


if __name__ == "__main__":
    main()
