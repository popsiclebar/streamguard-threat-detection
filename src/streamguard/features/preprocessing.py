"""Feature preprocessing for validated StreamGuard security events.

Preprocessing is the bridge between human-readable event fields and numeric
model inputs. The rules here are intentionally simple for the first milestone so
the extraction contract is easy to inspect, test, and explain in interviews.
"""

from streamguard.domain import SecurityEvent
from streamguard.features.feature_contract import FEATURE_NAMES, FEATURE_VERSION, EventFeatureVector


def extract_event_features(event: SecurityEvent) -> EventFeatureVector:
    """Convert one validated event into StreamGuard's ordered feature vector.

    The returned values follow `FEATURE_NAMES` exactly. Keeping this logic in one
    function prevents the API, future Kafka worker, and future model-training
    code from inventing different feature orders or calculations.
    """
    total_bytes = event.source_bytes + event.destination_bytes
    bytes_per_packet = total_bytes / event.packet_count if event.packet_count else 0.0
    failed_connection_ratio = event.failed_connections / event.packet_count if event.packet_count else 0.0

    values = (
        float(event.source_port),
        float(event.destination_port),
        float(event.duration_ms),
        float(event.source_bytes),
        float(event.destination_bytes),
        float(event.packet_count),
        float(event.failed_connections),
        float(event.tcp_flag_count),
        1.0 if event.protocol == "TCP" else 0.0,
        1.0 if event.protocol == "UDP" else 0.0,
        1.0 if event.protocol == "ICMP" else 0.0,
        bytes_per_packet,
        failed_connection_ratio,
    )

    return EventFeatureVector(
        names=FEATURE_NAMES,
        values=values,
        version=FEATURE_VERSION,
    )
