"""Integration tests for DriftBalloon SDK against a live local backend.

Run with:  pytest -m integration -v
Requires:  a running local backend (e.g. `make api` from the repo root)
"""

import time

import pytest

from driftballoon import DriftBalloon

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Log round-trip
# ---------------------------------------------------------------------------

class TestSDKLogRoundTrip:
    """Verify that logs reach the backend and the queue drains."""

    def test_log_single_entry(self, test_api_key: str, backend_url: str):
        db = DriftBalloon(
            api_key=test_api_key,
            base_url=backend_url,
            auto_start=False,
        )
        db.log(name="integ-log-single", response="Hello from integration test").submit()
        assert len(db._log_queue) == 1

        db._flush_logs()
        assert len(db._log_queue) == 0

    def test_log_batch(self, test_api_key: str, backend_url: str):
        db = DriftBalloon(
            api_key=test_api_key,
            base_url=backend_url,
            auto_start=False,
        )
        for i in range(5):
            db.log(name="integ-log-batch", response=f"Batch response {i}").submit()
        assert len(db._log_queue) == 5

        db._flush_logs()
        assert len(db._log_queue) == 0

    def test_background_flush(self, test_api_key: str, backend_url: str):
        db = DriftBalloon(
            api_key=test_api_key,
            base_url=backend_url,
            sync_interval=1.0,
            auto_start=True,
        )
        try:
            for i in range(3):
                db.log(name="integ-log-bg", response=f"BG response {i}").submit()

            # Wait long enough for at least one background cycle
            time.sleep(2.5)
            assert len(db._log_queue) == 0
        finally:
            db.stop()


# ---------------------------------------------------------------------------
# Config sync
# ---------------------------------------------------------------------------

class TestSDKConfigSync:
    """Verify config sync pulls real data from the backend."""

    def test_sync_config(self, test_api_key: str, backend_url: str):
        db = DriftBalloon(
            api_key=test_api_key,
            base_url=backend_url,
            auto_start=False,
        )
        # Log once so the prompt exists server-side
        db.log(name="integ-config-sync", response="seed log").invoke()

        db._sync_config()

        config = db.get_config("integ-config-sync")
        assert config is not None
        assert config.name == "integ-config-sync"

    def test_get_active_prompt(self, test_api_key: str, backend_url: str):
        db = DriftBalloon(
            api_key=test_api_key,
            base_url=backend_url,
            auto_start=False,
        )
        db.log(name="integ-active-prompt", response="seed log").invoke()
        db._sync_config()

        active = db.get_active_prompt("integ-active-prompt")
        assert active == "a"

    def test_get_baseline_status(self, test_api_key: str, backend_url: str):
        db = DriftBalloon(
            api_key=test_api_key,
            base_url=backend_url,
            auto_start=False,
        )
        db.log(name="integ-baseline", response="seed log").invoke()
        db._sync_config()

        status, count = db.get_baseline_status("integ-baseline")
        assert status == "learning"
        assert count < 30


# ---------------------------------------------------------------------------
# Context manager lifecycle
# ---------------------------------------------------------------------------

class TestSDKContextManager:
    """Verify the with-statement lifecycle."""

    def test_full_lifecycle(self, test_api_key: str, backend_url: str):
        with DriftBalloon(
            api_key=test_api_key,
            base_url=backend_url,
            sync_interval=1.0,
            auto_start=True,
        ) as db:
            db.log(name="integ-lifecycle", response="lifecycle test").submit()
            time.sleep(2.0)
            assert len(db._log_queue) == 0

        # After exiting, background thread should be stopped
        assert db._running is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestSDKErrorHandling:
    """Verify graceful degradation with bad credentials."""

    def test_invalid_key_graceful(self, backend_url: str):
        db = DriftBalloon(
            api_key="db_sk_invalid_key_for_testing",
            base_url=backend_url,
            auto_start=False,
        )
        db.log(name="integ-bad-key", response="should not crash").submit()
        # Flush should not raise even with an invalid key
        db._flush_logs()
