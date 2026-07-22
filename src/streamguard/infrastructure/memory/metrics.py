"""In-memory operational metrics repository for StreamGuard.

The counters are process-local and reset on restart, making this adapter useful
for tests and simple development runs but not for durable analytics.
"""

from streamguard.services.repositories import MetricsSnapshot


class InMemoryMetricsRepository:
    """Store operational counters inside the current Python process."""

    def __init__(self) -> None:
        """Create zeroed counters for local development and tests."""
        self._processed_total = 0
        self._anomalies_total = 0
        self._duplicates_total = 0
        self._invalid_total = 0
        self._failed_total = 0

    def increment_processed(self, *, is_anomaly: bool) -> None:
        """Record one newly processed result and whether it was anomalous."""
        self._processed_total += 1
        if is_anomaly:
            self._anomalies_total += 1

    def increment_duplicate(self) -> None:
        """Record one duplicate event handled through idempotency."""
        self._duplicates_total += 1

    def increment_invalid(self) -> None:
        """Record one invalid event payload."""
        self._invalid_total += 1

    def increment_failed(self) -> None:
        """Record one failed processing attempt."""
        self._failed_total += 1

    def snapshot(self) -> MetricsSnapshot:
        """Return current in-memory counter values."""
        return MetricsSnapshot(
            processed_total=self._processed_total,
            anomalies_total=self._anomalies_total,
            duplicates_total=self._duplicates_total,
            invalid_total=self._invalid_total,
            failed_total=self._failed_total,
        )
