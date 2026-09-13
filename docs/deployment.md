# Deployment Guide

## Docker Compose

The easiest way to run Agent Operator in production is via Docker Compose.
This sets up the API server, a background worker, and PostgreSQL.

### Quick Start

```bash
# Clone the repository
git clone https://github.com/himanshu231204/agent-operator.git
cd agent-operator

# Create environment file
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker compose up -d

# Check health
curl http://localhost:8000/api/v1/health
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI HTTP server |
| `worker` | — | Background task processor |
| `postgres` | 5432 | PostgreSQL database |

## Environment Variables

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENVIRONMENT` | `development` | `development` or `production` |
| `APP_DEBUG` | `false` | Enable debug mode |
| `APP_API_PREFIX` | `/api/v1` | API route prefix |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/agent_operator` | PostgreSQL connection URL |
| `DATABASE_POOL_SIZE` | `5` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | `10` | Max overflow connections |

### Model Routing

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_ROUTER_FAST_MODEL` | `gpt-4o-mini` | Fast model for classification/formatting |
| `MODEL_ROUTER_TOOL_CALLING_MODEL` | `gpt-4o` | Tool-calling model |
| `MODEL_ROUTER_REASONING_MODEL` | `gpt-4o` | Reasoning model |
| `MODEL_ROUTER_STRONGEST_MODEL` | `gpt-4o` | Strongest model for high-risk tasks |

### LLM Providers

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `OPENROUTER_API_KEY` | OpenRouter API key (for multi-provider access) |
| `TAVILY_API_KEY` | Tavily search API key |

### LangSmith Tracing

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGCHAIN_TRACING_V2` | — | Set to `true` to enable |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | — | Project name for traces |

### Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `LIMITS_MAX_ITERATIONS` | `25` | Max agent loop iterations |
| `LIMITS_MAX_TOOL_CALLS` | `50` | Max tool calls per task |
| `LIMITS_MAX_EXECUTION_SECONDS` | `900` | Global execution timeout |
| `LIMITS_MAX_RETRIES` | `3` | Max retry attempts |
| `LIMITS_RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Per-tool rate limit |

### Social Integrations

| Variable | Description |
|----------|-------------|
| `X_ACCESS_TOKEN` | X/Twitter OAuth2 access token |
| `X_BEARER_TOKEN` | X/Twitter app-only bearer token |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn OAuth2 access token |
| `LINKEDIN_AUTHOR_URN` | LinkedIn author URN (e.g., `urn:person:abc123`) |

## Scaling

### Multiple Workers

To scale horizontally, simply start multiple worker instances.
PostgreSQL's `SELECT ... FOR UPDATE SKIP LOCKED` ensures each task is
claimed by exactly one worker:

```bash
docker compose up -d --scale worker=3
```

### Database Pooling

For high-throughput deployments, consider adding PgBouncer between
workers and PostgreSQL to reduce connection overhead.

## Monitoring

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Returns `{"status": "ok", "database": "connected"}`.

### Structured Logs

All logs are emitted as JSON (structlog). Example:

```json
{"task_id": "...", "event": "llm.start", "model": "gpt-4o", "level": "info"}
```

### LangSmith Traces

When enabled, every agent run is traced in LangSmith. View traces at:
https://smith.langchain.com/o/default/projects

### Secrets Audit

Scan for potential secret leakage in tool call records:

```bash
# Via API
curl http://localhost:8000/api/v1/audit/secrets

# Via CLI
python cli.py audit
```

## Security

### Secret Management

- Never commit `.env` files to Git
- Use a secret manager (AWS Secrets Manager, HashiCorp Vault) in production
- Rotate API keys regularly
- Use short-lived OAuth tokens where possible

### Network

- Run behind a reverse proxy (nginx, traefik) with TLS
- Set `SECURITY_ALLOWED_HOSTS` to restrict CORS origins
- Use `SECURITY_CORS_ORIGINS` to whitelist frontend origins

### Rate Limiting

Built-in rate limiting prevents runaway loops from hammering external APIs.
Configure `LIMITS_RATE_LIMIT_REQUESTS_PER_MINUTE` per your provider quotas.
