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
API -> Services -> Orchestrator -> LangGraph ReAct Agents -> Tools -> Integrations/Infrastructure
```

Business logic never lives in FastAPI routes; it lives in `app/services`. Each specialized agent
(`app/agents/`) is a compiled **LangGraph** graph built with `create_react_agent`. The orchestrator
drives the task state machine and approval gateway, calling each agent graph per plan step. Tools
(`app/tools/`) are `StructuredTool`-wrapped capabilities routed through the `ToolExecutionEngine`
so permission checks and audit logging are never bypassed. See `app/` for the full package layout.

### Agent graph pattern

Each specialized agent is a compiled LangGraph subgraph with isolated `MessagesState` (context quarantine). The orchestrator passes a structured input dict — not its own message history — into each subgraph, preventing context bleed between agents.

```python
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# One subgraph per specialized agent — isolated MessagesState per invocation
research_graph = create_react_agent(
    model=routed_chat_model,           # selected by ModelRouter
    tools=[tavily_search, web_fetch],  # community tools via ToolExecutionEngine
    prompt=RESEARCH_SYSTEM_PROMPT,
)

# Orchestrator calls subgraph with structured input; receives structured result
async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
    compiled = research_graph.compile(checkpointer=checkpointer)
    result = await compiled.ainvoke(
        {"messages": [HumanMessage(content=step_instruction)]},
        config={
            "configurable": {"thread_id": str(task_id)},
            "callbacks": [run_callback],   # BaseCallbackHandler for tracing
        },
    )
```

**Context quarantine**: the orchestrator never forwards its own `MessagesState` into a subgraph — each agent reasons in complete isolation.

## Requirements

- Python 3.12+
- PostgreSQL 16 (via Docker Compose, or local)
- [Playwright](https://playwright.dev/python/) Chromium browser (`playwright install chromium`)
- `langgraph` + `langgraph-checkpoint-postgres` — agent graphs and PostgreSQL checkpointing
- `langchain-community` — built-in tools and toolkits (TavilySearch, PlaywrightBrowserToolkit, etc.)

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in real values; never commit .env

# Start PostgreSQL (or point DATABASE_URL at your own)
docker compose up -d postgres

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
