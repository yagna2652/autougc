# Gemini Interaction Analysis Prompt

Paste this into Gemini along with 5-15 TikTok videos of people interacting with the mechanical keyboard keychain.

---

## PROMPT

I'm uploading multiple TikTok/short-form videos of real people interacting with a product: a **mechanical keyboard keychain** (a tiny 4-key mechanical keyboard on a keychain, about 7cm long). These are real UGC videos that performed well on TikTok.

Watch every video carefully, paying close attention to the hands. I need you to build a comprehensive **interaction profile** that captures exactly how real humans interact with this product on camera. This will be used to generate AI videos, so precision matters — vague descriptions are useless.

### PART 1: GRIP ANALYSIS

For each video, note:
- Which hand holds the product? (dominant or non-dominant?)
- Exactly where on the product do the fingers grip? (sides? top and bottom? wrapped around?)
- Which fingers stabilize it? (thumb + index? thumb + middle? palm cradle?)
- How tight is the grip? (firm/locked vs. loose/casual)
- Does the grip shift during the video or stay constant?
- What is the orientation of the product relative to the camera? (horizontal? angled? vertical?)

Then synthesize across ALL videos: **What is the most common grip pattern?**

### PART 2: FINGER CHOREOGRAPHY

For each interaction moment in each video:
- Which finger(s) press the keys? (index? thumb? multiple?)
- How many keys are pressed per interaction burst?
- What is the pressing pattern? (left-to-right sweep? random? single repeated key? alternating?)
- How deep is the keypress visually? (full travel? light tap?)
- What is the speed/rhythm? (rapid fire? deliberate single clicks? rhythmic pattern?)
- Does the pressing hand switch roles with the holding hand at any point?

Synthesize: **What are the 3-5 most common interaction patterns, ranked by frequency?**

### PART 3: WHAT STAYS STILL

This is critical. For each video:
- Does the product body move/rotate during key presses, or stay locked?
- Does the holding hand's wrist move?
- Does the holding hand's fingers shift?
- Is the chain visible? Is it dangling, tucked, or held?
- What is the camera doing — static, slight movement, or dynamic?

Synthesize: **What elements are consistently stationary across all videos?**

### PART 4: TIMING AND RHYTHM

For each video:
- How long is the first interaction (from first touch to first pause)?
- How many click bursts are there?
- What's the approximate clicks-per-second during active pressing?
- Are there dramatic pauses between bursts?
- Does the rhythm match music/audio or is it independent?

Synthesize: **What is the typical timing signature?** (e.g., "3-4 rapid clicks over 1 second, 0.5s pause, repeat")

### PART 5: CAMERA AND FRAMING

For each video:
- How close is the camera to the product? (extreme close-up? medium? wide?)
- What angle? (top-down? eye-level? slightly above? below looking up?)
- Is it handheld or stable?
- Is the person's face visible or just hands?
- What's the background? (desk? lap? held up to camera?)

Synthesize: **What are the 2-3 most common framing setups?**

### PART 6: IMPOSSIBLE INTERACTIONS (NEGATIVE PROFILE)

This is the most important section. Based on everything you observed:

List every interaction that **NEVER happens** across all videos. Be exhaustive. Think about:
- Do people ever use two hands to press keys simultaneously?
- Do people ever press between the keys or outside the keycaps?
- Do people ever throw it in the air and catch it?
- Do people ever press more than one key at the exact same time?
- Do people ever hold it by the chain while pressing keys?
- Do people ever use their palm or knuckle to press?
- Are there any finger combinations that never appear?
- Any movements that would be physically impossible given the product size?

List them as: **"Never observed: [specific interaction]"**

### PART 7: STRUCTURED OUTPUT

After your analysis, compile everything into this exact format:

```
GRIP:
[2-3 sentences describing the canonical grip]

INTERACTION_PATTERNS:
1. [Pattern name]: [Detailed description with finger specifics]
2. [Pattern name]: [Detailed description with finger specifics]
3. [Pattern name]: [Detailed description with finger specifics]
(up to 5)

STATIONARY_ELEMENTS:
- [What stays still, bullet list]

TIMING:
[1-2 sentences on rhythm signature]

CAMERA_SETUPS:
1. [Setup name]: [Description]
2. [Setup name]: [Description]

IMPOSSIBLE_INTERACTIONS:
- [Never-seen interaction 1]
- [Never-seen interaction 2]
- [Never-seen interaction 3]
(be exhaustive, aim for 10+)

ADDITIONAL_OBSERVATIONS:
[Anything surprising or notable that doesn't fit above categories]
```

Take your time. Watch each video multiple times if needed. I need accuracy over speed.
