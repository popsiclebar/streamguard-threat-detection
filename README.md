# StreamGuard

## Event-Driven Threat Detection Pipeline

StreamGuard is a local-first backend for ingesting network-security events and
producing structured anomaly-detection results. It supports both synchronous
HTTP requests and Kafka-compatible event streams while keeping validation,
feature extraction, scoring, and persistence behind shared application
services.

The project demonstrates an event-driven service architecture built around
versioned data contracts, deterministic feature extraction, interchangeable
infrastructure adapters, idempotent processing, and observable failure paths.
Detection is exposed through one application boundary, allowing model
implementations to evolve independently of transport and storage concerns.

## Contents

- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Capabilities](#capabilities)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Streaming Workflow](#streaming-workflow)
- [Development and Verification](#development-and-verification)
- [Operational Semantics](#operational-semantics)
- [Roadmap](#roadmap)

## Architecture

```text
SYNCHRONOUS
HTTP client ---> FastAPI ---> DetectionService ---> HTTP response
                    |                 |
                    |                 +---> feature extraction ---> scoring
                    |                 +---> repository interfaces
                    |                              |
                    +--- alerts / metrics          +---> Memory or Redis
                                                   +---> PostgreSQL history

STREAMING
JSONL ---> Producer ---> Kafka raw topic ---> Detector worker
                                                  |
                         +------------------------+------------------+
                         | valid                                     | invalid
                         v                                           v
                DetectionService                           dead-letter topic
                         |
                         v
                completed-detection topic
```

Both ingestion paths converge on `DetectionService`. The service owns the
feature-to-result workflow and depends only on repository protocols; FastAPI,
Kafka, Redis, and PostgreSQL remain infrastructure details. The worker publishes
valid results to the completed topic and preserves invalid input as structured
dead-letter records for inspection or replay.

## Project Structure

```text
streamguard-threat-detection/
|-- apps/
|   |-- api/            # FastAPI application and routes
|   |-- detector/       # Kafka-compatible detection worker
|   `-- producer/       # JSONL event replay CLI
|-- src/streamguard/
|   |-- domain/         # Versioned input and output schemas
|   |-- features/       # Feature contract and preprocessing
|   |-- models/         # Explainable baseline scorer
|   |-- services/       # Application workflows and repository protocols
|   `-- infrastructure/ # Memory, Redis, PostgreSQL, and Kafka adapters
|-- tests/              # Unit, integration-style, and API tests
|-- data/sample/        # Reproducible example events
|-- scripts/            # Topic setup and streaming smoke test
|-- docker-compose.yml
`-- pyproject.toml
```

## Capabilities

- Accept and validate versioned network-security events through FastAPI.
- Extract a deterministic 13-feature vector from each accepted event.
- Produce explainable anomaly scores with a configurable rule-based threshold.
- Retrieve recent results and filter alerts by minimum score.
- Store recent alerts, idempotency markers, and counters in memory or Redis.
- Optionally persist complete detection results to PostgreSQL using queryable
  columns and a JSONB representation of the versioned result.
- Replay JSONL events into a Kafka-compatible Redpanda broker.
- Consume raw events and publish completed detection results.
- Route malformed streamed events to a dead-letter topic.
- Run the service stack locally with Docker Compose.

## Technology Stack

- Python 3.12
- FastAPI and Uvicorn
- Pydantic
- Redpanda / Kafka (`confluent-kafka`)
- Redis
- PostgreSQL / psycopg
- Docker Compose
- pytest and Ruff

## Quick Start

### Requirements

- Python 3.12+
- Git
- Docker Desktop or another Docker-compatible runtime for Redis, Redpanda, and
  PostgreSQL

Clone and install the project:

```bash
git clone git@github.com:popsiclebar/streamguard-threat-detection.git
cd streamguard-threat-detection
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Run the default in-memory API:

```bash
python3 -m uvicorn apps.api.main:app --reload
```

Interactive OpenAPI documentation is available at
`http://localhost:8000/docs`.

### Direct Detection

Submit the included example event:

```bash
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -d @data/sample/example_event.json
```

Posting the same retained `event_id` again returns the original detection
instead of creating a duplicate.

Inspect service state:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
curl http://localhost:8000/api/v1/alerts
curl "http://localhost:8000/api/v1/alerts?minimum_score=0.7"
curl http://localhost:8000/api/v1/metrics
```

Retrieve one result with `GET /api/v1/alerts/{detection_id}`.

## API Reference

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/detections` | Validate and score one security event |
| `GET` | `/api/v1/alerts` | List recent detections with optional `limit` and `minimum_score` filters |
| `GET` | `/api/v1/alerts/{detection_id}` | Retrieve one detection result |
| `GET` | `/api/v1/metrics` | Read processed, anomalous, duplicate, invalid, and failed counters |
| `GET` | `/health/live` | Confirm that the API process is running |
| `GET` | `/health/ready` | Read application readiness state |

All request and response bodies use versioned Pydantic schemas. FastAPI exposes
the generated OpenAPI schema at `/openapi.json` and interactive documentation at
`/docs`.

## Storage Backends

Start the optional storage services:

```bash
docker compose up -d redis postgres
```

Run the API with Redis operational state and durable PostgreSQL history:

```bash
ALERT_REPOSITORY_BACKEND=redis \
DETECTION_HISTORY_BACKEND=postgres \
python3 -m uvicorn apps.api.main:app --reload
```

Memory remains the default alert backend, and durable history is disabled by
default. See `.env.example` for all supported settings.

## Configuration

StreamGuard is configured through environment variables. Defaults support a
zero-infrastructure API run; external services are enabled explicitly.

| Variable | Default | Description |
| --- | --- | --- |
| `ALERT_REPOSITORY_BACKEND` | `memory` | Operational-state adapter: `memory` or `redis` |
| `DETECTION_HISTORY_BACKEND` | `none` | Durable-history adapter: `none` or `postgres` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `POSTGRES_URL` | local `streamguard` database | PostgreSQL connection URL |
| `RECENT_ALERT_LIMIT` | `100` | Maximum number of retained recent results |
| `ALERT_TTL_SECONDS` | `86400` | Redis alert retention period |
| `PROCESSED_EVENT_TTL_SECONDS` | `86400` | Redis idempotency-marker retention period |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka-compatible broker address |
| `KAFKA_RAW_TOPIC` | `security-events.raw` | Input event topic |
| `KAFKA_DETECTION_TOPIC` | `security-detections.completed` | Completed-result topic |
| `KAFKA_DEAD_LETTER_TOPIC` | `security-events.dead-letter` | Invalid-payload topic |
| `PRODUCER_EVENTS_PER_SECOND` | `5` | Default replay rate for the producer CLI |

## Streaming Workflow

Start Redpanda and create the required topics:

```bash
docker compose up -d redpanda
python3 -m scripts.create_topics
```

In separate terminals, replay the sample events and run the detector:

```bash
python3 -m apps.producer.main \
  --input data/sample/events.jsonl \
  --events-per-second 5
```

```bash
python3 -m apps.detector.main --max-messages 2
```

The worker consumes `security-events.raw`, publishes valid results to
`security-detections.completed`, and sends invalid payloads to
`security-events.dead-letter`.

Run the automated streaming smoke test after the broker is ready:

```bash
python3 -m scripts.smoke_test
```

## Development and Verification

Run the automated test suite:

```bash
python3 -m pytest -q
```

Run static lint checks:

```bash
python3 -m ruff check apps src tests scripts
```

The test suite covers domain validation, feature extraction, baseline scoring,
service orchestration, repository adapters, API endpoints, Kafka serialization,
worker behavior, configuration, and the smoke-test helper.

Current repository status: **87 tests passing** and **Ruff checks passing**.

## Operational Semantics

- **Scoring:** The baseline scorer produces deterministic, explainable results
  against the versioned feature contract. Offline training, calibrated model
  thresholds, and predictive evaluation are separate roadmap items.
- **Delivery:** The worker commits consumed messages after processing. The
  current pipeline does not claim end-to-end exactly-once delivery.
- **Idempotency:** Duplicate suppression is bounded by the retention of both the
  processed-event marker and its associated alert result.
- **Readiness:** The readiness endpoint reports application state; it does not
  currently probe Redis, PostgreSQL, or Kafka.
- **Observability:** Repository-backed counters provide local operational
  insight. Centralized metrics, tracing, and structured logs are not configured.
- **Deployment:** Docker Compose provisions a reproducible development stack;
  production orchestration, secrets management, and horizontal scaling are out
  of scope for the current version.

## Roadmap

- Add continuous integration for tests and linting.
- Add dependency-aware readiness checks and structured application logging.
- Strengthen worker retry, delivery-confirmation, and shutdown behavior.
- Add database migrations and richer indexes for detection history.
- Introduce a scorer protocol and a trained scikit-learn anomaly detector.
- Add a reproducible training and evaluation pipeline with versioned artifacts.
- Report precision, recall, F1, and false-positive rate on held-out labeled data.
