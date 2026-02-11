# DriftBalloon Integration Prompts

Ready-to-use prompts for AI coding assistants (Claude Code, Cursor, Copilot, etc.)

## Prompt 1: Full Integration (Recommended)

Copy and paste this prompt to your AI assistant:

```
Add DriftBalloon drift detection to my LLM application.

DriftBalloon is installed via: pip install "driftballoon[wrappers]"

Find all LLM API calls in my codebase (OpenAI, Anthropic, LangChain, etc.) and:

1. For OpenAI calls: Replace `from openai import OpenAI` with `from driftballoon.wrappers.openai import OpenAI` and add `driftballoon_api_key=os.environ["DRIFTBALLOON_API_KEY"]` to the client initialization.

2. For Anthropic calls: Replace `from anthropic import Anthropic` with `from driftballoon.wrappers.anthropic import Anthropic` and add `driftballoon_api_key=os.environ["DRIFTBALLOON_API_KEY"]` to the client initialization.

3. For LangChain: Add `from driftballoon.wrappers.langchain import DriftBalloonCallbackHandler` and add `DriftBalloonCallbackHandler(api_key=os.environ["DRIFTBALLOON_API_KEY"])` to the callbacks.

This enables automatic drift detection for all LLM calls.
```

## Prompt 2: OpenAI Only

```
Add DriftBalloon to my OpenAI integration.

Replace:
from openai import OpenAI
client = OpenAI()

With:
from driftballoon.wrappers.openai import OpenAI
client = OpenAI(driftballoon_api_key=os.environ["DRIFTBALLOON_API_KEY"])

This wraps the OpenAI client to automatically log all LLM calls for drift detection.
Install with: pip install "driftballoon[wrappers]"
```

## Prompt 3: Anthropic Only

```
Add DriftBalloon to my Anthropic integration.

Replace:
from anthropic import Anthropic
client = Anthropic()

With:
from driftballoon.wrappers.anthropic import Anthropic
client = Anthropic(driftballoon_api_key=os.environ["DRIFTBALLOON_API_KEY"])

This wraps the Anthropic client to automatically log all LLM calls for drift detection.
Install with: pip install "driftballoon[wrappers]"
```

## Prompt 4: LangChain Only

```
Add DriftBalloon drift detection to my LangChain application.

Import and use the callback handler:
from driftballoon.wrappers.langchain import DriftBalloonCallbackHandler

handler = DriftBalloonCallbackHandler(api_key=os.environ["DRIFTBALLOON_API_KEY"])

Add this handler to your LLM's callbacks:
llm = ChatOpenAI(callbacks=[handler])
# or
chain.invoke(input, config={"callbacks": [handler]})

Install with: pip install "driftballoon[wrappers]"
```

## Prompt 5: Manual SDK Integration

```
Add DriftBalloon drift detection to my LLM application using the direct SDK.

1. Initialize at app startup:
from driftballoon import DriftBalloon
db = DriftBalloon(api_key=os.environ["DRIFTBALLOON_API_KEY"])

2. Register each prompt with a name:
db.register(
    name="my-prompt-name",
    prompt_a="The system prompt text",
    prompt_b="Optional fallback prompt"  # Used if drift detected
)

3. After each LLM call, log the response:
db.log(name="my-prompt-name", response=llm_response_text, model="gpt-4").submit()

Find all LLM calls and add the appropriate db.log().submit() call after each one.
Install with: pip install driftballoon
```

## Prompt 6: Scan Codebase for LLM Calls

```
Scan my codebase and list all files that make LLM API calls.

Look for these patterns:
- OpenAI: client.chat.completions.create, ChatCompletion.create, from openai
- Anthropic: client.messages.create, from anthropic
- LangChain: ChatOpenAI, ChatAnthropic, LLMChain, .invoke(, from langchain
- LlamaIndex: query_engine.query, index.as_query_engine, from llama_index

For each file found, show the file path, line numbers, and the type of LLM call.
```

## Prompt 7: Add Environment Variable

```
Add DRIFTBALLOON_API_KEY to my environment configuration.

Find where environment variables are configured (e.g., .env, .env.example, docker-compose.yml, etc.) and add:

DRIFTBALLOON_API_KEY=db_sk_your_api_key_here

Also update any environment documentation or setup instructions.
```

## Usage Tips

1. **Start with Prompt 6** to understand where LLM calls exist in your codebase
2. **Use Prompt 1** for comprehensive integration
3. **Use framework-specific prompts (2-4)** if you only use one LLM provider
4. **Use Prompt 5** if you need fine-grained control over what gets logged
5. **Use Prompt 7** to set up the API key configuration

## After Integration

Once DriftBalloon is integrated:
- LLM calls are automatically logged
- Baseline is established after ~30 calls
- Drift detection activates automatically
- View drift events at https://driftballoon.com/dashboard
