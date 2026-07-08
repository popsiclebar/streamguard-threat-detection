"""Detector worker application package for StreamGuard.

The detector worker consumes raw security events from Kafka-compatible topics,
reuses the shared detection service, and publishes completed or dead-letter
messages.
"""
