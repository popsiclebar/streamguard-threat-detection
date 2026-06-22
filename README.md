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

1. Security events are submitted through an API or streamed through a Kafka-compatible broker.
2. Events are validated and transformed into structured features.
3. A detection component scores suspicious activity.
4. Recent detection results and processed event markers are stored in Redis.
5. FastAPI exposes endpoints for detection, health checks, and result retrieval.

### What It Can Do

The first MVP is planned to support:

- Submit security events through a FastAPI endpoint.
- Validate incoming events with typed Pydantic schemas.
- Transform events into structured features for anomaly scoring.
- Process events from a Kafka-compatible streaming topic.
- Store recent detections and processed event IDs in Redis.
- Route invalid messages to a dead-letter flow.
- Run locally with Docker Compose.
- Provide unit and API tests for core behavior.

## Built With

Planned core stack:

- Python
- FastAPI
- Pydantic
- Kafka-compatible local broker
- Redis
- Docker / Docker Compose
- pytest
- Ruff

## Getting Started

### Prerequisites

Planned local requirements:

- Python 3.12+
- Docker Desktop or another Docker-compatible runtime
- Git

### Installation

Clone the repository:

```bash
git clone git@github.com:popsiclebar/streamguard-threat-detection.git
cd streamguard-threat-detection
```

Create a local environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies once they are added:

```bash
pip install -e ".[dev]"
```

## Usage

Planned local workflow:

```bash
docker compose up --build
```

Planned direct API workflow:

```bash
uvicorn apps.api.main:app --reload
```

Planned detection request:

```bash
curl -X POST http://localhost:8000/api/v1/detections \
  -H "Content-Type: application/json" \
  -d @data/sample/example_event.json
```

## Roadmap

- [ ] Define versioned security-event and detection-result schemas.
- [ ] Implement feature extraction and baseline anomaly scoring.
- [ ] Add FastAPI health and detection endpoints.
- [ ] Add unit and API tests.
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