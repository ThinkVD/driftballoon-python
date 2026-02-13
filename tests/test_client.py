"""Tests for DriftBalloon SDK client."""

import pytest
from unittest.mock import patch

import httpx
import respx

from driftballoon import DriftBalloon
from driftballoon.client import QueuedLog, PromptConfig, LogTask


class TestDriftBalloonInit:
    """Tests for DriftBalloon initialization."""

    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        with patch.object(DriftBalloon, 'start'):
            db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
            assert db.api_key == "db_sk_test1234567890ab"
            assert db.base_url == DriftBalloon.DEFAULT_BASE_URL

    def test_init_with_invalid_api_key(self):
        """Test initialization with invalid API key raises error."""
        with pytest.raises(ValueError, match="Invalid API key format"):
            DriftBalloon(api_key="invalid_key")

    def test_init_with_empty_api_key(self):
        """Test initialization with empty API key raises error."""
        with pytest.raises(ValueError, match="Invalid API key format"):
            DriftBalloon(api_key="")

    def test_init_with_custom_base_url(self):
        """Test initialization with custom base URL."""
        with patch.object(DriftBalloon, 'start'):
            db = DriftBalloon(
                api_key="db_sk_test1234567890ab",
                base_url="https://custom.api.com/",
                auto_start=False
            )
            assert db.base_url == "https://custom.api.com"  # Trailing slash removed

    def test_init_auto_start_disabled(self):
        """Test that auto_start=False prevents background thread start."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        assert db._running is False
        assert db._sync_thread is None


class TestLog:
    """Tests for log submission."""

    def test_log_returns_log_task(self):
        """Test that log() returns a LogTask."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)

        task = db.log(name="test-prompt", response="Test response", prompt="Test input", model="gpt-4")

        assert isinstance(task, LogTask)
        assert len(db._log_queue) == 0  # Not queued until .submit()

    def test_submit_queues_entry(self):
        """Test that .submit() adds entry to queue."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)

        db.log(name="test-prompt", response="Test response", prompt="Test input", model="gpt-4").submit()

        assert len(db._log_queue) == 1
        assert db._log_queue[0].data["prompt_name"] == "test-prompt"
        assert db._log_queue[0].data["response_text"] == "Test response"
        assert db._log_queue[0].data["input_text"] == "Test input"
        assert db._log_queue[0].data["model"] == "gpt-4"

    def test_submit_multiple_entries(self):
        """Test submitting multiple entries."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)

        db.log(name="prompt1", response="Response 1", prompt="Input 1", model="gpt-4").submit()
        db.log(name="prompt2", response="Response 2", prompt="Input 2", model="gpt-4").submit()
        db.log(name="prompt1", response="Response 3", prompt="Input 3", model="gpt-4").submit()

        assert len(db._log_queue) == 3

    @respx.mock
    def test_invoke_sends_synchronously(self, respx_mock):
        """Test that .invoke() sends the log synchronously."""
        route = respx_mock.post("https://server.driftballoon.com/api/v1/logs").mock(
            return_value=httpx.Response(202, json={"status": "accepted", "count": 1})
        )

        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db.log(name="test-prompt", response="Sync response", prompt="Sync input", model="gpt-4").invoke()

        assert route.called
        assert len(db._log_queue) == 0  # Not queued — sent directly


class TestGetActivePrompt:
    """Tests for get_active_prompt."""

    def test_get_active_prompt_returns_a(self):
        """Test getting active prompt when A is active."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._config_cache["test"] = PromptConfig(
            name="test",
            active_prompt="a"
        )

        result = db.get_active_prompt("test")
        assert result == "a"

    def test_get_active_prompt_returns_b(self):
        """Test getting active prompt when B is active."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._config_cache["test"] = PromptConfig(
            name="test",
            active_prompt="b"
        )

        result = db.get_active_prompt("test")
        assert result == "b"

    def test_get_active_prompt_not_found(self):
        """Test get_active_prompt returns None for unknown prompt."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)

        result = db.get_active_prompt("unknown")
        assert result is None


class TestGetBaselineStatus:
    """Tests for get_baseline_status."""

    def test_baseline_learning(self):
        """Test baseline status when learning."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._config_cache["test"] = PromptConfig(
            name="test",
            baseline_status="learning",
            baseline_sample_count=15
        )

        status, count = db.get_baseline_status("test")
        assert status == "learning"
        assert count == 15

    def test_baseline_ready(self):
        """Test baseline status when ready."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._config_cache["test"] = PromptConfig(
            name="test",
            baseline_status="ready",
            baseline_sample_count=50
        )

        status, count = db.get_baseline_status("test")
        assert status == "ready"
        assert count == 50

    def test_baseline_not_found(self):
        """Test baseline status for unknown prompt."""
        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)

        status, count = db.get_baseline_status("unknown")
        assert status == "learning"
        assert count == 0


class TestConfigSync:
    """Tests for config synchronization."""

    @respx.mock
    def test_sync_config_updates_cache(self, respx_mock):
        """Test that _sync_config updates local cache."""
        respx_mock.get("https://server.driftballoon.com/api/v1/config").mock(
            return_value=httpx.Response(200, json={
                "prompts": {
                    "test-prompt": {
                        "active_prompt": "b",
                        "baseline_status": "ready",
                        "baseline_sample_count": 50,
                        "min_baseline_samples": 30,
                        "drift_threshold": 0.8,
                        "length_drift_threshold": 2.0,
                        "auto_switch_enabled": False,
                        "status": "active",
                    }
                },
                "cache_ttl_seconds": 30
            })
        )

        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._config_cache["test-prompt"] = PromptConfig(
            name="test-prompt",
            active_prompt="a"
        )

        db._sync_config()

        config = db._config_cache["test-prompt"]
        assert config.active_prompt == "b"
        assert config.baseline_status == "ready"
        assert config.baseline_sample_count == 50

    @respx.mock
    def test_sync_config_adds_new_prompts(self, respx_mock):
        """Test that _sync_config adds new prompts to cache."""
        respx_mock.get("https://server.driftballoon.com/api/v1/config").mock(
            return_value=httpx.Response(200, json={
                "prompts": {
                    "new-prompt": {
                        "active_prompt": "a",
                        "baseline_status": "learning",
                        "baseline_sample_count": 10,
                        "min_baseline_samples": 30,
                        "drift_threshold": 0.7,
                        "length_drift_threshold": 1.5,
                        "auto_switch_enabled": True,
                        "status": "active",
                    }
                },
                "cache_ttl_seconds": 30
            })
        )

        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        assert "new-prompt" not in db._config_cache

        db._sync_config()

        assert "new-prompt" in db._config_cache
        config = db._config_cache["new-prompt"]
        assert config.active_prompt == "a"
        assert config.baseline_sample_count == 10

    @respx.mock
    def test_sync_config_handles_server_error(self, respx_mock):
        """Test that _sync_config handles server errors gracefully."""
        respx_mock.get("https://server.driftballoon.com/api/v1/config").mock(
            return_value=httpx.Response(500)
        )

        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._config_cache["test-prompt"] = PromptConfig(
            name="test-prompt",
            active_prompt="a"
        )

        # Should not raise, should keep cached config
        db._sync_config()

        config = db._config_cache["test-prompt"]
        assert config.active_prompt == "a"  # Unchanged


class TestFlushLogs:
    """Tests for log flushing."""

    @respx.mock
    def test_flush_logs_sends_batch(self, respx_mock):
        """Test that _flush_logs sends queued logs."""
        respx_mock.post("https://server.driftballoon.com/api/v1/logs").mock(
            return_value=httpx.Response(202, json={
                "status": "accepted",
                "count": 2,
                "log_ids": ["id1", "id2"]
            })
        )

        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._log_queue = [
            QueuedLog(data={"prompt_name": "test", "response_text": "Response 1"}),
            QueuedLog(data={"prompt_name": "test", "response_text": "Response 2"}),
        ]

        db._flush_logs()

        assert len(db._log_queue) == 0

    @respx.mock
    def test_flush_logs_requeues_on_rate_limit(self, respx_mock):
        """Test that _flush_logs requeues on 429."""
        respx_mock.post("https://server.driftballoon.com/api/v1/logs").mock(
            return_value=httpx.Response(429, json={"error": "Rate limited"})
        )

        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._log_queue = [
            QueuedLog(data={"prompt_name": "test", "response_text": "Response 1"}),
        ]

        db._flush_logs()

        # Should be requeued
        assert len(db._log_queue) == 1

    @respx.mock
    def test_flush_logs_retries_and_drops(self, respx_mock):
        """Test that _flush_logs retries up to max_retries then drops."""
        respx_mock.post("https://server.driftballoon.com/api/v1/logs").mock(
            return_value=httpx.Response(500)
        )

        db = DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False)
        db._log_queue = [
            QueuedLog(data={"prompt_name": "test", "response_text": "Response 1"}, retry_count=4, max_retries=5),
        ]

        db._flush_logs()

        # Should be dropped after max retries
        assert len(db._log_queue) == 0


class TestContextManager:
    """Tests for context manager usage."""

    def test_context_manager_stops_on_exit(self):
        """Test that context manager stops client on exit."""
        with DriftBalloon(api_key="db_sk_test1234567890ab", auto_start=False) as db:
            db.start()
            assert db._running is True

        assert db._running is False


class TestQueuedLog:
    """Tests for QueuedLog dataclass."""

    def test_queued_log_defaults(self):
        """Test QueuedLog default values."""
        log = QueuedLog(data={"test": "data"})

        assert log.data == {"test": "data"}
        assert log.retry_count == 0
        assert log.max_retries == 5


class TestPromptConfig:
    """Tests for PromptConfig dataclass."""

    def test_prompt_config_defaults(self):
        """Test PromptConfig default values."""
        config = PromptConfig(name="test")

        assert config.name == "test"
        assert config.active_prompt == "a"
        assert config.baseline_status == "learning"
        assert config.baseline_sample_count == 0
        assert config.min_baseline_samples == 30
        assert config.drift_threshold == 0.7
        assert config.length_drift_threshold == 1.5
        assert config.auto_switch_enabled is True
        assert config.status == "active"
