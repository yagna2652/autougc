# LLM Observability with LangSmith

This guide explains how to set up full prompt observability for the AutoUGC pipeline using LangSmith.

## Why Observability Matters for AI-Native Apps

When building AI-native applications with many LLM calls, you need to see:
- **Every prompt** sent to each model
- **Every response** received
- **Token usage** and costs
- **Latency** for each call
- **Full pipeline traces** showing how data flows through your system

Without this visibility, debugging becomes guesswork.

## Quick Setup (5 minutes)

### 1. Create a LangSmith Account

Go to [smith.langchain.com](https://smith.langchain.com) and sign up (free tier is sufficient).

### 2. Get Your API Key

1. Click your profile → "API Keys"
2. Create a new API key
3. Copy it

### 3. Set Environment Variables

Add these to your `.env` file:

```bash
# Enable LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_api_key_here
LANGCHAIN_PROJECT=autougc-pipeline
```

### 4. Restart Your Server

```bash
./stop-dev.sh && ./start-dev.sh
```

That's it! All LLM calls will now be traced.

## Viewing Your Traces

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Select the "autougc-pipeline" project
3. Click on any run to see:
   - Full input prompts
   - Model responses
   - Token counts
   - Latency
   - Nested sub-calls

## What Gets Traced

### Automatically Traced Components

Components that use `TracedAnthropicClient`:
- `StructureParser` - Video structure analysis prompts
- (More components can be added)

### Pipeline-Level Tracing

The LangGraph pipeline automatically creates traces for:
- Each node execution
- State transitions
- The full pipeline run

## Adding Tracing to New Components

### Option 1: Use TracedAnthropicClient

Replace your Anthropic client with the traced version:

```python
from src.tracing import TracedAnthropicClient, is_tracing_enabled

# In your __init__:
if is_tracing_enabled():
    self.client = TracedAnthropicClient(
        api_key=api_key,
        trace_name="my_component"  # This appears in LangSmith
    )
else:
    self.client = anthropic.Anthropic(api_key=api_key)

# Use exactly as before:
response = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{"role": "user", "content": prompt}]
)
```

### Option 2: Use Function Decorators

For non-LLM functions you want to trace:

```python
from src.tracing import trace_function, trace_chain

@trace_function(name="analyze_frames")
def analyze_frames(frames: list) -> dict:
    # Your code here
    return results

# Or for chain-like operations:
@trace_chain(name="process_video")
def process_video(video_url: str) -> dict:
    # Your code here
    return results
```

### Option 3: Use Context Managers

For more granular control:

```python
from src.tracing import trace_span

with trace_span("download_video", inputs={"url": video_url}) as span:
    video_path = download_video(video_url)
    span.set_outputs({"path": str(video_path)})
```

## Understanding the LangSmith UI

### Projects View
- Lists all your projects (e.g., "autougc-pipeline")
- Shows run counts and error rates

### Runs View
- Each row is a pipeline execution
- Click to expand and see all nested calls
- Filter by status, date, or tags

### Run Details
- **Input**: The exact prompt/messages sent
- **Output**: The model's response
- **Metadata**: Model name, tokens, latency
- **Child Runs**: Nested calls within this run

## Cost Tracking

LangSmith shows token usage for each call. To estimate costs:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| claude-sonnet-4-20250514 | $3.00 | $15.00 |
| claude-3-5-haiku | $0.25 | $1.25 |

## Debugging Tips

### Finding Failed Runs
1. In LangSmith, filter by "Status: Error"
2. Click on the failed run
3. Expand to find the exact call that failed
4. View the full prompt and error message

### Comparing Prompts
1. Find two runs you want to compare
2. Open them in separate tabs
3. Compare the input prompts side-by-side

### Prompt Iteration Workflow
1. Run your pipeline
2. Find the trace in LangSmith
3. Copy the prompt that needs improvement
4. Edit in your code
5. Re-run and compare outputs

## Local Development (Without LangSmith)

If you don't want to use LangSmith, you can still log prompts locally:

```python
from src.tracing import log_prompt_to_console

# Manually log a prompt:
log_prompt_to_console(
    prompt="Your prompt here",
    response="Model response",
    model="claude-sonnet-4-20250514",
    component="structure_parser"
)
```

Or just don't set `LANGCHAIN_TRACING_V2=true` - all tracing code becomes no-ops.

## Troubleshooting

### Traces Not Appearing
1. Check `LANGCHAIN_TRACING_V2=true` is set
2. Check `LANGCHAIN_API_KEY` is valid
3. Check network connectivity to smith.langchain.com
4. Look for errors in your server logs

### Incomplete Traces
- Make sure components are using `TracedAnthropicClient`
- Check that async calls are properly awaited

### High Latency
- LangSmith adds <5ms overhead per call
- If you see higher latency, check network connectivity

## Best Practices

1. **Name your traces descriptively** - Use component names like `structure_parser`, `mechanics_generator`
2. **Add metadata** - Include useful context like video IDs, user IDs
3. **Review regularly** - Check traces after each development session
4. **Compare before/after** - When changing prompts, compare trace outputs
5. **Monitor costs** - Use LangSmith's token counts to track spending

## Further Reading

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangGraph Tracing](https://langchain-ai.github.io/langgraph/how-tos/tracing/)
- [Best Practices for LLM Observability](https://docs.smith.langchain.com/observability)