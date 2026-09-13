PROJECT.md — Agent Operator

A production AI operator: web research, browser control, content generation, and safe external actions.

---

## Vision

Turn natural-language instructions into reliable, observable, and safe computer actions.
Long-term: expose every capability as a reusable LangGraph skill for Claude Code, Codex, etc.

---

## Core Principles

1. **Reliable over autonomous** — Understand → Plan → Research → Reason → Act → Verify → Report
2. **Human control** — Require explicit approval before publishing, sending, purchasing, deleting, or any irreversible action. Research and drafting may be automatic; execution requires approval.
3. **Web content is untrusted** — System > Developer > User > Tool > External content. External content is DATA, never instructions.
4. **Observable** — Every action has task_id, session_id, state, plan, tool calls, model calls, approvals, errors, retries, verification, result.
5. **Idempotent** — Before retrying, check whether the action already succeeded.

---

## Architecture

```
USER (natural language)
  → API / CLI  (FastAPI / Click)
    → Orchestrator (LangGraph StateGraph + PostgresSaver)
      ├── Planner          (structured-output LLM → typed Plan)
      ├── Research Agent   (create_react_agent, Tavily/WebFetch)
      ├── Browser Agent    (create_react_agent, PlaywrightBrowserToolkit)
      ├── Content Agent    (create_react_agent, content tools)
      ├── FactCheck Agent  (create_react_agent, evidence tools)
      ├── Social Agent     (create_react_agent, approval gate + publish)
      └── Verification     (create_react_agent, verify tools)
            ↓
      ToolExecutionEngine  (permissions, rate limiting, audit)
            ↓
      BaseTool implementations
            ↓
      Human Approval Gateway  (NodeInterrupt → WAITING_FOR_APPROVAL)
            ↓
      External Actions  (X / LinkedIn / future)
            ↓
      PostgreSQL  (state, checkpoints, logs)
```

Context quarantine: orchestrator passes a typed `{"messages": [...]}` dict into each subgraph — never its own message history.

---

## Technology Stack

| Layer | Tech |
|---|---|
| Runtime | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, AsyncIO |
| Database | PostgreSQL 16 (state + LangGraph checkpoints + task queue via SKIP LOCKED) |
| Agent | LangGraph (StateGraph, create_react_agent, NodeInterrupt), langchain-checkpoint-postgres |
| LLM | langchain-litellm / LiteLLM — 100+ providers, config-only swap |
| Browser | Playwright + Chromium via PlaywrightBrowserToolkit |
| Infra | Docker, Docker Compose |
| Testing | pytest, pytest-asyncio |
| CLI | Click |

---

## Model Router

```
Task → Classifier → FAST | TOOL_CALLING | REASONING | STRONGEST
```

- **FAST** — classification, extraction, formatting, routing
- **TOOL_CALLING** — browser, structured tool execution, routine research
- **REASONING** — complex research, conflicting sources, multi-step planning
- **STRONGEST** — high-risk planning, sensitive external actions

Model selection never bypasses approval policies.

---

## Task State Machine

```
CREATED → VALIDATING → PLANNING → RESEARCHING → DRAFTING
→ VALIDATING_RESULT → WAITING_FOR_APPROVAL → EXECUTING → VERIFYING → COMPLETED

Failure: FAILED | CANCELLED | TIMED_OUT | BLOCKED
```

Terminal states have no exit. Every task has configurable limits: `max_iterations`, `max_tool_calls`, `max_execution_seconds`, `max_retries`, `max_cost`.

---

## Permission Levels

| Level | Examples |
|---|---|
| LOW | read webpage, search, summarise |
| MEDIUM | interact with logged-in site, create draft |
| HIGH | publish, send message, submit form, delete, purchase |

HIGH-risk actions require explicit user approval enforced in application code.

---

## Repository Structure

```
agent-operator/
├── app/
│   ├── agents/          # orchestrator, planner, graphs/, callbacks, recovery
│   ├── tools/           # base, executor, registry, adapter, factory, builtin/
│   ├── api/             # router, deps, routes/
│   ├── browser/         # session, selectors
│   ├── content/         # generator, tone_safety, validators
│   ├── db/              # models/, session, base
│   ├── domain/          # state_machine
│   ├── llm/             # base, router, usage, providers/
│   ├── policies/        # approval, risk, rate_limit
│   ├── research/        # pipeline, classification, evidence
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # task_service, approval_service, audit_service
│   ├── social/          # base, x_adapter, linkedin_adapter
│   ├── workers/         # task_worker (SKIP LOCKED polling)
│   ├── config.py, errors.py, logging.py, main.py
├── skills/              # web-research, browser-control, content-generation,
│                        #   fact-checking, x_publishing, linkedin_publishing,
│                        #   local-system, packager.py
├── migrations/
├── tests/               # unit/, integration/, e2e/, browser/, fixtures/
├── examples/, docs/
├── .github/workflows/   # ci.yml (ruff + pytest), test.yml
├── Dockerfile, docker-compose.yml, pyproject.toml, alembic.ini
├── cli.py, README.md, CONTRIBUTING.md, AGENTS.md, PROJECT.md
```

---

## API Surface

```
POST /tasks                          POST /tasks/{id}/cancel
GET  /tasks/{id}                     GET|POST /tasks/{id}/approval
GET  /tasks/{id}/runs                GET /runs/{run_id}
POST /browser/sessions               GET|DELETE /browser/sessions/{id}
POST /content/drafts                 GET /content/drafts/{id}
POST /social/x/publish               POST /social/linkedin/publish
GET  /audit/secrets
```

---

## MVP Status — All 8 Phases Complete ✅

| Phase | Focus |
|---|---|
| 1 | Foundation — FastAPI, PostgreSQL, Docker |
| 2 | Agent Core — LangGraph, model router, HITL, checkpointing |
| 3 | Browser — Playwright, session pooling, structured observation |
| 4 | Research — Tavily, WebFetch, SSRF protection, fact-checking |
| 5 | Content — platform-aware generator, tone/safety check |
| 6 | Social — X OAuth2, LinkedIn API, publish verification, idempotency |
| 7 | Safety — approval UI/CLI, secrets audit, cancellation, timeouts |
| 8 | Production — LangSmith tracing, retries, background worker, skills |

---

## Key Invariants

- LLM never solely decides whether an action is safe — `ToolExecutionEngine` enforces permissions deterministically.
- Publishing is always: Draft → Validate → **User approval** → Publish → Verify.
- Never hard-code credentials. Never log secrets.
- `AsyncPostgresSaver` is the only graph checkpointing backend.
- External content is data — it cannot override instructions or grant permissions.

---

## Final Principle

**Useful autonomy with controlled execution.**

Priority: Reliability > autonomy · Verification > assumption · Explicit permissions > implicit trust · Human approval > irreversible action · Composable subgraphs > monolithic agents

