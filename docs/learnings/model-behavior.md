# Model Behavior Learnings

How the video generation models (Kling, Sora) and the prompt-writing LLM actually behave.

## Kling Video Model

### Training data biases
- **Keyboards = horizontal.** The word "keyboard" triggers horizontal orientation unless explicitly overridden.
- **"Click" = typing.** Button-pressing verbs trigger utility/typing motions, not fidget energy.
- **Anatomical compromise.** When given conflicting hand instructions (fingers behind + pressing front), it picks an awkward middle ground.

### What Kling responds to
- **Visual scene descriptions**, not technical instructions
- **Simple, concrete motions** — one action per sentence
- **Orientation keywords** in the first sentence ("held VERTICALLY", "chain dangling at bottom")
- **DO NOT SHOW blocks** — these work, but only if they actually reach the model (were being truncated)

### What Kling ignores
- Precise timing instructions (0.3s cadence, 120 BPM) — it approximates
- Complex finger choreography described in technical terms
- Instructions about things already visible in the starting image

## Prompt-Writing LLM (OpenRouter, gpt-4o-mini)

### Tendencies
- Writes "technical instruction manuals" when given detailed mechanics
- Defaults to "click", "tap", "press" even when mechanics say "squeeze", "crunch"
- Follows the interaction pattern names well (Fidget Wave, Anxious Crunch)
- Includes DO NOT SHOW blocks when instructed
- Does NOT naturally include "VERTICALLY" in the opening unless mechanics prose emphasizes it

### Critical: System prompt instructions override injected data
The LLM treats the instruction template (PHYSICS CONSTRAINTS, CRITICAL REQUIREMENTS, motion verb lists) as higher authority than the `{product_mechanics}` block. If the instructions list "click, press, tap" as the vocabulary, the LLM will use those verbs even when the mechanics text says "squeeze, plunge, crunch."

**This means:** when you change the config vocabulary, you must also update the corresponding instruction vocabulary in `generate_prompt.py`. The config data alone is not enough — the framing in the system prompt wins.

### Conflicting fields cause hedging
When two injected fields contradict each other (e.g. mechanics says "fingers are actuators" but stationary_elements says "fingers remain locked"), the LLM hedges toward the safest/most generic interpretation. Example: wrote "grip remains firm" instead of "loose, relaxed fist" because it couldn't reconcile both signals. **Always audit all config fields for internal consistency after a mechanics rewrite.**

### What helps
- Named interaction patterns with vivid descriptions (not just mechanical specs)
- Explicit forbidden actions in `impossible_interactions`
- The interaction library clips give it "beat" structure to work with
- Instruction verb lists that match the config vocabulary (don't say "click counts" if you want "squeeze")

## Gemini Analysis Model

### Strengths
- Excellent at diagnosing why a video looks wrong from prompt + output comparison
- Identifies training data biases (horizontal keyboard default)
- Spots anatomical impossibilities in prompt descriptions
- Catches truncation issues

### Best used as
A post-hoc analysis tool: feed it the raw prompt payload + video output, ask "why does this look wrong?"
See `docs/gemini-interaction-analysis-prompt.md` for the structured analysis prompt.
