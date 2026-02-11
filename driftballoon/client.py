"""DriftBalloon SDK client for LLM output drift detection."""

import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class QueuedLog:
    """A log entry queued for submission."""
    data: dict
    retry_count: int = 0
    max_retries: int = 5


@dataclass
class PromptConfig:
    """Configuration for a prompt."""
    name: str
    active_prompt: str = "a"
    baseline_status: str = "learning"
    baseline_sample_count: int = 0
    min_baseline_samples: int = 30
    drift_threshold: float = 0.7
    length_drift_threshold: float = 1.5
    auto_switch_enabled: bool = True
    status: str = "active"


class LogTask:
    """A pending log operation. Call .invoke() or .submit() to execute."""

    def __init__(self, client: "DriftBalloon", data: dict):
        self._client = client
        self._data = data

    def invoke(self) -> None:
        """Send the log synchronously (blocks until the server responds)."""
        self._client._send_log_sync(self._data)

    def submit(self) -> None:
        """Queue the log for background submission (fire-and-forget)."""
        entry = QueuedLog(data=self._data)
        with self._client._queue_lock:
            self._client._log_queue.append(entry)


class DriftBalloon:
    """
    DriftBalloon SDK client.

    Features:
    - Local-first config cache with 30s sync
    - Offline queue for log submission
    - Fire-and-forget logging
    - Graceful degradation when server unavailable

    Usage:
        db = DriftBalloon(api_key="db_sk_xxxx")

        # After each LLM call — fire-and-forget
        db.log(name="summarizer", response=response, prompt=prompt).submit()

        # Or block until the server confirms receipt
        db.log(name="summarizer", response=response, prompt=prompt).invoke()

        # Get current active prompt version ("a" or "b")
        active = db.get_active_prompt("summarizer")
    """

    DEFAULT_BASE_URL = "https://api.driftballoon.com"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        sync_interval: float = 30.0,
        auto_start: bool = True,
    ):
        """
        Initialize DriftBalloon client.

        Args:
            api_key: Your DriftBalloon API key (starts with db_sk_)
            base_url: API base URL (defaults to https://api.driftballoon.com)
            sync_interval: Config sync interval in seconds (default 30)
            auto_start: Start background sync automatically (default True)
        """
        if not api_key or not api_key.startswith("db_sk_"):
            raise ValueError("Invalid API key format. Must start with 'db_sk_'")

        self.api_key = api_key
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._sync_interval = sync_interval

        # Local config cache
        self._config_cache: dict[str, PromptConfig] = {}
        self._config_lock = threading.Lock()

        # Log queue
        self._log_queue: list[QueuedLog] = []
        self._queue_lock = threading.Lock()

        # Background sync
        self._running = False
        self._sync_thread: threading.Thread | None = None

        # HTTP client
        self._http_client: httpx.Client | None = None

        if auto_start:
            self.start()

    @property
    def http_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=10.0,
                headers={"X-API-Key": self.api_key},
            )
        return self._http_client

    def start(self):
        """Start background sync thread."""
        if self._running:
            return

        self._running = True
        self._sync_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._sync_thread.start()
        logger.debug("DriftBalloon background sync started")

    def stop(self):
        """Stop background sync and flush remaining logs."""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)
        self._flush_logs()

        if self._http_client:
            self._http_client.close()
            self._http_client = None

    def log(
        self,
        name: str,
        response: str,
        prompt: str | None = None,
        model: str | None = None,
    ) -> LogTask:
        """
        Log an LLM response for drift detection.

        Returns a LogTask — call .submit() for fire-and-forget or
        .invoke() to block until the server confirms receipt.

        Args:
            name: Name of the prompt
            response: The LLM response text
            prompt: The input prompt (optional, for reference)
            model: The LLM model used (optional)

        Returns:
            LogTask with .invoke() and .submit() methods
        """
        data = {
            "prompt_name": name,
            "response_text": response,
            "input_text": prompt,
            "model": model,
        }
        return LogTask(self, data)

    def get_active_prompt(self, name: str) -> str | None:
        """
        Get the currently active prompt version.

        Returns "a" or "b" based on which prompt version is currently active
        (may have been auto-switched due to drift).

        Args:
            name: Name of the prompt

        Returns:
            "a" or "b", or None if not found
        """
        with self._config_lock:
            config = self._config_cache.get(name)

        if not config:
            return None

        return config.active_prompt

    def get_config(self, name: str) -> PromptConfig | None:
        """
        Get the full configuration for a prompt.

        Args:
            name: Name of the prompt

        Returns:
            PromptConfig or None if not found
        """
        with self._config_lock:
            return self._config_cache.get(name)

    def get_baseline_status(self, name: str) -> tuple[str, int]:
        """
        Get the baseline learning status for a prompt.

        Args:
            name: Name of the prompt

        Returns:
            Tuple of (status: "learning"|"ready", sample_count)
        """
        with self._config_lock:
            config = self._config_cache.get(name)

        if not config:
            return ("learning", 0)

        return (config.baseline_status, config.baseline_sample_count)

    def _send_log_sync(self, data: dict) -> None:
        """Send a single log entry synchronously."""
        self.http_client.post(
            f"{self.base_url}/api/v1/logs",
            json={"logs": [data]},
        )

    def _background_worker(self):
        """Background thread for config sync and log submission."""
        while self._running:
            try:
                self._sync_config()
                self._flush_logs()
            except Exception as e:
                logger.error(f"Background worker error: {e}")

            time.sleep(self._sync_interval)

    def _sync_config(self):
        """Fetch latest config from server and populate cache for all prompts."""
        try:
            response = self.http_client.get(
                f"{self.base_url}/api/v1/config",
            )

            if response.status_code == 200:
                data = response.json()
                prompts = data.get("prompts", {})

                with self._config_lock:
                    for name, config_data in prompts.items():
                        if name in self._config_cache:
                            # Update existing cached prompt
                            existing = self._config_cache[name]
                            existing.active_prompt = config_data.get("active_prompt", existing.active_prompt)
                            existing.baseline_status = config_data.get("baseline_status", existing.baseline_status)
                            existing.baseline_sample_count = config_data.get("baseline_sample_count", existing.baseline_sample_count)
                            existing.min_baseline_samples = config_data.get("min_baseline_samples", existing.min_baseline_samples)
                            existing.drift_threshold = config_data.get("drift_threshold", existing.drift_threshold)
                            existing.length_drift_threshold = config_data.get("length_drift_threshold", existing.length_drift_threshold)
                            existing.auto_switch_enabled = config_data.get("auto_switch_enabled", existing.auto_switch_enabled)
                            existing.status = config_data.get("status", existing.status)
                        else:
                            # Add new prompt to cache
                            self._config_cache[name] = PromptConfig(
                                name=name,
                                active_prompt=config_data.get("active_prompt", "a"),
                                baseline_status=config_data.get("baseline_status", "learning"),
                                baseline_sample_count=config_data.get("baseline_sample_count", 0),
                                min_baseline_samples=config_data.get("min_baseline_samples", 30),
                                drift_threshold=config_data.get("drift_threshold", 0.7),
                                length_drift_threshold=config_data.get("length_drift_threshold", 1.5),
                                auto_switch_enabled=config_data.get("auto_switch_enabled", True),
                                status=config_data.get("status", "active"),
                            )

                logger.debug("Config synced from server")

        except Exception as e:
            logger.debug(f"Config sync failed (using cached): {e}")

    def _flush_logs(self):
        """Send queued logs to server with batching."""
        MAX_BATCH_SIZE = 50  # Cap per cycle
        BATCH_POST_SIZE = 10  # Logs per HTTP request

        with self._queue_lock:
            to_process = self._log_queue[:MAX_BATCH_SIZE]
            self._log_queue = self._log_queue[MAX_BATCH_SIZE:]

        if not to_process:
            return

        remaining: list[QueuedLog] = []

        # Send logs in batches
        for i in range(0, len(to_process), BATCH_POST_SIZE):
            batch = to_process[i:i + BATCH_POST_SIZE]

            try:
                response = self.http_client.post(
                    f"{self.base_url}/api/v1/logs",
                    json={"logs": [item.data for item in batch]},
                )

                if response.status_code == 429:
                    # Rate limited - re-queue batch
                    remaining.extend(batch)
                elif response.status_code not in (200, 201, 202):
                    # Other error - retry with backoff
                    for item in batch:
                        item.retry_count += 1
                        if item.retry_count < item.max_retries:
                            remaining.append(item)

            except Exception as e:
                logger.debug(f"Log submission failed: {e}")
                for item in batch:
                    item.retry_count += 1
                    if item.retry_count < item.max_retries:
                        remaining.append(item)

        # Re-queue failed items
        if remaining:
            with self._queue_lock:
                self._log_queue = remaining + self._log_queue

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop background sync."""
        self.stop()
        return False
