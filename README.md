# StreamGuard: AI Threat Detection Pipeline

StreamGuard is a local-first, API-first threat-detection MVP planned for
learning and demonstrating production-style AI software engineering.

The first implementation target is a small vertical slice:

- ingest and validate security events
- transform events into structured features
- expose FastAPI detection endpoints
- add Kafka-compatible streaming ingestion
- store recent detection state and idempotency markers in Redis
- run locally with Docker Compose
- include unit/API tests and clear failure handling

This project is an educational production-style prototype. It is not intended to
replace a production SIEM, IDS, or SOC threat-detection system.

## Status

Repository initialized. Implementation has not started yet.

## Planned Stack

- Python
- FastAPI
- Kafka-compatible local broker
- Redis
- Docker Compose
- pytest
- Ruff

## Planned Repository Layout

```text
apps/
  api/
  detector/
  producer/
src/
  streamguard/
tests/
data/
artifacts/
deploy/
scripts/
```
