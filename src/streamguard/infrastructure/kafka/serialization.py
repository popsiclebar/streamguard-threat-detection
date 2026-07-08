"""JSON serialization helpers for Kafka-compatible event messages.

Kafka transports bytes. These helpers convert StreamGuard's validated domain
models to and from JSON bytes so producers, consumers, and tests use one
consistent message format.
"""

from streamguard.domain import DeadLetterMessage, DetectionResult, SecurityEvent


def serialize_security_event(event: SecurityEvent) -> bytes:
    """Serialize one validated security event into UTF-8 JSON bytes."""
    return event.model_dump_json().encode("utf-8")


def deserialize_security_event(payload: bytes) -> SecurityEvent:
    """Deserialize UTF-8 JSON bytes into a validated security event."""
    return SecurityEvent.model_validate_json(payload.decode("utf-8"))


def serialize_detection_result(result: DetectionResult) -> bytes:
    """Serialize one detection result into UTF-8 JSON bytes."""
    return result.model_dump_json().encode("utf-8")


def serialize_dead_letter(message: DeadLetterMessage) -> bytes:
    """Serialize one dead-letter record into UTF-8 JSON bytes."""
    return message.model_dump_json().encode("utf-8")
