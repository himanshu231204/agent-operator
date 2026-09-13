# Agent Operator

A production-oriented AI operator that can research the web, control a browser, reason over information, create content, and execute approved actions across web and social platforms.

[![CI](https://github.com/himanshu231204/agent-operator/actions/workflows/ci.yml/badge.svg)](https://github.com/himanshu231204/agent-operator/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

See [`PROJECT.md`](PROJECT.md) for product vision and architecture, and [`AGENTS.md`](AGENTS.md) for implementation rules.

## Features

- **Web Research**: Tavily-powered search with SSRF-protected web fetching
- **Content Generation**: Platform-aware drafting (X/Twitter, LinkedIn) with tone/safety checks
- **Social Publishing**: X/Twitter API v2 and LinkedIn integration with idempotency
- **Browser Automation**: Playwright-controlled Chromium with session pooling
- **Safety**: Human approval gates, rate limiting, secrets audit, task cancellation
- **Observability**: Structured logging, LangSmith tracing, token usage tracking

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone
git clone https://github.com/himanshu231204/agent-operator.git
cd agent-operator

# Install dependencies (creates venv automatically)
uv sync --extra dev

# Configure
cp .env.example .env
# Edit .env with your API keys

# Start database
docker compose up -d postgres

# Run migrations
uv run alembic upgrade head

# Start API
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/api/v1/health`

## Development

### Running Tests

```bash
# All tests (except real-LLM tests)
pytest tests/ -x

# With coverage
pytest --cov=app --cov-report=term-missing

# Unit tests only
pytest tests/unit/ -v
```

### Code Style

```bash
# Lint
ruff check .

# Type check
mypy app/

# Fix auto-fixable issues
ruff check --fix .
```

### CLI

```bash
# Create and monitor a task
python cli.py run "Research PostgreSQL best practices"

# Check task status
python cli.py status --task-id <uuid>

# View logs
python cli.py logs --task-id <uuid>

# Approve/cancel/audit
python cli.py approve --task-id <uuid>
python cli.py cancel --task-id <uuid>
python cli.py audit
```

## Architecture

```
API → Services → Orchestrator → LangGraph Agents → Tools → External APIs
```

Each specialized agent (`research`, `browser`, `content`, `social`, etc.) is a compiled **LangGraph** subgraph with isolated `MessagesState` (context quarantine). The orchestrator drives the task state machine, calling each agent per plan step. All tool calls route through `ToolExecutionEngine` for permission checks and audit logging.

See [`docs/deployment.md`](docs/deployment.md) for deployment configuration.

## Contributing

We welcome contributions! Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) for:

- Development setup
- Code style guidelines
- Testing requirements
- Pull request process
- Architecture patterns

## License

[MIT](LICENSE)
