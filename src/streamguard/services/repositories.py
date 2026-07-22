"""Repository interfaces used by StreamGuard services.

Repository protocols define what application services need from storage without
coupling those services to a specific database. Concrete adapters can store
recent operational state in memory or Redis and durable history in PostgreSQL.
"""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from streamguard.domain import DetectionResult


class AlertRepository(Protocol):
    """Storage interface for recent detection results.

    A Protocol is Python's structural interface: any object with these methods
    can be used as an alert repository, whether it stores data in memory, Redis,
    or another backend.
    """

    def save(self, result: DetectionResult) -> None:
        """Store one detection result."""

    def list_recent(
        self,
        *,
        limit: int = 100,
        minimum_score: float | None = None,
    ) -> list[DetectionResult]:
        """Return recent detections, newest first, with optional score filtering."""

    def get(self, detection_id: UUID) -> DetectionResult | None:
        """Return one detection result by ID, or None when it is absent."""


class DetectionHistoryRepository(Protocol):
    """Storage interface for durable detection-result history.

    This repository is separate from `AlertRepository` on purpose. Alerts are a
    short operational window for the API, while history is the long-lived record
    we can later query for dashboards, analytics, model evaluation, and audits.
    """

    def save_detection(self, result: DetectionResult) -> None:
        """Store one detection result durably."""

    def get_detection(self, detection_id: UUID) -> DetectionResult | None:
        """Return one durable detection result by ID, or None when absent."""

    def list_detections(
        self,
        *,
        limit: int = 100,
        minimum_score: float | None = None,
    ) -> list[DetectionResult]:
        """Return durable detections, newest first, with optional score filtering."""


class ProcessedEventRepository(Protocol):
    """Storage interface for event idempotency markers.

    Idempotency means repeated submissions of the same event ID should not create
    duplicate detections while the processed marker is still retained.
    """

    def get_detection_id(self, event_id: UUID) -> UUID | None:
        """Return the detection ID previously produced for an event, if any."""

    def mark_processed(self, event_id: UUID, detection_id: UUID) -> None:
        """Remember which detection ID was produced for an event ID."""


@dataclass(frozen=True)
class MetricsSnapshot:
    """Point-in-time operational counters for StreamGuard."""

    processed_total: int = 0
    anomalies_total: int = 0
    duplicates_total: int = 0
    invalid_total: int = 0
    failed_total: int = 0


class MetricsRepository(Protocol):
    """Storage interface for operational counters.

    Counters help local developers and future operators see what the service has
    done without reading logs or inspecting storage internals.
    """

    def increment_processed(self, *, is_anomaly: bool) -> None:
        """Record one newly processed detection result."""

    def increment_duplicate(self) -> None:
        """Record one idempotent duplicate event hit."""

    def increment_invalid(self) -> None:
        """Record one invalid event payload."""

    def increment_failed(self) -> None:
        """Record one failed processing attempt."""

    def snapshot(self) -> MetricsSnapshot:
        """Return current counter values."""
