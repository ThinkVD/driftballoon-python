# DriftBalloon Integration Prompts

Ready-to-use prompts for AI coding assistants (Claude Code, Cursor, Copilot, etc.)

## Prompt 1: SDK Integration (Recommended)

Copy and paste this prompt to your AI assistant:

```
Add DriftBalloon drift detection to my LLM application.

DriftBalloon is installed via: pip install driftballoon

1. Initialize the client at app startup:
from driftballoon import DriftBalloon
import os
db = DriftBalloon(api_key=os.environ["DRIFTBALLOON_API_KEY"])

2. After each LLM call, log the response (fire-and-forget):
db.log(name="my-prompt-name", response=llm_response_text, model="gpt-4").submit()

3. Optionally check which prompt version is active:
active = db.get_active_prompt("my-prompt-name")

Find all LLM calls in my codebase and add the appropriate db.log().submit() call after each one.
Prompts are auto-created on the server when first logged — no registration step needed.
```

## Prompt 2: Scan Codebase for LLM Calls

```
Scan my codebase and list all files that make LLM API calls.

Look for these patterns:
- OpenAI: client.chat.completions.create, ChatCompletion.create, from openai
- Anthropic: client.messages.create, from anthropic
- LangChain: ChatOpenAI, ChatAnthropic, LLMChain, .invoke(, from langchain
- LlamaIndex: query_engine.query, index.as_query_engine, from llama_index

For each file found, show the file path, line numbers, and the type of LLM call.
```

## Prompt 3: Add Environment Variable

```
Add DRIFTBALLOON_API_KEY to my environment configuration.

Find where environment variables are configured (e.g., .env, .env.example, docker-compose.yml, etc.) and add:

DRIFTBALLOON_API_KEY=db_sk_your_api_key_here

Also update any environment documentation or setup instructions.
```

## Usage Tips

1. **Start with Prompt 2** to understand where LLM calls exist in your codebase
2. **Use Prompt 1** to integrate DriftBalloon logging after each LLM call
3. **Use Prompt 3** to set up the API key configuration

## After Integration

Once DriftBalloon is integrated:
- LLM responses are logged via `db.log().submit()` (fire-and-forget)
- Baseline is established after ~30 logged responses
- Drift detection activates automatically
- View drift events at https://driftballoon.com/dashboard
