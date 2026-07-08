# StreamGuard

## AI Threat Detection Pipeline

StreamGuard is a local-first, API-first threat-detection pipeline for learning
and demonstrating production-style AI software engineering. The project focuses
on turning security events into structured anomaly-detection results through a
small but realistic backend system.

## Table of Contents

- [About The Project](#about-the-project)
- [Built With](#built-with)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## About The Project

StreamGuard simulates a lightweight threat-detection workflow:

1. Security events are submitted through a FastAPI endpoint.
2. Events are validated and transformed into structured features.
3. A transparent baseline component scores suspicious activity.
4. Recent detection results are stored in process-local memory for retrieval.
5. FastAPI exposes endpoints for direct detection, recent alerts, and health checks.
6. Later milestones will add Kafka ingestion, Redis state, and vector search.

### Current Capabilities

The current Milestone 1 slice supports:

- Submit security events through a FastAPI endpoint.
- Validate incoming events with typed Pydantic schemas.
- Transform events into structured features for anomaly scoring.
- Score events with an honest rule-based baseline.
- Return versioned detection results.
- Store recent detection results in memory while the API process is running.
- Optionally store recent detection results in Redis.
- Track processed event IDs for idempotent repeated detection requests.
- Track basic operational counters for processed, anomalous, and duplicate events.
- Retrieve recent alerts and individual alert details through the API.
- Replay sample JSONL security events into a Kafka-compatible broker.
- Expose health and readiness endpoints.
- Provide unit and API tests for core behavior.

Planned later milestones include Kafka-compatible streaming ingestion, Redis
operational state, persistence across restarts, dead-letter handling, Qdrant
similarity search, and trained scikit-learn/PyTorch model backends.

## Built With

Current stack:

- Python
- FastAPI
- Pydantic
- pytest
- Ruff

Planned additions:

- Kafka-compatible local broker
- Qdrant
- Docker / Docker Compose for the full local stack
- scikit-learn
- PyTorch

## Getting Started

### Prerequisites

Local requirements:

- Python 3.12+
- Git

Docker Desktop or another Docker-compatible runtime will be needed for later
Kafka and Qdrant milestones. Redis can already be run with Docker Compose.

### Installation

Clone the repository:

```bash
git clone git@github.com:popsiclebar/streamguard-threat-detection.git
cd streamguard-threat-detection
```

Create a local environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

## Usage

Run tests:

```bash
python3 -m pytest -q
```

Run lint checks:

```bash
python3 -m ruff check apps src tests
```

Run the direct API workflow:

```bash
python3 -m uvicorn apps.api.main:app --reload
```

By default, recent alerts and processed-event markers are stored in process
memory. To use Redis for that operational state, start Redis and enable the
Redis repository backend:

```bash
docker compose up -d redis
ALERT_REPOSITORY_BACKEND=redis python3 -m uvicorn apps.api.main:app --reload
```

Start the local Kafka-compatible broker:

```bash
docker compose up -d redpanda
```

Create required Kafka-compatible topics:

```bash
python3 -m scripts.create_topics
```

Replay sample JSONL events to the raw security-events topic:

```bash
python3 -m apps.producer.main \
  --input data/sample/events.jsonl \
  --events-per-second 5
```

Run the detector worker against the raw topic:

```bash
python3 -m apps.detector.main --max-messages 2
```

The worker consumes from `security-events.raw`, calls the shared
`DetectionService`, publishes completed results to
`security-detections.completed`, and publishes malformed messages to
`security-events.dead-letter`.

Run the end-to-end streaming smoke test:

```bash
python3 -m scripts.smoke_test
```

Health checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

Detection request:

```bash
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -d @data/sample/example_event.json
```

Posting the same `event_id` again returns the original detection result while
the processed-event marker and alert detail are still retained.

Recent alerts:

```bash
curl http://localhost:8000/api/v1/alerts
curl "http://localhost:8000/api/v1/alerts?minimum_score=0.7"
```

Alert detail:

```bash
curl http://localhost:8000/api/v1/alerts/{detection_id}
```

Operational metrics:

```bash
curl http://localhost:8000/api/v1/metrics
```

Interactive API docs are available locally at:

```text
http://localhost:8000/docs
```

## Roadmap

- [x] Define versioned security-event and detection-result schemas.
- [x] Implement feature extraction and baseline anomaly scoring.
- [x] Add FastAPI health and detection endpoints.
- [x] Add in-memory recent alert retrieval.
- [x] Add unit and API tests.
- [x] Add Redis-backed recent alert repository.
- [x] Add Docker Compose Redis service.
- [ ] Add Kafka-compatible event ingestion.
- [x] Add Redis processed-event idempotency markers.
- [x] Add Redis operational counters.
- [x] Add Kafka-compatible broker service.
- [x] Add sample JSONL event producer.
- [x] Add detector worker foundation.
- [x] Add Kafka topic setup script.
- [x] Add end-to-end streaming smoke test script.
- [x] Add streaming dead-letter handling for invalid raw events.
- [ ] Add CI with linting and tests.
- [ ] Document architecture, limitations, and demo commands.

## Project Structure

```text
streamguard-threat-detection/
├── apps/
│   ├── api/
│   ├── detector/
│   └── producer/
├── src/
│   └── streamguard/
├── tests/
├── data/
│   └── sample/
├── artifacts/
├── deploy/
├── scripts/
├── .env.example
├── pyproject.toml
└── README.md
```

## Contributing

This is currently a personal learning project. Suggestions are welcome, but the
main development goal is to keep the system small, understandable, and runnable
locally.

If you want to propose a change:

1. Fork the project.
2. Create a feature branch.
3. Make a focused change.
4. Open a pull request with a clear explanation.

## License

No license has been selected yet.
