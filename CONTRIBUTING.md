# Contributing to Agent Operator

Welcome! This guide will help you get started with contributing to Agent Operator.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Project Architecture](#project-architecture)
- [Adding New Features](#adding-new-features)
- [Submitting Changes](#submitting-changes)

---

## Getting Started

### Prerequisites

- **Python 3.12+**
- **PostgreSQL 16+**
- **uv** package manager ([installation](https://docs.astral.sh/uv/getting-started/installation/))

### Fork & Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR_USERNAME/agent-operator.git
cd agent-operator
```

---

## Development Setup

### 1. Install Dependencies

```bash
# uv automatically creates a virtualenv and installs deps
uv sync --extra dev
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys (see below)
```

**Minimum required for development:**
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agent_operator
MODEL_ROUTER_DEFAULT_PROVIDER=fake
```

**Optional (for full functionality):**
```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

### 3. Set Up Database

```bash
# Start PostgreSQL (Docker)
docker compose up -d postgres

# Run migrations
uv run alembic upgrade head
```

### 4. Verify Installation

```bash
# Run tests
pytest tests/ -x -q

# Check code style
ruff check .
```

---

## Code Style

We enforce consistency via `ruff` (linting + formatting) and `mypy` (type checking).

### Ruff

| Rule Set | Coverage |
|----------|----------|
| E, F, I, UP, B, ASYNC | All Python files |
| Line length | 100 (E501 ignored) |
| Import sorting | isort (first-party: `app`) |

```bash
# Check
ruff check app/ tests/

# Auto-fix
ruff check --fix app/ tests/
```

### Type Hints

All application code uses type hints. Run `mypy` before committing:

```bash
mypy app/
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files | `snake_case.py` | `tool_executor.py` |
| Classes | `PascalCase` | `ToolExecutionEngine` |
| Functions | `snake_case` | `execute()` |
| Constants | `UPPER_SNAKE` | `MAX_RETRIES` |
| Private | `_leading_underscore` | `_session` |

---

## Testing

### Test Structure

```
tests/
├── unit/           # Isolated logic (no network/DB)
├── integration/    # Database + service layer
├── e2e/            # Full pipeline (mocked external)
├── browser/        # Playwright (requires Chromium)
└── fixtures/       # Test data (adversarial payloads, etc.)
```

### Running Tests

```bash
# All tests (except real-LLM tests)
pytest tests/ -x --ignore=tests/integration/test_content_generator_real_llm.py

# Unit tests only
pytest tests/unit/ -v

# With coverage
pytest --cov=app --cov-report=term-missing

# Specific test file
pytest tests/unit/test_tool_executor.py -v
```

### Writing Tests

- **Unit tests**: Mock all external dependencies. Fast and isolated.
- **Integration tests**: Use in-memory SQLite. Test service + DB layer.
- **E2E tests**: Mock HTTP/network calls. Test full pipeline.

```python
# Example unit test
async def test_approval_creates_db_row(session):
    service = ApprovalService(session)
    approval = await service.create_approval(uuid.uuid4(), ApprovalRequest(...))
    assert approval.status == "pending"
```

---

## Project Architecture

### Request Flow

```
HTTP Request
  → FastAPI Router (app/api/routes/)
    → Service (app/services/)
      → Orchestrator (app/agents/orchestrator.py)
        → LangGraph Subgraph (app/agents/graphs/)
          → ToolExecutionEngine (app/tools/executor.py)
            → BaseTool implementation (app/tools/builtin/)
              → External API (X, LinkedIn, etc.)
```

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `app/agents/` | LangGraph agent subgraphs (research, browser, content, etc.) |
| `app/api/` | FastAPI routers + dependency injection |
| `app/db/` | SQLAlchemy ORM models |
| `app/llm/` | Model router, provider abstraction, usage tracking |
| `app/policies/` | Approval, risk classification, rate limiting |
| `app/schemas/` | Pydantic request/response models |
| `app/services/` | Business logic (orchestrator, tasks, approvals) |
| `app/social/` | X/LinkedIn adapters |
| `app/tools/` | Tool framework + built-in implementations |
| `app/workers/` | Background task processing |
| `migrations/` | Alembic database migrations |
| `skills/` | Reusable packaged LangGraph subgraphs |
| `tests/` | All tests |

### Key Concepts

1. **Tools**: All capabilities are `BaseTool` subclasses with typed I/O schemas and `ToolPermissions`.
2. **ToolExecutionEngine**: Central dispatcher enforcing permissions, rate limiting, and audit logging.
3. **Context Quarantine**: Each agent subgraph receives only a step-scoped `HumanMessage`, never the orchestrator's full history.
4. **Approval Gateway**: HIGH-risk actions (publish, send, delete) require explicit user approval before execution.
5. **Idempotency**: External actions (publishing) check for duplicates before retrying.

---

## Adding New Features

### Adding a New Tool

1. Create `app/tools/builtin/my_tool.py`:

```python
from app.policies.risk import RiskLevel
from app.schemas.my_tool import MyToolInput, MyToolOutput
from app.tools.base import BaseTool, ToolPermissions

class MyTool(BaseTool[MyToolInput, MyToolOutput]):
    name = "my_tool"
    description = "What this tool does"
    permissions = ToolPermissions(
        risk_level=RiskLevel.LOW,
        requires_approval=False,
    )

    async def execute(self, tool_input: MyToolInput) -> MyToolOutput:
        # Implementation
        ...
```

2. Register in `app/tools/factory.py`:

```python
from app.tools.builtin.my_tool import MyTool

# In build_registry():
registry.register(MyTool())
```

3. Add to agent graph's `_TOOL_NAMES`:

```python
# In app/agents/graphs/my_agent.py:
_TOOL_NAMES = ["my_tool", ...]
```

4. Write tests in `tests/unit/test_my_tool.py`.

### Adding a New Agent Graph

1. Create `app/agents/graphs/my_agent.py` following the pattern:

```python
from langgraph.prebuilt import create_react_agent
from app.agents.graphs._helpers import MY_CRITERIA, collect_tools, resolve_model

_SYSTEM_PROMPT = """..."""
_TOOL_NAMES = ["tool_a", "tool_b"]

def build_graph(router, engine, registry, *, context=None):
    model = resolve_model(router, MY_CRITERIA)
    tools = collect_tools(_TOOL_NAMES, engine, registry, context=context)
    return create_react_agent(model=model, tools=tools, state_modifier=_SYSTEM_PROMPT)
```

2. Add `_AGENT_KEY` entry in `app/agents/orchestrator.py`.

3. Add `RoutingCriteria` constant in `app/agents/graphs/_helpers.py`.

---

## Submitting Changes

### Branch Naming

```
feat/add-web-research-tool
fix/orchestrator-timeout-handling
docs/update-architecture-diagram
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add LinkedIn OAuth2 adapter
fix: prevent duplicate social posts on retry
docs: add deployment guide
test: add rate limiter unit tests
refactor: extract approval service interface
```

### Pull Request Process

1. **Open a PR** with a clear description of the change
2. **CI must pass**: `ruff check`, `mypy`, and `pytest`
3. **Add tests** for new functionality
4. **Update docs** if behavior changes
5. **Request review** from a maintainer

### Code Review Checklist

- [ ] Code follows project style (ruff + mypy clean)
- [ ] Tests added and passing
- [ ] No secrets in code/logs (use environment variables)
- [ ] Idempotency considered for external actions
- [ ] Permissions enforced via `ToolPermissions`
- [ ] Context quarantine maintained (no shared `MessagesState`)

---

## Need Help?

- Read `PROJECT.md` for product vision and architecture
- Read `AGENTS.md` for detailed implementation rules
- Open an issue for bugs or feature requests

Thank you for contributing!
