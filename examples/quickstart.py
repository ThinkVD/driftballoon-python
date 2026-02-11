#!/usr/bin/env python3
"""Quick smoke test for the DriftBalloon SDK against a local backend.

Usage:
    DRIFTBALLOON_API_KEY=db_sk_xxx python examples/quickstart.py
"""

import os
import sys
import time

from driftballoon import DriftBalloon

api_key = os.environ.get("DRIFTBALLOON_API_KEY")
if not api_key:
    sys.exit("Set DRIFTBALLOON_API_KEY before running this script.")

base_url = os.environ.get("DRIFTBALLOON_BASE_URL", "http://localhost:8000")

with DriftBalloon(api_key=api_key, base_url=base_url, sync_interval=5.0) as db:
    prompts = ["Tell me a joke", "Summarize this article", "Translate to French"]
    for i, prompt in enumerate(prompts):
        db.log(name="quickstart-test", response=f"Simulated response {i}", prompt=prompt, model="gpt-4").submit()
        print(f"Logged response {i}")

    print("Waiting for background flush...")
    time.sleep(6)

    db._sync_config()
    status, count = db.get_baseline_status("quickstart-test")
    active = db.get_active_prompt("quickstart-test")
    print(f"Prompt 'quickstart-test': active={active}, baseline={status}, samples={count}")

print("Done.")
