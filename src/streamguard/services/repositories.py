"""Repository interfaces used by StreamGuard services.

Repository protocols define what application services need from storage without
coupling those services to a specific database. The first implementation is
in-memory; a later milestone can add Redis behind the same interface.
"""

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


class ProcessedEventRepository(Protocol):
    """Storage interface for event idempotency markers.

    Idempotency means repeated submissions of the same event ID should not create
    duplicate detections while the processed marker is still retained.
    """

    def get_detection_id(self, event_id: UUID) -> UUID | None:
        """Return the detection ID previously produced for an event, if any."""

    def mark_processed(self, event_id: UUID, detection_id: UUID) -> None:
        """Remember which detection ID was produced for an event ID."""
