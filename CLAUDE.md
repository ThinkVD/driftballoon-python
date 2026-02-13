# DriftBalloon Integration Guide for Claude Code

## What is DriftBalloon?

DriftBalloon is a log-only LLM output drift detection SDK. It monitors your LLM outputs for semantic and length drift. DriftBalloon stays completely out of the critical path -- developers call `db.log(...).submit()` (fire-and-forget) or `db.log(...).invoke()` (synchronous) after their LLM calls.

## When to Use DriftBalloon

Add DriftBalloon when the user wants to:
- Monitor LLM outputs for quality/consistency
- Detect when an LLM's behavior changes over time
- Check which prompt version is active (configured via the dashboard)
- Track prompt performance in production

## Integration Pattern

```python
from driftballoon import DriftBalloon

# Initialize once at app startup
db = DriftBalloon(api_key="db_sk_xxx")

# After each LLM call, log the response
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": user_input}]
)
db.log(name="my-prompt", response=response.choices[0].message.content, prompt=user_input, model="gpt-4").submit()

# Optionally check which prompt version is active ("a" or "b")
active = db.get_active_prompt("my-prompt")
```

## Step-by-Step Integration

### Step 1: Install the SDK
```bash
pip install driftballoon
```

### Step 2: Get API Key
Get your API key from https://driftballoon.com/dashboard

### Step 3: Add Logging
1. Initialize DriftBalloon client at app startup
2. Add `db.log()` calls after each LLM response
3. Prompts are auto-created on the server when first logged

### Step 4: Verify Integration
```python
# Check baseline status
status, count = db.get_baseline_status("my-prompt")
print(f"Baseline: {status}, samples: {count}")
```

## Environment Variables

```bash
DRIFTBALLOON_API_KEY=db_sk_xxx
DRIFTBALLOON_BASE_URL=https://server.driftballoon.com  # optional
```

## Common Integration Locations

When integrating DriftBalloon, look for:
1. **Service/client initialization files** - Add DriftBalloon client init
2. **LLM wrapper/utility files** - Add logging after LLM calls
3. **API route handlers** - If LLM calls happen in routes
4. **Background task handlers** - For async LLM processing

## Best Practices

1. **Initialize once**: Create DriftBalloon client at app startup, not per-request
2. **Use meaningful names**: `"user-support-summarizer"` not `"prompt1"`
3. **Log every response**: Drift detection needs consistent logging
4. **Configure in dashboard**: Set up prompt A/B and thresholds via the web UI
5. **Wait for baseline**: Detection activates after ~30 samples

## Troubleshooting

### "Logs not appearing"
- Verify API key starts with `db_sk_`
- Check network access to server.driftballoon.com
- Logs are async; wait 10-30 seconds

### "Drift not detected"
- Check `get_baseline_status()` - need 30+ samples
- Verify logging is happening on every call
