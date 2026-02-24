# Interaction Iterations Log

Chronological record of what we tried, what failed, and what improved.

---

## Iteration 1 — Thumb-only actuator (original)

**Config:** Thumb is sole actuator. Fingers form static cradle on back. One key at a time.

**Result:** Video model showed awkward pinching grip. Character poked keys like typing on a calculator. Horizontal orientation despite vertical being specified.

**Root cause analysis (via Gemini):**
1. Missing "VERTICAL" in opening sentence — model defaults to horizontal
2. Anatomical impossibility — fingers locked behind + index pressing front = pinch compromise
3. "Click/tap" verbs triggered typing priors
4. Prompt truncated at 120 words, losing DO NOT SHOW block

---

## Iteration 2 — Wrapped fidget grip (current, 2026-02-24)

**Changes made:**
- **Mechanics:** Rewritten. Four fingers are actuators, palm is backboard, thumb stays on back/side
- **Grip:** "Wrapped Fidget Grip" — loose fist, fingers on top keycaps, thumb does NOT press
- **Interaction patterns:** Replaced with Fidget Wave, Anxious Crunch, Absentminded Hold
- **Impossible interactions:** Added thumb-pressing, side-pressing, frozen keys, calculator typing
- **prompt_safety.py:** Removed 120-word cap, verb replacements, sentence allowlist filter
- **max_tokens:** Removed from LLM call (was 2000)

**Test prompt output (test_prompt_only.py):**
- DO NOT SHOW block: survives intact (12 constraints)
- Sanitization: zero changes to prompt
- Word count: 343 (was truncated to ~120 before)
- All 3 new interaction patterns used
- Missing: "vertical" in opening, "squeeze/bounce/plunge" verbs (LLM still defaults to "click/press")

**Status:** Prompt-only test complete. Video not yet generated.

**Finding: LLM system prompt overrides config vocabulary (2026-02-24)**

Field-by-field audit of the 343-word prompt revealed 5 of 12 key config concepts are missing or wrong:

| Config says | Prompt says | Problem |
|---|---|---|
| "vertical column" | "close-up... held in the right hand" | No "VERTICALLY" anywhere |
| "loose squeezing motion" | "clicks", "pressing" | Generic verbs override vivid config language |
| "loose, relaxed fist" | "grip remains firm" | Direct contradiction |
| "keycap plunges ~2mm, springs back" | "keys depress and spring back up" | Weak, no "plunge/sink" |
| "like drumming on a desk" / "piston" | Sequential press described clinically | Energy lost |

**Root cause:** The system prompt in `generate_prompt.py` is actively fighting the config:
1. Lists "click, press, tap" as preferred motion verbs (6 mentions of "click", 0 mentions of "squeeze/plunge/bounce")
2. Frames output as "finger choreography, click counts, cadence" — technical manual style
3. `stationary_elements` in config.json still says "fingers remain locked" — contradicts new mechanics where fingers are the movers

**Lesson:** The LLM treats system prompt instructions as higher authority than injected data. If the instructions say "write click counts" and the config says "squeeze", the LLM will write "click." The instruction framing must match the config vocabulary.

**Status: FIXED (2026-02-24)**

All next steps completed in a single pass:
- Motion verb list updated: squeeze, plunge, crunch, bounce, drum, spring, sink, press
- PHYSICS CONSTRAINTS rewritten: no more "click counts" / "finger choreography"
- FOCUS ON MOTION rewritten: fidget energy, keycap contact, key physics
- video_prompt field instruction: "vivid cinematic scene" not "technical manual"
- CRITICAL REQ #12: orientation instruction instead of finger naming
- `stationary_elements` in config.json: fingers are movers, palm/back are stable
- `timing` in config.json: "reset finger position" (not thumb)
- Applied to BOTH `_build_prompt_request` and `_build_prompt_request_openrouter`

**Pending:** Video generation test to confirm Kling responds to the updated prompt vocabulary.
