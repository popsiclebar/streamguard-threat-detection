"""In-memory infrastructure adapters for local StreamGuard development.

In-memory adapters are useful before external services exist because they let
the application exercise realistic boundaries while keeping tests fast and
deterministic. Data disappears when the Python process stops.
"""

from uuid import UUID

from streamguard.domain import DetectionResult


class InMemoryAlertRepository:
    """Store recent detection results inside the current Python process."""

    def __init__(self, max_results: int = 100) -> None:
        """Create an empty repository with a maximum number of retained results."""
        if max_results < 1:
            raise ValueError("max_results must be at least 1")
        self._max_results = max_results
        self._results: list[DetectionResult] = []

    def save(self, result: DetectionResult) -> None:
        """Store one result and trim older entries past the retention limit."""
        self._results.insert(0, result)
        del self._results[self._max_results :]

    def list_recent(
        self,
        *,
        limit: int = 100,
        minimum_score: float | None = None,
    ) -> list[DetectionResult]:
        """Return newest results first with optional anomaly-score filtering."""
        if limit < 1:
            raise ValueError("limit must be at least 1")

        results = self._results
        if minimum_score is not None:
            results = [result for result in results if result.anomaly_score >= minimum_score]

        return results[:limit]

    def get(self, detection_id: UUID) -> DetectionResult | None:
        """Find one detection result by its detection ID."""
        for result in self._results:
            if result.detection_id == detection_id:
                return result
        return None


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
