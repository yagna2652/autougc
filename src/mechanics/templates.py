"""
Template Library for Mechanics Engine.

Contains tested patterns for hooks, body sections, and CTAs
that produce realistic human mechanics in Sora 2.
"""

from src.mechanics.models import (
    SegmentType,
    HandPosition,
    ExpressionState,
    BodyPosture,
    EyeDirection,
    HandMechanics,
    ExpressionMechanics,
    BodyMechanics,
    EyeMechanics,
    ProductMechanics,
)


# =============================================================================
# HOOK TEMPLATES
# =============================================================================

HOOK_TEMPLATES = {
    "product_reveal": {
        "description": "Product rises into frame with excited reveal",
        "hands": HandMechanics(
            position=HandPosition.HOLDING_PRODUCT,
            description="Right hand rises from below frame, holding bottle at slight angle toward camera",
            which_hand="right",
            movement="rises smoothly from below frame",
            holds_product=True,
            product_angle="slight tilt toward camera",
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.EXCITED_SMILE,
            description="Raised eyebrows → widening smile as product enters frame",
            transition_from=ExpressionState.RAISED_EYEBROWS,
            transition_desc="transitions to excited smile",
            micro_expressions=["eyebrow flash", "slight lip purse before smile"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.LEANING_FORWARD,
            description="Subtle forward lean toward camera, natural arm tremor",
            movement="slight forward movement",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_PRODUCT,
            description="Quick glance at product, then back to phone screen",
            blink_pattern="natural",
            glance_pattern="product → camera → product",
        ),
        "product": ProductMechanics(
            visible=True,
            interaction="Held up beside face, label facing camera",
            position_in_frame="right side, face height",
            reveal_style="rises from below frame",
        ),
    },
    "pov_storytelling": {
        "description": "POV style hook with direct camera address",
        "hands": HandMechanics(
            position=HandPosition.GESTURING,
            description="Hands gesture conversationally, palms open toward camera",
            which_hand="both",
            movement="natural conversational gestures",
            holds_product=False,
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.RAISED_EYEBROWS,
            description="Eyebrows raised in 'you won't believe this' expression, slight head tilt",
            micro_expressions=["knowing look", "subtle smirk"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.LEANING_FORWARD,
            description="Conspiratorial lean toward camera, like sharing a secret",
            movement="slight forward lean",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Direct eye contact with camera, intimate connection",
            blink_pattern="natural",
            glance_pattern="steady with occasional natural breaks",
        ),
    },
    "curiosity_hook": {
        "description": "Creates curiosity with skeptical-to-surprised transition",
        "hands": HandMechanics(
            position=HandPosition.ON_FACE,
            description="One hand near chin in thinking pose, then drops as realization hits",
            which_hand="right",
            movement="drops from face as expression changes",
            holds_product=False,
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.SURPRISED,
            description="Thinking expression → eyes widen with realization",
            transition_from=ExpressionState.THINKING,
            transition_desc="transforms into surprise",
            micro_expressions=["slight frown", "eye widening"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.UPRIGHT,
            description="Slight backward movement in surprise, then forward with interest",
            movement="micro-recoil then lean",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Eyes widen, brief glance away then back to emphasize discovery",
            blink_pattern="slow deliberate blink",
            glance_pattern="away → back with wider eyes",
        ),
    },
    "casual_share": {
        "description": "Casual, friend-sharing-discovery style hook",
        "hands": HandMechanics(
            position=HandPosition.GESTURING,
            description="Relaxed hand gesture, palm up like offering information",
            which_hand="right",
            movement="casual explanatory gesture",
            holds_product=False,
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.SOFT_SMILE,
            description="Relaxed, genuine smile, slightly asymmetrical",
            micro_expressions=["natural blink", "slight head nod"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.UPRIGHT,
            description="Relaxed posture, slight natural sway",
            movement="minimal, natural micro-movements",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Friendly eye contact, like talking to a friend",
            blink_pattern="natural",
            glance_pattern="steady with conversational breaks",
        ),
    },
}


# =============================================================================
# BODY TEMPLATES
# =============================================================================

BODY_TEMPLATES = {
    "demonstration": {
        "description": "Active product demonstration",
        "hands": HandMechanics(
            position=HandPosition.DEMONSTRATING,
            description="Rotates product to show label, unscrews cap, demonstrates use",
            which_hand="both",
            movement="deliberate demonstration movements",
            holds_product=True,
            product_angle="varies to show different angles",
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.GENUINE_WARMTH,
            description="Excited smile softens to genuine warmth, slight nod of approval",
            transition_from=ExpressionState.EXCITED_SMILE,
            transition_desc="softens to",
            micro_expressions=["approval nod", "satisfied lip press"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.UPRIGHT,
            description="Stable posture for demonstration, slight movements for emphasis",
            movement="subtle shifts to show product angles",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_PRODUCT,
            description="Glances between phone and product conversationally",
            blink_pattern="natural",
            glance_pattern="camera → product → camera rhythm",
        ),
        "product": ProductMechanics(
            visible=True,
            interaction="Active demonstration - showing, opening, using",
            position_in_frame="center, well-lit",
            demonstration="opening, applying, or showing key feature",
        ),
    },
    "testimonial": {
        "description": "Personal experience sharing",
        "hands": HandMechanics(
            position=HandPosition.GESTURING,
            description="Emphatic hand gestures, touches chest for personal emphasis",
            which_hand="both",
            movement="emotional, personal gestures",
            holds_product=False,
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.EMPHATIC,
            description="Expressive face showing genuine emotion, eyebrows move with emphasis",
            micro_expressions=["eyebrow raises on key words", "genuine smile breaks through"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.LEANING_FORWARD,
            description="Engaged forward lean, body language shows conviction",
            movement="emphatic movements matching speech",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Direct sincere eye contact, occasional look up when remembering",
            blink_pattern="natural",
            glance_pattern="camera with occasional upward glances when recalling",
        ),
    },
    "education": {
        "description": "Teaching/explaining content",
        "hands": HandMechanics(
            position=HandPosition.COUNTING,
            description="Counts on fingers for points, uses hand as visual guide",
            which_hand="both",
            movement="counting, pointing, explaining gestures",
            holds_product=False,
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.CURIOUS,
            description="Engaged, teacher-like expression, eyebrows raise for emphasis",
            micro_expressions=["knowing nods", "emphasis expressions"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.UPRIGHT,
            description="Authoritative but friendly posture",
            movement="slight movements for emphasis",
            natural_tremor=False,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Direct teaching eye contact, occasional thoughtful glances",
            blink_pattern="natural",
            glance_pattern="steady with emphasis breaks",
        ),
    },
    "comparison": {
        "description": "Before/after or product comparison",
        "hands": HandMechanics(
            position=HandPosition.HOLDING_PRODUCT,
            description="Holds product(s) at different positions for comparison",
            which_hand="both",
            movement="shifting between positions",
            holds_product=True,
            product_angle="varied for comparison",
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.RAISED_EYEBROWS,
            description="Skeptical look → impressed expression transition",
            transition_from=ExpressionState.THINKING,
            transition_desc="transforms to impressed",
            micro_expressions=["skeptical squint", "impressed eye widening"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.UPRIGHT,
            description="Steady for clear comparison shots",
            movement="minimal for clarity",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_PRODUCT,
            description="Eyes move between comparison points",
            blink_pattern="natural",
            glance_pattern="product A → product B → camera",
        ),
    },
}


# =============================================================================
# CTA TEMPLATES
# =============================================================================

CTA_TEMPLATES = {
    "soft_recommendation": {
        "description": "Gentle, friendly recommendation",
        "hands": HandMechanics(
            position=HandPosition.HOLDING_PRODUCT,
            description="Holds product gently, slight lift toward camera",
            which_hand="right",
            movement="gentle presentation gesture",
            holds_product=True,
            product_angle="label toward camera",
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.GENUINE_WARMTH,
            description="Warm, genuine smile, slight head tilt",
            micro_expressions=["genuine smile", "friendly nod"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.LEANING_FORWARD,
            description="Slight lean in for intimacy",
            movement="gentle forward movement",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Warm direct eye contact, like talking to a friend",
            blink_pattern="natural",
            glance_pattern="steady friendly gaze",
        ),
        "product": ProductMechanics(
            visible=True,
            interaction="Gentle hold, final display",
            position_in_frame="prominent but not pushy",
        ),
    },
    "urgent_action": {
        "description": "Energetic call to action",
        "hands": HandMechanics(
            position=HandPosition.POINTING,
            description="Points toward camera/link area, emphatic gesture",
            which_hand="right",
            movement="decisive pointing motion",
            holds_product=False,
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.EXCITED_SMILE,
            description="Excited, urgent expression, eyes wide with enthusiasm",
            micro_expressions=["eyebrow flash", "urgent nod"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.LEANING_FORWARD,
            description="Forward lean with energy, sense of urgency",
            movement="emphatic forward movement",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Intense, direct eye contact emphasizing urgency",
            blink_pattern="minimal",
            glance_pattern="locked on camera",
        ),
    },
    "curious_tease": {
        "description": "Leaves viewer curious, soft close",
        "hands": HandMechanics(
            position=HandPosition.GESTURING,
            description="Slight shrug gesture, palms up, 'try it yourself' motion",
            which_hand="both",
            movement="open, inviting gesture",
            holds_product=False,
        ),
        "expression": ExpressionMechanics(
            state=ExpressionState.CURIOUS,
            description="Knowing smile, raised eyebrow, 'you'll see' expression",
            micro_expressions=["knowing look", "slight smirk"],
        ),
        "body": BodyMechanics(
            posture=BodyPosture.SHRUGGING,
            description="Casual shrug, relaxed confidence",
            movement="light shrug motion",
            natural_tremor=True,
        ),
        "eyes": EyeMechanics(
            direction=EyeDirection.AT_CAMERA,
            description="Playful eye contact, slight squint of knowing",
            blink_pattern="natural",
            glance_pattern="playful, inviting gaze",
        ),
    },
}


# =============================================================================
# PRODUCT-SPECIFIC TEMPLATES
# =============================================================================

PRODUCT_CATEGORY_MODIFIERS = {
    "skincare": {
        "demonstration_actions": [
            "shows texture on back of hand",
            "gentle application motion to face",
            "shows before/after skin",
        ],
        "hold_style": "delicate, product-forward",
        "typical_reveal": "held at face level, label visible",
    },
    "supplement": {
        "demonstration_actions": [
            "shakes bottle gently",
            "opens cap, pours into hand",
            "shows pill/gummy size",
        ],
        "hold_style": "casual, medicine-cabinet familiar",
        "typical_reveal": "rises from below frame or pulled from pocket",
    },
    "tech": {
        "demonstration_actions": [
            "shows product from multiple angles",
            "demonstrates key feature",
            "shows size comparison with hand",
        ],
        "hold_style": "careful, showcasing build quality",
        "typical_reveal": "unboxing motion or deliberate reveal",
    },
    "food": {
        "demonstration_actions": [
            "shows packaging",
            "opens and shows contents",
            "taste reaction",
        ],
        "hold_style": "appetizing angles, good lighting on product",
        "typical_reveal": "held up or placed on surface",
    },
    "fashion": {
        "demonstration_actions": [
            "shows fabric/material",
            "demonstrates fit or features",
            "styling showcase",
        ],
        "hold_style": "displayed against body or held out",
        "typical_reveal": "worn or held up for display",
    },
    "general": {
        "demonstration_actions": [
            "shows product clearly",
            "demonstrates main feature",
            "shows size/scale",
        ],
        "hold_style": "clear, well-lit presentation",
        "typical_reveal": "standard reveal from below or side",
    },
}


def get_hook_template(style: str) -> dict:
    """Get a hook template by style name."""
    return HOOK_TEMPLATES.get(style, HOOK_TEMPLATES["casual_share"])


def get_body_template(framework: str) -> dict:
    """Get a body template by framework name."""
    return BODY_TEMPLATES.get(framework, BODY_TEMPLATES["demonstration"])


def get_cta_template(urgency: str) -> dict:
    """Get a CTA template by urgency style."""
    return CTA_TEMPLATES.get(urgency, CTA_TEMPLATES["soft_recommendation"])


def get_product_modifiers(category: str) -> dict:
    """Get product-specific modifiers by category."""
    return PRODUCT_CATEGORY_MODIFIERS.get(category, PRODUCT_CATEGORY_MODIFIERS["general"])
