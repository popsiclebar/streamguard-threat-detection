"""Tests for turning validated security events into numeric feature vectors.

These tests protect the feature contract. If feature order or calculations drift
later, the tests fail before scoring or model-training code quietly changes
behavior.
"""

from streamguard.domain import SecurityEvent
from streamguard.features import FEATURE_NAMES, FEATURE_VERSION, extract_event_features


def valid_event_payload() -> dict[str, object]:
    """Build a representative event payload for feature extraction tests."""
    return {
        "schema_version": "1.0",
        "event_id": "50e7935d-8c80-49ef-9613-a846c88b1220",
        "timestamp": "2026-06-22T08:30:00Z",
        "source_ip": "10.10.1.12",
        "destination_ip": "172.16.0.20",
        "source_port": 52311,
        "destination_port": 443,
        "protocol": "TCP",
        "duration_ms": 192.4,
        "source_bytes": 1450,
        "destination_bytes": 8300,
        "packet_count": 41,
        "failed_connections": 2,
        "tcp_flag_count": 4,
    }


def test_extract_event_features_uses_authoritative_order() -> None:
    """Extracted feature names must match the shared contract exactly."""
    event = SecurityEvent.model_validate(valid_event_payload())

    features = extract_event_features(event)

    assert features.names == FEATURE_NAMES
    assert features.version == FEATURE_VERSION
    assert len(features.values) == len(FEATURE_NAMES)


def test_extract_event_features_maps_numeric_fields() -> None:
    """Raw numeric event fields should be copied into predictable float values."""
    event = SecurityEvent.model_validate(valid_event_payload())

    feature_map = extract_event_features(event).as_dict()

    assert feature_map["source_port"] == 52311.0
    assert feature_map["destination_port"] == 443.0
    assert feature_map["duration_ms"] == 192.4
    assert feature_map["source_bytes"] == 1450.0
    assert feature_map["destination_bytes"] == 8300.0


def test_extract_event_features_one_hot_encodes_protocol() -> None:
    """Protocol text becomes numeric indicator columns for model compatibility."""
    payload = valid_event_payload()
    payload["protocol"] = "UDP"
    event = SecurityEvent.model_validate(payload)

    feature_map = extract_event_features(event).as_dict()

    assert feature_map["protocol_tcp"] == 0.0
    assert feature_map["protocol_udp"] == 1.0
    assert feature_map["protocol_icmp"] == 0.0


def test_extract_event_features_calculates_derived_values() -> None:
    """Derived features summarize traffic intensity and connection failures."""
    event = SecurityEvent.model_validate(valid_event_payload())

    feature_map = extract_event_features(event).as_dict()

    assert feature_map["bytes_per_packet"] == (1450 + 8300) / 41
    assert feature_map["failed_connection_ratio"] == 2 / 41


def test_extract_event_features_handles_zero_packets() -> None:
    """Division-based derived features should be safe when packet_count is zero."""
    payload = valid_event_payload()
    payload["packet_count"] = 0
    payload["failed_connections"] = 0
    event = SecurityEvent.model_validate(payload)

    feature_map = extract_event_features(event).as_dict()

    assert feature_map["bytes_per_packet"] == 0.0
    assert feature_map["failed_connection_ratio"] == 0.0
