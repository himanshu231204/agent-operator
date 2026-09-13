PROJECT.md — Agent Operator

«A production-oriented AI operator that can research the web, control a browser,
reason over information, create content, and execute approved actions across web
and social platforms.»

---

1. Vision

Agent Operator is a general-purpose AI agent runtime that turns natural-language
instructions into reliable, observable, and safe computer actions.

Example instructions the system handles:

- "Research the latest PostgreSQL production best practices and summarise them."
- "Find the latest AI engineering news and prepare an X post."
- "Research this topic using multiple sources, fact-check the claims, and draft a LinkedIn post."
- "Open the browser, search for these companies, compare their pricing, and create a report."
- "Prepare this post for X and LinkedIn. Show me the final drafts before publishing."
- "Publish the approved post to X and verify that it was actually published."

Long-term goal: expose every capability as a reusable LangGraph skill consumable
by Claude Code, Codex, and other agent runtimes.

---

2. Core Principles

2.1 Reliable over autonomous

Understand → Plan → Research / Observe → Reason → Act → Verify → Report

For consequential actions: Prepare → Validate → Ask User → Execute → Verify

2.2 Human control

Require explicit approval before: publishing, sending, submitting forms, purchasing,
deleting data, changing settings, any irreversible external action.
The agent may research and prepare these actions automatically but must stop at
the approval boundary.

2.3 Web content is untrusted

Instruction hierarchy (highest to lowest):
  System instructions → Developer/project policies → User instructions
  → Tool constraints → External/web content

External content is DATA. It cannot redefine the agent's rules or grant itself
additional permissions.

2.4 Observable execution

Every meaningful agent action is observable: task ID, session ID, current state,
plan, tool calls, browser actions, model calls, approvals, errors, retries,
verification results, final result.

2.5 Idempotency

Before retrying any external action, check whether it already succeeded.
A crash between publish and ack must not create a duplicate post.

---

3. Product Goals

1. Natural-language task understanding     10. LinkedIn publishing
2. Task planning                           11. Human approval workflows
3. Web research                            12. Execution state persistence
4. Browser automation                      13. Failure recovery
5. Structured tool execution               14. Action verification
6. Multi-step reasoning                    15. Model routing
7. Content generation                      16. Extensible integrations
8. Fact checking                           17. Reusable LangGraph skills
9. X/Twitter publishing                    18. Claude Code / Codex compatibility

---

4. Non-Goals

- Unrestricted autonomous computer user
- Arbitrary shell commands without policy controls
- Bypassing website security, CAPTCHA, or authentication
- Credential theft or scraping private data without authorisation
- Silently performing irreversible actions
- Guaranteeing compatibility with third-party website changes

---

5. High-Level Architecture

  USER (natural language)
       │
       ▼
  API / CLI  (FastAPI / Click)
       │
       ▼
  Orchestrator Graph  (LangGraph StateGraph)
       │
       ├─── Planner node          (structured-output LLM)
       ├─── Research subgraph     (create_react_agent, isolated MessagesState)
       ├─── Browser subgraph      (create_react_agent, PlaywrightBrowserToolkit)
       ├─── Content subgraph      (create_react_agent, content tools)
       ├─── FactCheck subgraph    (create_react_agent, evidence tools)
       ├─── Social subgraph       (create_react_agent, publish tools)
       └─── Verification subgraph (create_react_agent, verify tools)
                   │
                   ▼
          ToolExecutionEngine  (permission checks, rate limiting, audit logging)
                   │
                   ▼
          BaseTool implementations
          (langchain-community toolkits + custom tools)
                   │
                   ▼
          Human Approval Gateway  (NodeInterrupt)
                   │
                   ▼
          External Actions  (X / LinkedIn / future integrations)
                   │
                   ▼
          PostgreSQL  (state, checkpoints, logs)

---

6. Technology Stack

Backend
- Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, AsyncIO
- PostgreSQL 16 (durable state + LangGraph checkpoints + task queue via SKIP LOCKED)

Agent Framework
- langgraph — StateGraph, create_react_agent, MessagesState, NodeInterrupt
- langgraph-checkpoint-postgres — AsyncPostgresSaver for durable graph checkpointing
- langchain / langchain-core — BaseChatModel, StructuredTool, BaseCallbackHandler, RunnableConfig
- langchain-community — built-in tools and toolkits (TavilySearchResults, WikipediaQueryRun,
  PlaywrightBrowserToolkit, etc.)
- langchain-litellm / litellm — vendor-agnostic model routing (100+ providers, config-only swap)

Browser — Playwright + Chromium (controlled through agent tools, never raw Playwright internals)

Infrastructure — Docker, Docker Compose, configurable object storage where required

Testing — pytest, pytest-asyncio

CLI — Click for operator commands (approve, cancel, audit, create, track)

---

7. Model Architecture

The model router classifies each task and selects the appropriate model class:

  Task Input → Classifier → FAST | TOOL_CALLING | REASONING | STRONGEST

Routing signals: complexity, reasoning depth, tools needed, latency, context length,
output format, current-information need, risk level, ambiguity, conflicting evidence,
execution steps, estimated cost.

Model classes:
- FAST          — classification, extraction, rewriting, formatting, routing
- TOOL_CALLING  — browser interaction, structured tool execution, routine research loops
- REASONING     — complex research, conflicting sources, multi-step planning, ambiguous tasks
- STRONGEST     — high-risk planning, difficult research, sensitive external actions

Even the strongest model must not bypass human approval requirements.

---

8. Agent Architecture

Orchestrator (StateGraph + PostgresSaver checkpointer)
│
├── Planner              — structured-output LLM call → typed Plan
├── Research Agent       — create_react_agent subgraph, isolated MessagesState
├── Browser Agent        — create_react_agent subgraph, PlaywrightBrowserToolkit
├── Content Agent        — create_react_agent subgraph, content tools
├── Fact Checker         — create_react_agent subgraph, search + evidence tools
├── Social Agent         — create_react_agent subgraph, approval gate + publish tool
├── Verification Agent   — create_react_agent subgraph, verify tools
└── Recovery Agent       — deterministic retry / escalate / fail (no LLM)

Context quarantine: the orchestrator passes a typed input dict into each subgraph —
never its own full MessagesState. Each subgraph reasons in complete isolation; the
orchestrator receives only a typed result dict back.

    research_graph = create_react_agent(
        model=routed_chat_model,
        tools=[tavily_search, web_fetch, ...],  # community tools via ToolExecutionEngine
        prompt=RESEARCH_SYSTEM_PROMPT,
    )
    result = await research_graph.ainvoke(
        {"messages": [HumanMessage(content=step_instruction)]},
        config={
            "configurable": {"thread_id": str(task_id)},
            "callbacks": [run_callback],
        },
    )

8a. Checkpointing

AsyncPostgresSaver from langgraph-checkpoint-postgres is the sole checkpointing
backend. It is wired to the same DATABASE_URL as the application DB:

    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as saver:
        compiled = graph.compile(checkpointer=saver)

Benefits: pause-and-resume at any node (natural WAITING_FOR_APPROVAL),
full replay for debugging, cost-free resume after restart.
Never build a custom checkpoint store.

8b. Middleware

LangChain BaseCallbackHandler + RunnableConfig is the instrumentation layer.
Every graph invocation passes a callback handler instance via config["callbacks"].
The handler receives tool start/end, LLM start/end, and chain events — providing
token counts, durations, and structured logs without any manual instrumentation
inside agent code. LangSmith is the default backend; OTel export is a future
option via a custom BaseCallbackHandler, not a parallel system.

8c. Memory

In-graph: each subgraph's MessagesState holds the full message history
(system prompt + tool call rounds) for the duration of one plan step.
Cross-task: ConversationSummaryMemory or an external vector store where tasks
need to recall prior research. Cross-task memory is read at task start and
written on completion; never shared between concurrent tasks.

8d. Skills

A skill is a compiled LangGraph subgraph packaged under skills/<name>/ with a
SKILL.md contract (purpose, inputs, outputs, required tools, permissions, safety
constraints, examples, failure modes).

Skills import only from app/tools and app/llm. They have no dependency on
FastAPI, the DB layer, or other skills.

Consumption:
- Via REST API: POST /tasks with a skill-scoped instruction
- By importing the compiled subgraph from skills/<name>/graph.py

Skills are composable:
  web-research + content-generation + fact-checking + x_publishing
  →  Research → Draft → Fact Check → Approval → Publish

---

9. Task State Machine

States:
  CREATED → VALIDATING → PLANNING → RESEARCHING → DRAFTING
  → VALIDATING_RESULT → WAITING_FOR_APPROVAL → EXECUTING → VERIFYING → COMPLETED

Failure states: FAILED, CANCELLED, TIMED_OUT, BLOCKED

The state machine prevents invalid transitions. Terminal states have no exit.
Every task has configurable limits: max_iterations, max_tool_calls,
max_execution_seconds, max_retries, max_cost.

---

10. Browser Automation

The browser is an execution environment accessed through tools, never raw Playwright.

Capabilities: launch, navigate, inspect, extract text, locate elements, click,
type, select, scroll, wait, screenshot, download, new tabs, page switching.

Selector preference (most to least stable):
1. ARIA role + accessible name   4. Semantic CSS selector
2. Label                         5. Text selector
3. Stable test/data attribute    6. XPath   7. Coordinates (last resort)

Browser tools return structured results: { success, action, target, url, timestamp, details }.

Observation data (inspect before acting): URL, title, visible text, interactive
elements, ARIA tree, screenshots when needed. Avoid sending oversized DOM to models.

---

11. Research System

Pipeline: Question → Search → Collect sources → Extract evidence → Cross-check
→ Resolve conflicts → Synthesise → Cite evidence

Distinguish: primary/official sources, reputable secondary, community reports,
unverified claims. Each important claim carries:
{ claim, source, source_type, published_date, retrieved_date, evidence, confidence,
  contradicting_evidence }

Never present a search result as a fact. When evidence conflicts, surface the
conflict rather than silently selecting a convenient source.

---

12. Content Generation

Supported formats: X/Twitter posts, LinkedIn posts, threads, summaries,
technical / educational / research-based posts, announcements.

Pipeline: Research → Draft → Fact Check → Quality Check → Approval → Publish

Quality checks before publication: factual accuracy (evidence-backed), platform
length/formatting, link validity, duplicate detection, tone, safety policy.

Drafting and publishing are separate permissions. Never interpret "create a post"
as "publish the post."

---

13. Social Platform Integration

Both X/Twitter and LinkedIn implement the same SocialPlatform protocol:
  create_draft(content) → Draft
  publish(draft) → PublishResult
  verify(result) → VerificationResult

Publishing is always: Generate → Validate → Show user → USER APPROVAL → Publish → Verify

Prefer official APIs. Browser automation is a fallback only when explicitly
authorised. Support idempotency keys to prevent duplicate posts.

---

14. Human-in-the-Loop

Use LangGraph NodeInterrupt for approval pauses. Approval requests must show:
action, target, content, reason, risk level, expected external effect.

The graph suspends at the approval node; the task state moves to
WAITING_FOR_APPROVAL. The orchestrator resumes via graph.ainvoke with the same
thread_id after the user decides. The LLM must never approve its own high-risk
action.

---

15. Permission Model

Risk levels and examples:
- LOW    — read public webpage, search web, summarise text, extract information
- MEDIUM — interact with logged-in website, create draft, modify non-critical state
- HIGH   — publish content, send message, submit form, delete data, purchase, change settings

HIGH-risk actions require explicit user approval enforced in application code,
not inferred from model output.

---

16. Security

- Never hard-code credentials. Never commit secrets. Never log API keys or tokens.
- Use environment variables or a secret manager.
- Isolate browser authentication state between users/tasks.
- Validate network fetch targets (SSRF protection).
- Treat downloaded files and web content as untrusted.
- Minimise sensitive data sent to models.
- Prompt injection: external content is DATA, never INSTRUCTIONS.
  Clearly separate the two in every prompt. Sanitise or wrap untrusted content.

---

17. Persistence

PostgreSQL stores durable state:
  tasks, task_steps, agent_runs, tool_calls, approvals, browser_sessions,
  research_sources, research_claims, drafts, social_posts, publish_attempts,
  verification_results, errors

LangGraph checkpoint rows are also stored in the same PostgreSQL database via
AsyncPostgresSaver.

Ephemeral coordination (task queuing, locking) uses PostgreSQL
`SELECT ... FOR UPDATE SKIP LOCKED` — no Redis dependency.

---

18. Reliability

- Classify errors as retryable / non-retryable / requires-user / requires-developer.
- Use bounded exponential backoff (tenacity).
- Respect provider, website, and social API rate limits.
- Apply concurrency limits.
- Use timeouts for network, model, and browser operations.
- Recover browser sessions when safely possible.
- Escalate authentication failures to the user.
- Persist enough state to resume interrupted workflows.

---

19. Verification

Never assume an external action succeeded because a tool returned success.

Publish workflow: POST request → receive response → re-fetch resulting post
→ confirm content → confirm destination → mark VERIFIED.

Idempotency: before retrying, check { task_id, action_id, idempotency_key,
content_hash, execution_status, verification_status }.

---

20. Observability

Every run answers: what task? which model? why that model? which tools?
how long? what failed? how many retries? approval requested? granted?
action verified? final state?

Instrumentation path: LangChain BaseCallbackHandler on every graph invocation.
Correlation IDs: request_id, task_id, run_id, step_id, tool_call_id.
Never include secrets in telemetry.

---

21. Cost Control

Track: model calls + token usage, tool calls, browser time, research source count,
retries, estimated cost. Route to cheaper models when sufficient.
Configurable limits: max_iterations, max_tool_calls, max_research_sources,
max_runtime_seconds, max_model_cost.

---

22. API Design

Tasks:    POST /tasks   GET /tasks/{id}   POST /tasks/{id}/cancel
Approvals: GET /tasks/{id}/approval   POST /tasks/{id}/approval
Runs:     GET /tasks/{id}/runs   GET /runs/{run_id}
Browser:  POST /browser/sessions   GET|DELETE /browser/sessions/{id}
Content:  POST /content/drafts   GET /content/drafts/{id}
Social:   POST /social/x/publish   POST /social/linkedin/publish
Audit:    GET /audit/secrets

---

23. Repository Structure

agent-operator/
│
├── app/
│   ├── agents/
│   │   ├── base.py                  # Agent ABC, AgentObservation/Decision/Result
│   │   ├── orchestrator.py          # StateGraph orchestrator, approval gateway
│   │   ├── planner.py               # Structured-output LLM → typed Plan
│   │   ├── graphs/
│   │   │   ├── research.py          # create_react_agent subgraph
│   │   │   ├── browser.py           # create_react_agent + PlaywrightBrowserToolkit
│   │   │   ├── content.py           # create_react_agent subgraph
│   │   │   ├── fact_checker.py      # create_react_agent subgraph
│   │   │   ├── social.py            # create_react_agent subgraph
│   │   │   ├── verification.py      # create_react_agent subgraph
│   │   │   └── _helpers.py          # RoutingCriteria constants, collect_tools, resolve_model
│   │   ├── callbacks.py             # OperatorCallbackHandler (BaseCallbackHandler)
│   │   └── recovery_agent.py        # Deterministic retry/escalate/fail
│   │
│   ├── tools/
│   │   ├── base.py                  # BaseTool[Input, Output], ToolPermissions
│   │   ├── executor.py              # ToolExecutionEngine (permission + audit + rate limit + retry)
│   │   ├── registry.py              # ToolRegistry
│   │   ├── langchain_adapter.py     # BaseTool → StructuredTool via engine
│   │   ├── factory.py               # build_registry(), build_tool_engine()
│   │   └── builtin/
│   │       ├── search.py            # TavilySearchResults wrapper
│   │       ├── langsearch.py        # LangSearch secondary search
│   │       ├── fetch.py             # WebFetchTool (SSRF-protected)
│   │       ├── browser_toolkit.py   # PlaywrightBrowserToolkit wrapper
│   │       ├── filesystem.py        # File/folder tools
│   │       ├── shell.py             # ShellRunTool
│   │       ├── fact_check.py        # FactCheckTool
│   │       ├── content.py           # ContentDraftTool, ContentValidateTool
│   │       ├── social_publish.py    # XPublishTool, LinkedInPublishTool
│   │       └── social_verify.py     # SocialVerifyTool
│   │
│   ├── api/
│   │   ├── router.py
│   │   ├── deps.py                  # FastAPI dependency providers
│   │   └── routes/
│   │       ├── tasks.py
│   │       ├── approvals.py
│   │       ├── browser.py
│   │       ├── content.py
│   │       ├── social.py
│   │       ├── audit.py
│   │       └── health.py
│   │
│   ├── browser/
│   │   ├── session.py               # BrowserSessionManager
│   │   └── selectors.py
│   │
│   ├── content/
│   │   ├── generator.py             # LLMContentGenerator
│   │   ├── tone_safety.py           # ToneSafetyChecker (LLM-backed)
│   │   └── validators.py            # Deterministic validators
│   │
│   ├── db/
│   │   ├── models/
│   │   │   ├── task.py              # Task, TaskStep
│   │   │   ├── agent_run.py         # AgentRun
│   │   │   ├── approval.py          # Approval
│   │   │   ├── tool_call.py         # ToolCall (audit)
│   │   │   ├── browser_session.py   # BrowserSession
│   │   │   ├── research.py          # ResearchSource, ResearchClaim
│   │   │   ├── draft.py             # Draft
│   │   │   ├── social_post.py       # SocialPost, PublishAttempt
│   │   │   ├── verification.py      # VerificationResult
│   │   │   └── user.py              # User
│   │   ├── session.py
│   │   └── base.py
│   │
│   ├── domain/
│   │   └── state_machine.py         # TaskState enum + transition rules
│   │
│   ├── llm/
│   │   ├── base.py                  # ModelClass, RoutingCriteria, ModelSelection
│   │   ├── router.py                # ModelRouter
│   │   ├── usage.py                 # TokenUsage extraction
│   │   └── providers/
│   │       ├── litellm_provider.py  # ChatLiteLLM factory
│   │       └── registry.py
│   │
│   ├── policies/
│   │   ├── approval.py              # Approval policies
│   │   ├── risk.py                  # RiskLevel, ToolPermissions
│   │   └── rate_limit.py            # RateLimiter (token bucket)
│   │
│   ├── research/
│   │   ├── pipeline.py              # DefaultResearchPipeline
│   │   ├── classification.py        # Source classification + freshness
│   │   └── evidence.py              # Evidence helpers
│   │
│   ├── schemas/                     # Pydantic request/response schemas
│   │   ├── approval.py
│   │   ├── audit.py
│   │   ├── browser.py
│   │   ├── content.py
│   │   ├── research.py
│   │   ├── social.py
│   │   └── task.py
│   │
│   ├── services/
│   │   ├── task_service.py
│   │   ├── approval_service.py
│   │   └── audit_service.py         # Secrets audit (regex scan + redaction)
│   │
│   ├── social/
│   │   ├── base.py                  # SocialPlatform protocol
│   │   ├── x_adapter.py             # X/Twitter OAuth2 + API v2
│   │   └── linkedin_adapter.py      # LinkedIn REST API
│   │
│   ├── workers/
│   │   └── task_worker.py           # Background worker (SKIP LOCKED polling)
│   │
│   ├── config.py
│   ├── errors.py
│   ├── logging.py
│   └── main.py
│
├── skills/
│   ├── web-research/
│   │   ├── graph.py
│   │   └── SKILL.md
│   ├── browser-control/
│   │   ├── graph.py
│   │   └── SKILL.md
│   ├── content-generation/
│   │   ├── graph.py
│   │   └── SKILL.md
│   ├── fact-checking/
│   │   ├── graph.py
│   │   └── SKILL.md
│   ├── x_publishing/
│   │   ├── graph.py
│   │   └── SKILL.md
│   ├── linkedin_publishing/
│   │   ├── graph.py
│   │   └── SKILL.md
│   ├── local-system/
│   │   └── graph.py
│   └── packager.py                  # Skill validation + manifest export
│
├── migrations/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── browser/
│   └── fixtures/                    # Adversarial web content payloads
│
├── examples/
├── docs/
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                   # ruff + pytest
│   │   └── test.yml
│   └── PULL_REQUEST_TEMPLATE.md
│
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── alembic.ini
├── .env.example
├── .gitignore
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── PROJECT.md
├── AGENTS.md
└── cli.py                           # Click CLI (approve/cancel/audit/create/track)

---

24. MVP Phases — All Complete

Phase 1 — Foundation ✅
  Python project, FastAPI, config, logging, PostgreSQL, migrations, Docker.

Phase 2 — Agent Core ✅
  LangGraph StateGraph orchestrator, model router (LiteLLM), tool execution engine
  (permission-checked, audited), planner with structured output, PostgresSaver
  checkpointing, BaseCallbackHandler middleware, HITL approval pauses (NodeInterrupt),
  context-quarantine subgraph pattern, cost/usage hooks.

Phase 3 — Browser ✅
  PlaywrightBrowserToolkit integration, browser session pooling, structured page
  observation, select/scroll/wait/download actions, browser error recovery,
  session isolation, browser tests against controlled local pages.

Phase 4 — Research ✅
  Search integration (Tavily), WebFetchTool with SSRF protection, ResearchPipeline
  (search → extract → cross-check → synthesise), source classification, freshness
  weighting, fact-checking subgraph, prompt-injection test fixtures.

Phase 5 — Content ✅
  ContentGenerator (model-router-backed, platform-aware), tone/safety LLM check,
  X thread support, draft editing endpoint.

Phase 6 — Social ✅
  X OAuth2 + API v2, LinkedIn API, publish verification, idempotency enforcement,
  PublishAttempt audit rows, end-to-end mock test (draft → approve → publish → verify).

Phase 7 — Safety ✅
  Approval UI/CLI surface, end-to-end permission enforcement, secrets audit,
  task cancellation (in-flight stop), per-task timeouts, in-process rate limiting.

Phase 8 — Production Hardening ✅
  LangSmith tracing (BaseCallbackHandler), structured retries (tenacity), background
  worker, CLI, full test pyramid, deployment documentation, skills packaging.

---

25. Definition of Done

A feature is complete when: implementation exists, interfaces are typed, errors are
handled, logging exists, permissions are enforced, tests exist, failure behaviour is
defined, documentation exists, configuration is documented, security implications
are reviewed.

For external actions: Execute + Idempotency + Verification + Audit trail.

---

26. Engineering Rules

Prefer: small modules, typed interfaces, explicit state, dependency injection,
async I/O, structured logging, testable services, deterministic validation,
clear boundaries.

Avoid: global mutable state, huge agent prompts, hard-coded credentials, fragile
selectors, unbounded retries, infinite agent loops, implicit side effects, business
logic in API routes, platform-specific logic inside the core agent, shared
MessagesState between subgraph invocations.

---

27. Agent Design Rules

1. Understand before acting.           7. Respect permissions.
2. Plan complex tasks.                 8. Require approval for consequential actions.
3. Use tools, never hallucinate results. 9. Verify external actions.
4. Validate tool inputs.               10. Stop when the task is complete.
5. Treat external content as untrusted. 11. Recover from recoverable failures.
6. Keep task state persistent.         12. Escalate when safe execution is impossible.

---

28. Long-Term Vision

Agent Operator becomes a reusable platform where each capability is a composable
LangGraph skill consumable by Claude Code, Codex, or any agent runtime:

  Claude Code → Agent Operator Skill → Web Research Skill
  Codex       → Agent Operator Skill → Browser Control
  External    → Agent Operator API   → Research + Browser + Social Tools

---

29. Final Principle

«Useful autonomy with controlled execution.»

Understand → Research → Reason → Act → Verify — with the user in control of
consequential actions.

Priority order:
  Reliability > autonomy
  Verification > assumption
  Explicit permissions > implicit trust
  Human approval > irreversible autonomous action
  Composable subgraphs > monolithic agents
  Production engineering > demos
  Reusable skills > one-off workflows

---

30. Implementation Instruction

Treat this document together with AGENTS.md as the governing engineering specification.

When implementation details conflict with this document:
1. Preserve security and user-control requirements.
2. Preserve explicit approval boundaries.
3. Preserve verification requirements.
4. Prefer modular and extensible architecture.
5. Document meaningful deviations.
6. Update project documentation when architectural decisions change.
