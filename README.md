# DriftBalloon Python SDK

[![PyPI version](https://img.shields.io/pypi/v/driftballoon.svg)](https://pypi.org/project/driftballoon/)
[![Python](https://img.shields.io/pypi/pyversions/driftballoon.svg)](https://pypi.org/project/driftballoon/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

LLM output drift detection and observability. One line of logging — DriftBalloon stays completely out of your critical path.

## Install

```bash
pip install driftballoon
```

## Quickstart

```python
from driftballoon import DriftBalloon

db = DriftBalloon(api_key="db_sk_your_key")

# After each LLM call, log the response (fire-and-forget)
response = openai.chat.completions.create(model="gpt-4o", messages=[...])
db.log(
    name="support-agent",
    response=response.choices[0].message.content,
    model="gpt-4o",
).submit()

# Check which prompt version is active ("a" or "b")
active = db.get_active_prompt("support-agent")
```

## Features

- **Fire-and-forget logging** — `log().submit()` is non-blocking; your app never waits on DriftBalloon
- **Semantic drift detection** — detects when LLM responses shift meaning or topic
- **Length drift detection** — catches abnormally short or long responses
- **Prompt status tracking** — check which prompt version is active via `get_active_prompt()`
- **Multi-model support** — track `gpt-4o`, `claude-3-5-sonnet`, or any model string
- **Local config cache** — prompt configs are cached and synced every 30s
- **Offline resilience** — your app keeps working if DriftBalloon is unreachable
- **Retry with backoff** — failed log submissions are retried automatically

## Environment Variables

```bash
export DRIFTBALLOON_API_KEY=db_sk_your_key
```

```python
import os
from driftballoon import DriftBalloon

db = DriftBalloon(api_key=os.environ["DRIFTBALLOON_API_KEY"])
```

For self-hosted deployments, set the base URL:

```python
db = DriftBalloon(api_key="db_sk_xxx", base_url="https://driftballoon.your-company.com")
```

## API Reference

### `DriftBalloon(api_key, base_url=None, sync_interval=30.0, auto_start=True)`

Initialize the client. Can be used as a context manager.

### `log(name, response, prompt=None, model=None) -> LogTask`

Log an LLM response. Call `.submit()` (async, fire-and-forget) or `.invoke()` (synchronous).

### `get_active_prompt(name) -> "a" | "b" | None`

Get the active prompt version from cached config.

### `get_config(name) -> PromptConfig | None`

Get the full prompt configuration.

### `get_baseline_status(name) -> (status, count)`

Check if the baseline is ready (`"learning"` or `"ready"`) and how many samples have been collected.

## Documentation

Full docs at [docs.driftballoon.com](https://docs.driftballoon.com).

## Local Development

```bash
# Setup
make install

# Unit tests (no backend required)
make test

# Integration tests (requires running API)
make test-integration

# Quickstart smoke test
DRIFTBALLOON_API_KEY=db_sk_xxx python examples/quickstart.py

# Cross-venv testing from repo root
make sdk-test-local KEY=db_sk_xxx
```

## License

MIT
