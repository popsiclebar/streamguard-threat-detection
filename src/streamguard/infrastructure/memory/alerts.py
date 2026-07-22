"""In-memory recent-alert repository for StreamGuard.

This repository stores detection results inside the current Python process. It
is intentionally temporary and exists for tests and simple local development.
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
