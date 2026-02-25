# Product Mechanics Prompt

This is the exact text injected into the LLM as `{product_mechanics}` during prompt generation.
It is assembled by `_build_mechanics_text()` in `src/pipeline/product_loader.py` from `assets/products/keychain/config.json`.

---

4 keys in a single vertical column (1x4 layout), approximately 7cm long and 1.5cm wide. Translucent smoky housing with blue Cherry MX-style clicky switches visible inside; each key has ~2mm of travel with a sharp tactile snap (not a smooth linear glide). Metal chain with lobster clasp attached at the bottom when held vertically. The device is operated ONE-HANDED: the left hand holds and presses simultaneously. The index, middle, ring, and pinky fingers curl around the back and right side of the casing to form a firm static cradle against the middle phalanges. The thumb is the SOLE actuator — it hovers over the front face and presses one key at a time, moving up and down the vertical column. The thumb tip visibly whitens slightly from the switch resistance on each press. The grip fingers never move or adjust; only the thumb is active. The device is always held VERTICALLY with keys stacked in a column and the chain dangling at the bottom. The click sound is the hero moment — every press should feel intentional and land cleanly on a keycap.

Grip:
One-Handed Remote Grip: the left hand cradles the device vertically, with index through pinky fingers curled around the back forming a static backboard. The thumb rests on the front face as the sole operator. Grip is firm but relaxed — secure enough that the device does not slide when the thumb applies pressure to the stiff switches. The chain hangs freely at the bottom.

Interaction patterns:
- The Linear Sweep: Thumb presses keys sequentially from top to bottom (Key 1 → 2 → 3 → 4). Each press is distinct with full travel. Steady rhythm at ~120 BPM. (most common)
- The Fidget Burst: Rapid-fire pressing of a single key or oscillating between two adjacent keys (3-4 clicks per second). Thumb barely lifts off the keycap between presses. Erratic rhythm. (common)
- The LED Hold: Deliberate, slower press where the thumb holds a key down for ~0.5 seconds to fully illuminate the LED before releasing. Emphasizes the light-up response. (occasional)

Timing:
Burst and Pause: a sequence of 3-4 clicks over ~1.5 seconds (120-140 BPM), followed by a 1-second pause to admire the LED glow or reset the thumb position. The rhythm is tactile and auditory, driven by the clicky switch sound.

Stationary elements:
- The four supporting fingers (index, middle, ring, pinky) remain locked in a curled position throughout
- The clear plastic housing stays pinned against the fingers and does not slide up or down
- The wrist of the holding hand maintains a fixed position, only rotating very slightly to catch light
- Camera distance remains constant — framing does not zoom in or out

Impossible interactions:
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

## How this text is used in the LLM prompt

The mechanics text above is dropped verbatim into this section of the generation prompt:

```
## MECHANICS RULES
{product_mechanics}

These rules describe the physical reality of the product — how it's held, what moves,
what stays still, how big it is relative to hands. Your motion prompt MUST obey these
rules. If the rules say "only one finger presses at a time", do not show two fingers
pressing simultaneously. If the rules say "4 keys in a row", do not show 6 keys.

## PHYSICS CONSTRAINTS (MANDATORY IN video_prompt)
- State product scale relative to hand and stable grip.
- Specify exactly which finger(s) move in each beat.
- Specify what stays still: product body, grip hand, wrist, and palm.
- Include explicit click/press count and rhythm per beat (e.g., 4 clicks, 0.3s cadence).
- Use at least 3 explicit "DO NOT" constraints grounded in mechanics.
- Never show physically impossible gestures listed in mechanics.
```

And the `impossible_interactions` bullets are also appended to the final video prompt as a `DO NOT SHOW:` block after the LLM responds.
