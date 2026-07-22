"""Redis infrastructure adapters for StreamGuard operational state.

Redis is used for fast, temporary operational state such as recent alerts,
processed-event markers, and counters. It is not the durable historical store.
"""

from streamguard.infrastructure.redis.alerts import RedisAlertRepository
from streamguard.infrastructure.redis.metrics import RedisMetricsRepository
from streamguard.infrastructure.redis.processed_events import RedisProcessedEventRepository

__all__ = [
    "RedisAlertRepository",
    "RedisMetricsRepository",
    "RedisProcessedEventRepository",
]
