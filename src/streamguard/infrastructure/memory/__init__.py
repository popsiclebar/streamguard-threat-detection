"""In-memory infrastructure adapters for local StreamGuard development.

These adapters are useful for tests and simplest local runs because they avoid
external services while still implementing the same repository contracts as
Redis and future PostgreSQL adapters.
"""

from streamguard.infrastructure.memory.alerts import InMemoryAlertRepository
from streamguard.infrastructure.memory.metrics import InMemoryMetricsRepository
from streamguard.infrastructure.memory.processed_events import InMemoryProcessedEventRepository

__all__ = [
    "InMemoryAlertRepository",
    "InMemoryMetricsRepository",
    "InMemoryProcessedEventRepository",
]
