# Agent Operator

A production-oriented AI operator that can research the web, control a browser, reason over
information, create content, and execute approved actions across web and social platforms.

See [`PROJECT.md`](PROJECT.md) for product vision and architecture, and [`AGENTS.md`](AGENTS.md)
for implementation rules. This repository is currently a **foundation**: the project skeleton,
typed interfaces, and infrastructure wiring are in place; the agent reasoning, browser
autonomy, research synthesis, and real social publishing are implemented incrementally on top
of it (see PROJECT.md section 54, "MVP").

## Architecture

```
API -> Services -> Agents -> Tools -> Integrations/Infrastructure
```

Business logic never lives in FastAPI routes; it lives in `app/services`. Agents (`app/agents`)
and tools (`app/tools`) are typed interfaces the orchestrator will drive. See `app/` for the
full package layout.

## Requirements

- Python 3.12+
- PostgreSQL 16 (via Docker Compose, or local)
- Redis 7 (via Docker Compose, or local)
- [Playwright](https://playwright.dev/python/) Chromium browser (`playwright install chromium`)

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in real values; never commit .env

# Start PostgreSQL + Redis (or point DATABASE_URL/REDIS_URL at your own)
docker compose up -d postgres redis

alembic upgrade head
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/api/v1/health`

## Testing

```bash
ruff check .
mypy app
pytest
```

## Docker

```bash
docker compose up --build
```

## Database migrations

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```
