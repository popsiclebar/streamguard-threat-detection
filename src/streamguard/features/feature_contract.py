"""Authoritative feature contract shared by training and serving code.

Machine-learning systems are sensitive to feature order. This module defines the
single ordered list of feature names that every StreamGuard component must use
when turning security events into model-ready numeric vectors.
"""

from dataclasses import dataclass


FEATURE_VERSION = "1.0.0"

FEATURE_NAMES: tuple[str, ...] = (
    "source_port",
    "destination_port",
    "duration_ms",
    "source_bytes",
    "destination_bytes",
    "packet_count",
    "failed_connections",
    "tcp_flag_count",
    "protocol_tcp",
    "protocol_udp",
    "protocol_icmp",
    "bytes_per_packet",
    "failed_connection_ratio",
)


@dataclass(frozen=True)
class EventFeatureVector:
    """Ordered numeric representation of one validated security event.

    A dataclass is a small Python class mostly used to hold related data. The
    `frozen=True` option makes instances immutable, which protects the feature
    vector from accidental mutation after extraction.
    """

    names: tuple[str, ...]
    values: tuple[float, ...]
    version: str

    def as_dict(self) -> dict[str, float]:
        """Return a readable name-to-value mapping for debugging and tests."""
        return dict(zip(self.names, self.values, strict=True))
