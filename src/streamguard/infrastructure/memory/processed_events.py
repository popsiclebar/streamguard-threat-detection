"""In-memory processed-event repository for StreamGuard idempotency.

Processed-event markers map an input event ID to the detection result that was
already produced for it.
"""

from uuid import UUID


class InMemoryProcessedEventRepository:
    """Store processed event markers inside the current Python process."""

    def __init__(self) -> None:
        """Create an empty event-to-detection marker store."""
        self._event_to_detection: dict[UUID, UUID] = {}

    def get_detection_id(self, event_id: UUID) -> UUID | None:
        """Return the detection ID previously produced for an event ID."""
        return self._event_to_detection.get(event_id)

    def mark_processed(self, event_id: UUID, detection_id: UUID) -> None:
        """Remember which detection ID was produced for one event ID."""
        self._event_to_detection[event_id] = detection_id
