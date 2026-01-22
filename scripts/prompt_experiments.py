"""
Prompt Experimentation System for UGC Realism Testing

Tests different prompt variations to find the most realistic UGC output.
Focuses on: skin texture, eye contact, camera movement, iPhone aesthetic
"""

import os
import time
from datetime import datetime
from pathlib import Path

import fal_client
from dotenv import load_dotenv

load_dotenv()

# Set FAL API key
fal_key = os.getenv("FAL_KEY")
if fal_key:
    os.environ["FAL_KEY"] = fal_key


# =============================================================================
# PROMPT BUILDING BLOCKS
# =============================================================================

# Camera/Device descriptors - make it feel like iPhone footage
CAMERA_STYLES = {
    "iphone_basic": "filmed on iPhone, vertical video, front-facing camera",
    "iphone_detailed": "filmed on iPhone 14 Pro front camera, slight lens distortion at edges, natural phone camera quality, not cinematic",
    "iphone_selfie": "iPhone selfie video, arm's length distance, front camera with slight wide-angle distortion",
    "amateur": "amateur smartphone footage, imperfect framing, casual phone recording",
    "raw_phone": "raw unedited iPhone footage, no stabilization, natural phone camera shake",
}

# Camera movement - authentic handheld feel
MOVEMENT_STYLES = {
    "handheld_subtle": "subtle handheld micro-movements, natural hand tremor",
    "handheld_amateur": "amateur handheld camera shake, imperfect stabilization, slight drift",
    "selfie_adjust": "occasional frame adjustments as if checking the screen, natural selfie movements",
    "breathing": "gentle movement from breathing while holding phone, organic micro-shake",
    "static_attempt": "attempting to hold camera still but with natural human micro-movements",
}

# Skin and appearance - avoid AI perfection
SKIN_REALISM = {
    "natural_skin": "natural skin with visible pores and texture, not airbrushed",
    "imperfect_skin": "real human skin texture, minor imperfections, natural sebum shine",
    "detailed_skin": "photorealistic skin with pores, fine lines, natural uneven skin tone, peach fuzz visible",
    "no_filter": "no beauty filter, no skin smoothing, raw camera capture of real skin",
    "authentic_face": "authentic human face with natural asymmetry, real skin texture, visible pores near nose",
}

# Eye contact and gaze
EYE_CONTACT = {
    "phone_screen": "looking at phone screen not lens, slightly below camera eye contact",
    "checking_frame": "occasionally glancing at screen to check framing then back to lens",
    "natural_gaze": "natural eye contact with camera, occasional blinks, eyes not perfectly centered",
    "authentic_look": "looking into front-facing camera, slight downward angle as if looking at phone screen",
    "real_eyeline": "eyeline slightly off-center as typical with selfie videos, natural eye movements",
}

# Lighting - avoid studio perfection
LIGHTING_STYLES = {
    "ring_light": "ring light reflection visible in eyes, typical influencer bedroom setup",
    "window_light": "natural window lighting from one side, soft shadows on face",
    "mixed_amateur": "mixed lighting sources, slightly uneven illumination, not professionally lit",
    "bedroom_natural": "casual bedroom lighting, overhead light mixed with window, not color corrected",
    "raw_indoor": "raw indoor lighting, slight color cast, no professional lighting setup",
}

# Setting and environment
SETTINGS = {
    "messy_bedroom": "casual messy bedroom background, unmade bed visible, real lived-in space",
    "bathroom_mirror": "bathroom setting, mirror selfie style, toiletries visible in background",
    "kitchen_casual": "kitchen counter background, casual home environment, everyday clutter",
    "living_room": "living room couch, casual home setting, blankets and pillows visible",
    "generic_home": "typical home interior, not styled or staged, authentic everyday environment",
}

# Person appearance and behavior
PERSON_AUTHENTIC = {
    "casual_look": "wearing casual loungewear, no makeup or minimal makeup, hair not perfectly styled",
    "just_woke_up": "casual morning appearance, slightly messy hair, comfortable clothes",
    "real_person": "average everyday person, not model-like, relatable appearance",
    "authentic_style": "genuine casual style, comfortable clothes, natural unstaged appearance",
    "no_glam": "no professional styling, everyday casual look, authentically dressed",
}

# Energy and delivery
ENERGY_STYLES = {
    "genuine_excited": "genuinely excited but not over-the-top, authentic enthusiasm",
    "casual_share": "casually sharing like talking to a friend, relaxed energy",
    "real_reaction": "real authentic reaction, not performed or acted, genuine emotion",
    "conversational": "conversational tone, like facetiming a friend, natural delivery",
    "unscripted_feel": "feels unscripted and spontaneous, natural speech patterns",
}


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================


def build_ugc_prompt(
    action: str,
    camera: str = "iphone_detailed",
    movement: str = "handheld_amateur",
    skin: str = "detailed_skin",
    eyes: str = "phone_screen",
    lighting: str = "bedroom_natural",
    setting: str = "messy_bedroom",
    person: str = "casual_look",
    energy: str = "genuine_excited",
    extra: str = "",
) -> str:
    """
    Build a UGC-style prompt from components.

    Args:
        action: What the person is doing (e.g., "holding up a green supplement bottle")
        camera: Key from CAMERA_STYLES
        movement: Key from MOVEMENT_STYLES
        skin: Key from SKIN_REALISM
        eyes: Key from EYE_CONTACT
        lighting: Key from LIGHTING_STYLES
        setting: Key from SETTINGS
        person: Key from PERSON_AUTHENTIC
        energy: Key from ENERGY_STYLES
        extra: Additional prompt text

    Returns:
        Complete prompt string
    """
    parts = [
        CAMERA_STYLES.get(camera, camera),
        MOVEMENT_STYLES.get(movement, movement),
        f"young woman in her 20s {action}",
        SKIN_REALISM.get(skin, skin),
        EYE_CONTACT.get(eyes, eyes),
        LIGHTING_STYLES.get(lighting, lighting),
        SETTINGS.get(setting, setting),
        PERSON_AUTHENTIC.get(person, person),
        ENERGY_STYLES.get(energy, energy),
    ]

    if extra:
        parts.append(extra)

    return ", ".join(parts)


# Pre-built experiment prompts
EXPERIMENT_PROMPTS = {
    "v1_baseline": """
        Smartphone vertical video, young woman in her 20s in a casual bedroom setting,
        holding up a small green supplement bottle enthusiastically toward the camera,
        natural window lighting, authentic TikTok style, handheld camera with slight shake,
        she's smiling and excited, wearing casual clothes, relatable everyday person vibe,
        morning routine aesthetic
    """,
    "v2_iphone_focus": """
        filmed on iPhone 14 front camera, vertical selfie video, slight wide-angle lens distortion,
        young woman in her 20s holding up a green supplement bottle excitedly,
        natural phone camera quality NOT cinematic, amateur handheld micro-shake from breathing,
        real skin texture with visible pores not airbrushed, looking at phone screen slightly below lens,
        ring light reflection in eyes, messy bedroom background with unmade bed,
        wearing oversized t-shirt, genuine excitement like sharing with a friend,
        raw unedited iPhone footage aesthetic
    """,
    "v3_anti_ai": """
        raw iPhone front camera footage, NOT AI generated looking, NOT cinematic, NOT smooth,
        real human young woman holding green vitamin bottle toward camera,
        IMPERFECT: slight camera shake, natural hand tremor, amateur framing,
        REAL SKIN: visible pores, natural texture, slight shine, no smoothing filter,
        EYES: looking at phone screen not through it, checking her framing occasionally,
        bedroom with actual mess visible, wearing yesterday's clothes,
        genuinely excited but not acted, like a real TikTok creator,
        natural uneven indoor lighting, no color grading
    """,
    "v4_hyperreal": """
        ultra realistic iPhone 14 Pro selfie video, documentary-style authenticity,
        young woman early 20s excitedly showing green supplement bottle to camera,
        photorealistic skin: visible pores on nose and cheeks, natural skin texture, peach fuzz in light,
        micro-expressions, natural blink rate, eyes focused slightly below camera lens at screen,
        subtle hand tremor while holding phone, breathing movement in frame,
        casual bedroom: clothes on chair, charging cables, real lived-in space,
        overhead light mixed with window creating uneven lighting, slight shadows,
        wearing comfortable clothes, hair in messy bun, no makeup,
        authentic unforced smile, genuine product excitement, talking like to a close friend
    """,
    "v5_tiktok_native": """
        native TikTok video aesthetic, iPhone front camera at arm's length,
        young woman doing a product review in her bedroom, holding green gummy bottle,
        the specific look of real TikTok creators: checking themselves in screen,
        slight wide angle distortion on face edges from phone camera,
        real skin not filtered - you can see texture and pores clearly,
        that slightly awkward eye contact of looking at yourself on screen,
        typical bedroom setup: ring light visible as catchlight, messy background they tried to hide,
        wearing a big hoodie, hair not done, this is clearly not a professional shoot,
        genuine energy like she actually likes the product, not reading a script,
        handheld wobble, occasional reframing, raw phone footage quality
    """,
    "v6_maximum_real": """
        iPhone 13 front facing camera video, filmed vertically for TikTok,
        a real young woman not a model, mid-20s, average everyday appearance,
        holding a green supplement bottle up to show the camera while talking excitedly,

        CRITICAL - MUST LOOK REAL NOT AI:
        - skin has visible pores especially on nose, natural sebum shine on t-zone
        - slight dark circles under eyes, normal human imperfections
        - eyes looking at the phone screen not the lens, that typical selfie video eye line
        - natural asymmetrical face, one eye slightly different than other
        - real hair with flyaways, not perfectly styled

        CAMERA FEEL:
        - handheld shake from her arm getting tired holding phone up
        - slight focus hunting occasionally
        - that iPhone front camera slight distortion
        - NO stabilization, raw footage feel

        ENVIRONMENT:
        - her actual bedroom, not cleaned up for video
        - can see edge of unmade bed, maybe some clothes
        - mixed lighting: ceiling light on plus some window light
        - not aesthetically arranged, real life mess

        ENERGY:
        - genuinely likes the product, not acting
        - talking like she's FaceTiming her best friend
        - natural umms and pauses, not scripted delivery
        - real smile that reaches her eyes
    """,
}


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================


def generate_video(
    prompt: str,
    output_name: str,
    duration: int = 4,
    aspect_ratio: str = "9:16",
) -> dict:
    """
    Generate a video using Sora 2 via Fal.ai

    Args:
        prompt: The generation prompt
        output_name: Name for the output file (without extension)
        duration: Video duration (4, 8, or 12 seconds)
        aspect_ratio: Aspect ratio (9:16 for portrait)

    Returns:
        Dict with result info
    """
    if not os.getenv("FAL_KEY"):
        return {"error": "FAL_KEY not set in environment"}

    print(f"🎬 Generating: {output_name}")
    print(f"   Prompt: {prompt[:100]}...")
    print()

    start_time = time.time()

    try:

        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    print(f"   {log['message']}")

        result = fal_client.subscribe(
            "fal-ai/sora-2/text-to-video",
            arguments={
                "prompt": prompt.strip(),
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            },
            with_logs=True,
            on_queue_update=on_queue_update,
        )

        elapsed = time.time() - start_time

        if result and "video" in result:
            video_url = result["video"]["url"]

            # Download video
            import urllib.request

            output_dir = Path("output/experiments")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{output_name}.mp4"

            urllib.request.urlretrieve(video_url, output_path)

            print(f"✅ Saved to: {output_path}")
            print(f"   Time: {elapsed:.1f}s")
            print()

            return {
                "success": True,
                "path": str(output_path),
                "url": video_url,
                "time": elapsed,
                "prompt": prompt,
            }
        else:
            return {"error": "No video in result", "result": result}

    except Exception as e:
        return {"error": str(e)}


def run_experiment(
    experiment_name: str,
    prompt: str,
    num_variations: int = 1,
) -> list:
    """
    Run an experiment with a given prompt.

    Args:
        experiment_name: Name for this experiment
        prompt: The prompt to test
        num_variations: Number of videos to generate (for comparison)

    Returns:
        List of results
    """
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i in range(num_variations):
        output_name = f"{experiment_name}_{timestamp}"
        if num_variations > 1:
            output_name += f"_v{i + 1}"

        result = generate_video(prompt, output_name)
        result["experiment"] = experiment_name
        results.append(result)

    return results


def run_all_experiments(experiments: dict = None, duration: int = 4) -> dict:
    """
    Run all predefined experiments.

    Args:
        experiments: Dict of experiment_name -> prompt (uses EXPERIMENT_PROMPTS if None)
        duration: Video duration for each

    Returns:
        Dict of experiment_name -> result
    """
    if experiments is None:
        experiments = EXPERIMENT_PROMPTS

    all_results = {}

    print("=" * 60)
    print("RUNNING ALL EXPERIMENTS")
    print("=" * 60)
    print()

    for name, prompt in experiments.items():
        print(f"{'=' * 60}")
        print(f"EXPERIMENT: {name}")
        print(f"{'=' * 60}")

        results = run_experiment(name, prompt)
        all_results[name] = results[0] if results else {"error": "No results"}

        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, result in all_results.items():
        status = "✅" if result.get("success") else "❌"
        print(f"{status} {name}: {result.get('path', result.get('error', 'unknown'))}")

    return all_results


def quick_test(prompt: str, name: str = "quick_test") -> dict:
    """Quick single video test."""
    return generate_video(prompt, name)


# =============================================================================
# MAIN - Interactive Testing
# =============================================================================

if __name__ == "__main__":
    import sys

    print("🧪 UGC Prompt Experimentation System")
    print("=" * 50)
    print()

    if not os.getenv("FAL_KEY"):
        print("❌ FAL_KEY not found in .env")
        print("Add your Fal.ai API key to continue")
        sys.exit(1)

    print("Available experiments:")
    for i, name in enumerate(EXPERIMENT_PROMPTS.keys(), 1):
        print(f"  {i}. {name}")
    print()

    print("Options:")
    print("  - Enter number (1-6) to run single experiment")
    print("  - Enter 'all' to run all experiments")
    print("  - Enter 'custom' to test a custom prompt")
    print("  - Enter 'build' to build a prompt from components")
    print()

    choice = input("Choice: ").strip().lower()

    if choice == "all":
        run_all_experiments()

    elif choice == "custom":
        print("Enter your prompt (press Enter twice to finish):")
        lines = []
        while True:
            line = input()
            if line:
                lines.append(line)
            else:
                break
        prompt = " ".join(lines)
        quick_test(prompt, "custom_test")

    elif choice == "build":
        print("\nBuilding prompt from components...")
        print("Available options for each category - press Enter for default\n")

        action = input("Action (e.g., 'holding up a green vitamin bottle'): ").strip()
        if not action:
            action = "holding up a green supplement bottle excitedly"

        print(f"\nCamera styles: {list(CAMERA_STYLES.keys())}")
        camera = input("Camera [iphone_detailed]: ").strip() or "iphone_detailed"

        print(f"\nMovement styles: {list(MOVEMENT_STYLES.keys())}")
        movement = input("Movement [handheld_amateur]: ").strip() or "handheld_amateur"

        print(f"\nSkin styles: {list(SKIN_REALISM.keys())}")
        skin = input("Skin [detailed_skin]: ").strip() or "detailed_skin"

        print(f"\nEye contact: {list(EYE_CONTACT.keys())}")
        eyes = input("Eyes [phone_screen]: ").strip() or "phone_screen"

        print(f"\nLighting: {list(LIGHTING_STYLES.keys())}")
        lighting = input("Lighting [bedroom_natural]: ").strip() or "bedroom_natural"

        print(f"\nSetting: {list(SETTINGS.keys())}")
        setting = input("Setting [messy_bedroom]: ").strip() or "messy_bedroom"

        prompt = build_ugc_prompt(
            action=action,
            camera=camera,
            movement=movement,
            skin=skin,
            eyes=eyes,
            lighting=lighting,
            setting=setting,
        )

        print(f"\nBuilt prompt:\n{prompt}\n")

        if input("Generate? [y/N]: ").strip().lower() == "y":
            quick_test(prompt, "built_prompt")

    elif choice.isdigit():
        idx = int(choice) - 1
        names = list(EXPERIMENT_PROMPTS.keys())
        if 0 <= idx < len(names):
            name = names[idx]
            prompt = EXPERIMENT_PROMPTS[name]
            run_experiment(name, prompt)
        else:
            print("Invalid selection")

    else:
        print("Invalid choice")
