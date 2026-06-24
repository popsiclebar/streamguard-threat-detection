"""Domain models for StreamGuard's core security-event workflow.

Domain code describes the important business concepts in the system without
depending on API routes, streaming workers, databases, or infrastructure tools.
"""

from streamguard.domain.detections import DetectionResult
from streamguard.domain.events import SecurityEvent

__all__ = ["DetectionResult", "SecurityEvent"]
