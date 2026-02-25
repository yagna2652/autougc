# Interaction Mechanics

How the product interaction prompt system works end-to-end.

## The 4 Layers

### Layer 1 — Product Config (ground truth)
**File:** `assets/products/keychain/config.json`

This is the single source of truth for how the product physically behaves. Fields:
- `mechanics` — prose describing physical reality (grip, actuation, orientation)
- `grip` — how the hand holds the device
- `interaction_patterns` — named motion patterns (Fidget Wave, Anxious Crunch, Absentminded Hold)
- `timing` — rhythm and cadence
- `stationary_elements` — what doesn't move
- `impossible_interactions` — hard negatives (what must never appear)

Assembled into one text block by `_build_mechanics_text()` in `src/pipeline/product_loader.py`.

### Layer 2 — Interaction Library
**File:** `assets/interaction_library/index.json`

10 reference clips across 8 primitives. The LLM picks 1–3 clips to plan video "beats." Formatted by `_format_library()` in `generate_prompt.py` and injected as `## INTERACTION LIBRARY`.

### Layer 3 — LLM Prompt Instructions
**File:** `src/pipeline/nodes/generate_prompt.py`

The system prompt that tells the LLM how to translate mechanics into motion. Key sections:
- `## MECHANICS RULES` — injects Layer 1 verbatim
- `## PHYSICS CONSTRAINTS` — mandatory output requirements (key travel description, DO NOT constraints, no typing/utility framing)
- `## YOUR TASK` — pick clips, plan beats, write motion prompt
- `FOCUS ON MOTION` — fidget energy, keycap contact points, key physics (plunge/spring/sink)
- `CRITICAL REQUIREMENTS` — 14 rules including verb list (squeeze, plunge, crunch, bounce, drum, spring, sink, press), VERTICALLY orientation, and DO NOT SHOW section

**Important:** The instruction vocabulary MUST match the config vocabulary. The LLM treats instruction framing as higher authority than injected data (see `docs/learnings/model-behavior.md`).

### Layer 4 — Negative Constraint Appending
**Functions:** `_extract_impossible_interactions()`, `_append_negative_constraints()`

After the LLM responds, the pipeline appends `DO NOT SHOW:` bullets to the final `video_prompt` using either the LLM's `negative_prompt` field or auto-extracted `impossible_interactions`.

## Current Config State (as of 2026-02-24)

**Mechanics:** Wrapped fidget grip. Four fingers are the actuators (not thumb). Palm is backboard. Keys plunge ~2mm downward and spring back.

**Interaction Patterns:**
| Name | Description | Frequency |
|---|---|---|
| The Fidget Wave | Sequential finger press top→bottom, like drumming on a desk | Most common |
| The Anxious Crunch | Multi-finger simultaneous squeeze, bouncy and erratic | Common |
| The Absentminded Hold | Couple of fingers hold keys depressed, casual/idle | Occasional |

**Impossible Interactions (12):** Two-handed, horizontal hold, flat on table, thumb pressing, calculator-style typing, sides/edges pressing, stiff/frozen keys, and more.

## Analysis Worksheet

Use when watching generated video output:
- [ ] Device held vertically, chain dangling at bottom?
- [ ] One hand only?
- [ ] Fingers (not thumb) pressing the flat top faces of keycaps?
- [ ] Keys visibly plunging down and springing back?
- [ ] Palm acts as static backboard?
- [ ] Motion feels playful/fidgety (not typing/utility)?
- [ ] DO NOT SHOW constraints respected?

## Debugging: Which Layer to Fix

| Symptom | Probable Layer | Fix Location |
|---|---|---|
| Wrong finger pressing | Layer 1 — mechanics prose | `config.json` → `mechanics` / `grip` |
| Wrong orientation | Layer 1 — missing "vertical" | `config.json` → `mechanics` |
| Typing/utility feel | Layer 1 — interaction patterns | `config.json` → `interaction_patterns` |
| Wrong action entirely | Layer 1 — missing impossible | `config.json` → `impossible_interactions` |
| LLM ignoring rules | Layer 3 — instruction vocab mismatches config | `generate_prompt.py` → verb lists, PHYSICS CONSTRAINTS, FOCUS ON MOTION |
| Constraints missing from video | Layer 4 — truncation/sanitization | `prompt_safety.py` or `max_tokens` |
