# Interaction Prompt Audit

Use this file alongside the generated video output to identify what's working, what's wrong, and what to change.

---

## Layer 1 — Physical Mechanics (`assets/products/keychain/config.json`)

This is the ground truth. Everything else derives from it.

### Mechanics (prose)
```
4 keys in a single vertical column (1x4 layout), approximately 7cm long and 1.5cm wide.
Translucent smoky housing with blue Cherry MX-style clicky switches visible inside;
each key has ~2mm of travel with a sharp tactile snap (not a smooth linear glide).
Metal chain with lobster clasp attached at the bottom when held vertically.
The device is operated ONE-HANDED: the left hand holds and presses simultaneously.
The index, middle, ring, and pinky fingers curl around the back and right side of the
casing to form a firm static cradle against the middle phalanges. The thumb is the
SOLE actuator — it hovers over the front face and presses one key at a time, moving
up and down the vertical column. The thumb tip visibly whitens slightly from the switch
resistance on each press. The grip fingers never move or adjust; only the thumb is active.
The device is always held VERTICALLY with keys stacked in a column and the chain dangling
at the bottom. The click sound is the hero moment — every press should feel intentional
and land cleanly on a keycap.
```

### Grip
```
One-Handed Remote Grip: the left hand cradles the device vertically, with index through
pinky fingers curled around the back forming a static backboard. The thumb rests on the
front face as the sole operator. Grip is firm but relaxed — secure enough that the device
does not slide when the thumb applies pressure to the stiff switches. The chain hangs
freely at the bottom.
```

### Interaction Patterns
| Name | Description | Frequency |
|---|---|---|
| The Linear Sweep | Thumb presses keys sequentially top to bottom (Key 1→2→3→4). Each press distinct with full travel. Steady ~120 BPM. | Most common |
| The Fidget Burst | Rapid-fire pressing of a single key or oscillating between two adjacent keys (3–4 clicks/sec). Thumb barely lifts between presses. Erratic rhythm. | Common |
| The LED Hold | Deliberate slow press, thumb holds a key down ~0.5s to fully illuminate the LED before releasing. Emphasises light-up response. | Occasional |

### Timing
```
Burst and Pause: a sequence of 3–4 clicks over ~1.5 seconds (120–140 BPM), followed by
a 1-second pause to admire the LED glow or reset the thumb position. The rhythm is
tactile and auditory, driven by the clicky switch sound.
```

### Stationary Elements
- The four supporting fingers (index, middle, ring, pinky) remain locked in a curled position throughout
- The clear plastic housing stays pinned against the fingers and does not slide up or down
- The wrist of the holding hand maintains a fixed position, only rotating very slightly to catch light
- Camera distance remains constant — framing does not zoom in or out

### Impossible Interactions (Hard Negatives)
- two-handed interaction (holding with one hand, pressing with the other hand's finger)
- using the index finger to press keys (thumb is the sole actuator)
- holding the device horizontally in landscape orientation
- piano-style multi-finger pressing of multiple keys simultaneously
- pressing the device while it lies flat on a table or surface
- holding the device by the metal keychain ring while pressing keys
- inverted holding with the keychain ring pointing upward
- pressing the side or back of the plastic housing
- thumb pressing two keys simultaneously (fat-fingering both fully down)
- throwing or flipping the device in the air
- pressing outside the keycaps or between switches
- large wrist swings that cause the product to rotate dramatically

---

## Layer 2 — Interaction Library (`assets/interaction_library/index.json`)

The LLM picks 1–3 clips from this library to plan the "beats" of the video.

### Available Clips
| ID | Primitive | Framing | Duration | Tempo | Audio | Tags |
|---|---|---|---|---|---|---|
| mkc_closeup_click_loop_01 | closeup_click_loop | macro_closeup | 4.2s | fast | high | asmr, tactile, fidget |
| mkc_closeup_click_loop_02 | closeup_click_loop | close | 3.8s | medium | medium | tactile, fidget |
| mkc_selfie_click_01 | selfie_click_while_talking | selfie_medium | 6.5s | medium | medium | talking_head, casual, review |
| mkc_pocket_pull_01 | pocket_pull_and_click | close | 4.0s | medium | medium | reveal, everyday_carry, pocket |
| mkc_desk_idle_01 | desk_idle_click | desk_topdown | 5.0s | slow | high | workspace, productivity, idle |
| mkc_anxiety_relief_01 | anxiety_relief_click | close | 4.5s | fast | medium | stress_relief, fidget, anxiety |
| mkc_asmr_01 | sound_showcase_asmr | macro_closeup | 5.5s | slow | high | asmr, sound, tactile, satisfying |
| mkc_asmr_02 | sound_showcase_asmr | macro_closeup | 4.8s | medium | high | asmr, sound, crispy |
| mkc_dangle_click_01 | keychain_dangle_then_click | close | 3.5s | medium | medium | keychain, dangle, reveal |
| mkc_compare_clicks_01 | compare_clicks_variation | macro_closeup | 6.0s | varied | high | comparison, variation, demonstration |

### Primitives Registry (8 total)
| Primitive | Description | Ideal Framing | Duration Range | Audio Importance |
|---|---|---|---|---|
| closeup_click_loop | Macro shot of fingers clicking in loop | macro_closeup | 3–6s | high |
| selfie_click_while_talking | Talking head while casually clicking | selfie_medium | 5–10s | medium |
| pocket_pull_and_click | Pull from pocket, start clicking | close | 3–5s | medium |
| desk_idle_click | Top-down desk, clicking while working | desk_topdown | 4–7s | medium |
| anxiety_relief_click | Stress relief through clicking | close | 3–6s | medium |
| sound_showcase_asmr | ASMR-style sound focus | macro_closeup | 4–8s | critical |
| keychain_dangle_then_click | Show dangling, then click | close | 3–5s | low |
| compare_clicks_variation | Different click styles/speeds | macro_closeup | 5–8s | high |

---

## Layer 3 — LLM Prompt Instructions (`src/pipeline/nodes/generate_prompt.py`)

This is the full set of instructions the LLM receives that shape interaction output.

### Mechanics injection (verbatim)
```
## MECHANICS RULES
{product_mechanics}

These rules describe the physical reality of the product — how it's held, what moves,
what stays still, how big it is relative to hands. Your motion prompt MUST obey these
rules. If the rules say "only one finger presses at a time", do not show two fingers
pressing simultaneously. If the rules say "4 keys in a row", do not show 6 keys.
```

### Physics constraints (verbatim, mandatory in output)
```
## PHYSICS CONSTRAINTS (MANDATORY IN video_prompt)
- State product scale relative to hand and stable grip.
- Specify exactly which finger(s) move in each beat.
- Specify what stays still: product body, grip hand, wrist, and palm.
- Include explicit click/press count and rhythm per beat (e.g., 4 clicks, 0.3s cadence).
- Use at least 3 explicit "DO NOT" constraints grounded in mechanics.
- Never show physically impossible gestures listed in mechanics.
```

### Task instructions (verbatim)
```
## YOUR TASK
1. Pick 1–3 clips from the library that fit the TikTok's energy and style
2. Plan the beats — a short choreographed sequence (total ≤ 12 seconds)
3. Write a motion prompt describing how the scene animates from the product image
4. Write a casual script (1–3 sentences) adapted for this product
```

### Motion focus instructions (verbatim)
```
FOCUS ON MOTION (the product image is already visible):
- Hand movements: pull, click, flip, rotate, squeeze, tap
- Timing and rhythm of actions
- Camera motion per beat (push in, pull back, slight pan)
- Energy and dynamics (quick/snappy vs smooth/slow)
- DO NOT describe the product's appearance (colors, materials, shape)
```

### Critical requirements — interaction-relevant ones (verbatim)
```
1. Starting frame shows the product — describe how it MOVES from there
2. Follow the MECHANICS RULES exactly — do not invent impossible movements
4. Focus on hand movements, camera motion, energy
6. Motion verbs: pull, click, flip, rotate, press, slide, reveal
12. For each beat, name the active finger(s) and which hand stabilizes the product
13. Explicitly state what remains stationary in each beat
14. Add a clear "DO NOT SHOW" section inside the video prompt
```

### Output format — `video_prompt` field instruction (verbatim)
```
"video_prompt": "A motion-focused prompt. Start with scene setup, then beat-by-beat
motion with exact finger choreography, click counts, cadence, what remains still, and
a DO NOT SHOW section. Do not describe product appearance."
```

### Negative prompt field instruction (verbatim)
```
"negative_prompt": "A semicolon-separated list of explicit forbidden motions from
mechanics and physics constraints."
```

---

## Layer 4 — Negative Constraint Appending (`generate_prompt.py` → `_append_negative_constraints`)

After the LLM responds, the pipeline appends a `DO NOT SHOW:` block to the final `video_prompt`. It uses either:
1. The LLM's own `negative_prompt` field (preferred), or
2. Auto-extracted bullet points from the `impossible_interactions` section of the mechanics text

The final prompt structure sent to the video model is:
```
{video_prompt}

DO NOT SHOW:
- {constraint 1}
- {constraint 2}
...
```

---

## Analysis Worksheet

Use this section while watching the generated video.

### What to observe
- [ ] Is the device held vertically with chain dangling at the bottom?
- [ ] Is only ONE hand used?
- [ ] Is the THUMB the only finger pressing keys?
- [ ] Do the grip fingers stay locked/stationary?
- [ ] Does the thumb press one key at a time (no fat-fingering)?
- [ ] Is the wrist staying mostly fixed?
- [ ] Does the rhythm match (burst then pause, ~120 BPM)?
- [ ] Is the click the "hero moment" — intentional, clean?
- [ ] Does the camera stay at a constant distance?

### What's going wrong (fill in after watching)
```
Issue 1:


Issue 2:


Issue 3:

```

### Which layer is the likely cause
| Issue | Probable Layer | Fix location |
|---|---|---|
| Wrong finger pressing | Mechanics prose too vague | `config.json` → `mechanics` / `grip` |
| Wrong hand position | Grip description unclear | `config.json` → `grip` |
| Rhythm/timing off | Timing or patterns too vague | `config.json` → `timing` / `interaction_patterns` |
| Clip type mismatch | Wrong primitive selected | `index.json` → clips, or LLM prompt framing |
| LLM ignoring rules | Mechanics not emphatic enough | `generate_prompt.py` → PHYSICS CONSTRAINTS section |
| Wrong action altogether | Impossible interaction not listed | `config.json` → `impossible_interactions` |
