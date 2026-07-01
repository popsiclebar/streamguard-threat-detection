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
4. FastAPI exposes endpoints for direct detection and health checks.
5. Later milestones will add Kafka ingestion, Redis state, and vector search.

### Current Capabilities

The current Milestone 1 slice supports:

- Submit security events through a FastAPI endpoint.
- Validate incoming events with typed Pydantic schemas.
- Transform events into structured features for anomaly scoring.
- Score events with an honest rule-based baseline.
- Return versioned detection results.
- Expose health and readiness endpoints.
- Provide unit and API tests for core behavior.

Planned later milestones include Kafka-compatible streaming ingestion, Redis
operational state, dead-letter handling, Qdrant similarity search, and trained
scikit-learn/PyTorch model backends.

## Built With

Current stack:

- Python
- FastAPI
- Pydantic
- pytest
- Ruff

Planned additions:

- Kafka-compatible local broker
- Redis
- Qdrant
- Docker / Docker Compose
- scikit-learn
- PyTorch

## Getting Started

### Prerequisites

Local requirements:

- Python 3.12+
- Git

Docker Desktop or another Docker-compatible runtime will be needed for later
Kafka, Redis, and Qdrant milestones.

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

Interactive API docs are available locally at:

```text
http://localhost:8000/docs
```

## Roadmap

- [x] Define versioned security-event and detection-result schemas.
- [x] Implement feature extraction and baseline anomaly scoring.
- [x] Add FastAPI health and detection endpoints.
- [x] Add unit and API tests.
- [ ] Add Docker Compose for local services.
- [ ] Add Kafka-compatible event ingestion.
- [ ] Add Redis recent-result storage and idempotency.
- [ ] Add dead-letter handling for invalid events.
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
