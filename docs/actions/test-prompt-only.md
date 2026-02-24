# Action: Test Prompt Only

Run the pipeline through prompt generation without generating video. No Fal.ai cost.

## Command

```bash
uv run python scripts/test_prompt_only.py "<tiktok_url>"
```

## What it does

Runs steps 1–4 of the pipeline:
1. Downloads TikTok video
2. Extracts 5 key frames
3. Analyzes video with OpenRouter Vision (gpt-4o-mini)
4. Generates video prompt with OpenRouter LLM

Then prints:
- Full video analysis JSON
- Raw video prompt (from LLM)
- Sanitized video prompt (what Kling would receive)
- Whether DO NOT SHOW block survived
- Whether key fidget terms are present (vertical, squeeze, bounce, plunge, fidget, spring)
- Full product mechanics that were injected

## What to check

1. **DO NOT SHOW block present?** — If missing, check sanitization or LLM max_tokens
2. **Word count** — Should be 200+ words. If under 120, truncation is happening
3. **Sanitization diff** — Should say "no changes." If changes occurred, check `prompt_safety.py`
4. **Key terms** — Missing "vertical" or "squeeze" means LLM needs stronger instruction
5. **Interaction patterns** — Should see Fidget Wave / Anxious Crunch / Absentminded Hold

## Requirements

- `OPENROUTER_API_KEY` in `.env`
- Server does NOT need to be running (script runs pipeline directly)
