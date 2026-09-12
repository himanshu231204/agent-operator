# Agent Operator — Production Roadmap

Tracks the work remaining to take Agent Operator from foundation to the
production system described in `PROJECT.md`. Organized by the MVP phases in
`PROJECT.md` section 54. Check items off in PRs; keep this file in sync with
reality — an unchecked item here is the source of truth for "not done yet."

Every item must still satisfy `PROJECT.md`/`AGENTS.md` when implemented:
typed interfaces, dependency injection, tests, structured logging/errors,
explicit approval gates for consequential actions, and verification before
marking an external action successful. "Done" means the Definition of Done
in `PROJECT.md` section 55, not just "the code runs once."

---

## Status

- **Phase 1 — Foundation**: ✅ done (Python project, FastAPI, config, logging,
  PostgreSQL, migrations, Docker).
- **Phase 2 — Agent Core**: ✅ done. Model router runs on **LiteLLM** via
  `langchain-litellm` (`ChatLiteLLM`). Orchestrator loop, tool execution
  engine (permission-checked, audited), planner with structured output,
  agent wiring, HITL approvals, and cost/usage hooks are in place. See
  "Decisions already made" below.
- **Agent framework decision**: ✅ decided — **LangGraph** (`langgraph.prebuilt.create_react_agent`)
  is the chosen approach for all specialized agents (Research, Browser, Content,
  Fact Checker, Social, Verification). Each agent is a compiled LangGraph
  **subgraph** with isolated `MessagesState` (context quarantine). The outer
  orchestrator is a `StateGraph` that calls subgraphs per plan step.
- **Checkpointing**: ✅ decided — `PostgresSaver` from `langgraph-checkpoint-postgres`
  is the sole checkpointing backend; wired into `graph.compile(checkpointer=...)`.
- **Built-in tools**: ✅ decided — `langchain-community` toolkits (TavilySearchResults,
  PlaywrightBrowserToolkit, etc.) are the first choice for standard capabilities;
  always wrapped through `ToolExecutionEngine`.
- **Middleware**: ✅ decided — LangChain `BaseCallbackHandler` + `RunnableConfig`
  is the instrumentation layer; LangSmith is the default backend.
- **Memory**: ✅ decided — `MessagesState` in-graph, `ConversationSummaryMemory` /
  vector store for cross-task recall.
- **Skills**: ✅ decided — reusable packaged LangGraph subgraphs under `skills/`,
  each with a `SKILL.md` contract, consumable via API or direct import.
- **Observability backend**: ✅ decided — LangSmith via `BaseCallbackHandler`;
  OTel export is a future option via a custom handler, not a parallel system.
- **Phases 3–8**: not started.

---

## Decisions already made

- **Model routing → LiteLLM.** `app/llm/providers/litellm_provider.py`
  wraps `langchain_litellm.ChatLiteLLM`. `ModelRoutingSettings` model names
  are LiteLLM model strings (`"gpt-4o-mini"`, `"claude-3-5-sonnet-20241022"`,
  `"gemini/gemini-1.5-pro"`, `"openrouter/anthropic/claude-3.5-sonnet"`).
  Swapping/adding a vendor is a config change, not a code change. An
  optional self-hosted LiteLLM proxy ("omnirouter": `LITELLM_API_BASE` /
  `LITELLM_API_KEY`) can centralize keys, budgets, and cross-provider
  fallback behind one gateway instead of calling vendors directly.
  Providers configured: OpenAI, Anthropic, Gemini, OpenRouter.
- The `fake` provider (`FakeListChatModel`) stays registered for offline
  unit tests — never hits a network in CI.

---

## Phase 2 — Agent Core

- [x] **Orchestrator execution loop** (`app/agents/orchestrator.py`):
  observe → plan → per-step decide → approve-if-needed → execute → update
  state → recover, enforcing `LimitSettings` (max iterations, tool calls,
  execution time, retries).
- [x] **Planner agent**: LLM-with-structured-output (routed via
  `ModelRouter`, falls back to a single-step plan when the underlying
  provider does not support structured output — the `fake` provider used
  in CI). LangGraph revisit deferred to Phase 8 once branching/retry
  patterns emerge from real usage.
- [x] Wire each placeholder agent (`research_agent.py`, `browser_agent.py`,
  `content_agent.py`, `fact_checker.py`, `social_agent.py`,
  `verification_agent.py`, `recovery_agent.py`) to run through the tool
  execution engine + policy (recovery agent stays deterministic — no LLM
  call).
- [x] **Tool execution engine** (`app/tools/executor.py`): central
  dispatcher checks `ToolPermissions` (risk level, approval,
  authentication) *before* calling the tool, and persists a `ToolCall`
  row per invocation (AGENTS.md rules 154–158).
- [x] Persist `AgentRun`/`ToolCall` rows from real agent execution.
- [x] Concrete LangChain tool wrappers (`app/tools/langchain_adapter.py`):
  adapt `BaseTool` to `langchain_core.tools.StructuredTool` while routing
  execution through the engine (never bypassing permission checks).
- [x] Human-in-the-loop: orchestrator creates an `Approval` via
  `ApprovalService`, transitions to `WAITING_FOR_APPROVAL`, and returns;
  the next `run(task_id)` call resumes from the persisted plan with
  approved actions in `ExecutionContext.approved_actions`.
- [x] Cost/usage tracking: `app/llm/usage.py` normalizes LiteLLM /
  LangChain token metadata into a persistable dict (wiring the numbers
  onto `AgentRun.output` is a follow-up once real model calls are made).
- [x] Unit + integration tests for the orchestrator loop: happy path,
  approval pause, resume after approval, max-iteration cutoff, recovery
  classification.
- [ ] Add `langgraph`, `langgraph-checkpoint-postgres`, `langchain`,
  `langchain-community` to `pyproject.toml` and verify dependency resolution.
- [ ] Wire `AsyncPostgresSaver` into the orchestrator graph compilation
  (`graph.compile(checkpointer=postgres_saver)`).
- [ ] Implement a `BaseCallbackHandler` subclass for structured logging /
  LangSmith tracing and inject it via `RunnableConfig` on every graph call.
- [ ] Define and document the subgraph invocation contract: the typed input
  dict the orchestrator passes to each subgraph and the typed output dict it
  expects back (eliminates implicit message-history coupling).

## Phase 3 — Browser

- [x] **Browser channel configurability** (`BrowserHeadlessMode`, `BrowserChannel`
  in `app/config.py`): launch any Chromium-based browser via Playwright
  (`chromium`, `chrome`, `msedge`, `brave` — Brave requires `executable_path`).
  Platform-aware headless negotiation (new vs old headless on Windows/CI).
  See `.env.example` for the new `BROWSER_HEADLESS_MODE` / `BROWSER_CHANNEL`
  / `BROWSER_EXECUTABLE_PATH` keys.
- [x] Browser session pooling/reuse across steps of one task — orchestrator
  creates one `BrowserSession` per task, passes `session_id` through
  `ExecutionContext`, and closes it on task complete/fail/cancel.
- [x] Structured page observation: bounded, targeted extraction (visible text,
  interactive elements, ARIA tree) instead of raw DOM (PROJECT.md §13).
  `BrowserSession.inspect()` now returns `BrowserPageObservation`;
  `extract_text(selector, max_chars)` supports targeted/sized extraction.
- [x] `select`, `download`, `new_tab`, `switch_tab`, `list_tabs` actions
  implemented as typed tools + `BrowserSession` methods (navigate/inspect/click/
  type/screenshot already existed).
- [x] Browser error recovery: crashed page/context detection (`page.on("crash")`
  + `page.on("load")`) + safe restart with single retry, then escalation
  (AGENTS.md rule 188).
- [x] Session isolation between concurrent tasks/users (AGENTS.md rule 88):
  per-task session scoping via orchestrator-owned `BrowserSessionManager`.
- [x] Browser subgraph (`app/agents/graphs/browser.py`): bounded browser-tool
  call sequences within the `create_react_agent` ReAct loop.
- [x] Browser tests against controlled local test pages
  (`tests/unit/test_browser_session.py`, `tests/unit/test_browser_tools.py`).

## Phase 4 — Research

- [x] **Search integration** — *resolved*: **Tavily** is the primary search
  API (`WebSearchTool` → `web_search`, already registered) with **LangSearch**
  as a secondary fall-back (`lang_search`) when Tavily returns empty. Both are
  configured via `TAVILY_API_KEY` / `LANGSEARCH_API_KEY` in `.env.example`.
  Detailed decision record in `docs/phase-4-plan.md`.
- [x] `WebSearchTool` / `WebFetchTool` with SSRF protections (AGENTS.md
  rule 168–169: validate/restrict fetch targets) — `WebFetchTool` already has
  `_guard_url` SSRF protection (scheme allow-list, no private/loopback hosts);
  tests pass.
- [x] Document loaders + text splitters (`langchain-text-splitters`,
  already pulled in transitively) for extracting evidence from fetched
  pages — only where it improves retrieval quality (AGENTS.md rule 101):
  `RecursiveCharacterTextSplitter` in `DefaultResearchPipeline._chunk_text`,
  applied only when page length > 4000 chars (single chunk for short pages).
- [x] Implement `ResearchPipeline` (`app/research/pipeline.py`): search →
  extract → cross-check → synthesize, backed by real tools and the
  `REASONING` model class — concrete `DefaultResearchPipeline` drives
  `web_search`/`web_fetch`/`lang_search` through the `ToolExecutionEngine`;
  synthesis routes via `ModelRouter` with `RoutingCriteria(requires_reasoning=True,
  conflicting_evidence=True)`.
- [x] Source classification (primary/official/secondary/community/
  unverified) and freshness weighting — `app/research/classification.py`.
- [x] Fact-checking agent: `FactCheckTool` (`app/tools/builtin/fact_check.py`)
  verifies claims against sources via web search + fetch, routed through the
  engine; deterministic signal logic (no LLM verdict). Registered as
  `fact_check` in the tool factory.
- [x] Prompt-injection tests: fetched content containing "ignore previous
  instructions" style payloads must never change agent behavior (AGANS.md
  rule 203) — adversarial fixtures in `tests/fixtures/adversarial_web_content.py`
  (6 payloads) + `tests/unit/test_research_prompt_injection.py`; deterministic
  sentence sanitizer in `_extract_claims_from_text` strips injected directives.
- [x] Research tests: source ranking, conflict surfacing, citation
  correctness — `tests/unit/test_research_pipeline.py` (13 tests),
  `tests/unit/test_research_classification.py` (34 tests),
  `tests/unit/test_fact_check_tool.py` (18 tests).

### Phase 4 detailed implementation plan (checklist)

See `docs/phase-4-plan.md` for the full plan. Summary of what was built:

- [x] Resolve search provider decision (Tavily primary, LangSearch fallback).
- [x] `app/research/classification.py`: `classify_source`, `classify_source_obj`,
      `freshness_score`, `sort_by_confidence_and_freshness`; tests.
- [x] `app/tools/builtin/fact_check.py`: `FactCheckTool` (LOW risk, read-only,
      dispatches sub-tools via engine); `FactCheckToolInput`/`FactCheckToolOutput`
      with typed verdict constants; tests.
- [x] Register `fact_check` in `app/tools/factory.py` + wire engine in
      `build_tool_engine`; update registry test.
- [x] `app/schemas/research.py`: add `ResearchResult` schema.
- [x] `app/research/pipeline.py`: concrete `DefaultResearchPipeline`
      (search → extract → cross-check → synthesize → run) using REASONING
      model + text splitters; prompt-injection sanitizer.
- [x] `tests/fixtures/adversarial_web_content.py`: 6 injection payloads.
- [x] `tests/unit/test_research_prompt_injection.py`: fetch preserves content,
      pipeline doesn't echo instructions as facts, SSRF guards file:// URLs.
- [x] `tests/unit/test_research_pipeline.py`: source ranking, classification,
      max_sources, fallback, extract, cross-check, synthesize routing,
      conflict surfacing, citation correctness.
- [x] `tests/unit/test_research_classification.py`: all source types, freshness
      decay, ranking, edge cases.
- [x] `tests/unit/test_fact_check_tool.py`: verdict logic, evidence aggregation,
      conflicting evidence, empty results, unsupported claims, sub-tool routing.
- [x] `docs/phase-4-plan.md`: full plan + decision record.

## Phase 5 — Content

- [ ] Implement `ContentGenerator` (`app/content/generator.py`) using the
  model router — draft from validated research claims, platform-aware
  (X vs LinkedIn tone/length), never inventing stats/quotes/sources
  (AGENTS.md rule 120).
- [ ] Tone/safety checks: currently only length/links/duplicates are
  deterministic (`app/content/validators.py`); tone and safety need an
  LLM-backed check layered on top (AGENTS.md rule 272 — LLM only where
  deterministic validation isn't sufficient).
- [ ] Thread support for X (multi-post drafts with ordering).
- [ ] Draft editing endpoint/flow (PROJECT.md rule 122: drafts must be
  editable before approval) — currently create/read only.
- [ ] Content generation tests using the `fake` LiteLLM provider (no live
  API calls in CI).

## Phase 6 — Social

- [ ] **X/Twitter**: real OAuth2 flow + API v2 client behind `XAdapter`
  (`create_draft`/`publish`/`verify` currently raise `NotImplementedError`).
  Publish path must check idempotency (`SocialPost.idempotency_key`) before
  calling the API (PROJECT.md section 31).
- [ ] **LinkedIn**: same shape via `LinkedInAdapter` and the LinkedIn API.
- [ ] Publish verification: after publishing, re-fetch the post and confirm
  content/destination match before marking `VERIFIED` (PROJECT.md section
  30) — never trust a 200 response alone.
- [ ] `PublishAttempt` rows written on every attempt (model exists, nothing
  writes to it yet).
- [ ] CredentialProvider abstraction (PROJECT.md section 24) so OAuth
  tokens aren't just raw env vars long-term — *needs a decision* on token
  storage (encrypted DB column vs external secret manager) before this
  lands in a real deployment.
- [ ] End-to-end test: draft → approve → publish (mocked adapters) →
  verify → complete, per PROJECT.md section 47. Never hit real X/LinkedIn
  accounts from automated tests (AGENTS.md rule 202).

## Phase 7 — Safety

- [ ] Approval gateway: a real UI/CLI surface for `GET/POST
  /tasks/{id}/approval` (today it's API-only) so a human can actually see
  and act on pending approvals.
- [ ] Enforce tool permissions centrally end-to-end: the tool execution
  engine (Phase 2) must consult `ToolPermissions` before *every* call, not
  just log it.
- [ ] Prompt-injection defense tests across research + browser content
  paths (AGENTS.md rule 203) — expand beyond the Phase 4 fixtures to cover
  browser-extracted text too.
- [ ] Secrets audit: confirm no API key, token, or cookie ever reaches a
  log line, prompt, or DB column in plaintext once real credentials exist
  (AGENTS.md rules 163–166).
- [ ] Task cancellation: `TaskService.cancel_task` exists at the DB/state
  level, but nothing yet stops an in-flight orchestrator loop or browser
  session when cancellation is requested (PROJECT.md section 28).
- [ ] Timeouts: wire `LimitSettings.max_execution_seconds` into the
  orchestrator loop (currently only stored in config, not enforced).
- [ ] Rate limiting: per-provider/per-tool throttling + concurrency limits
  (AGENTS.md rules 185–186) — use `slowapi` (in-process) for now; revisit
  if multi-process workers are added.

## Phase 8 — Production Hardening

- [ ] Observability/tracing — *needs a decision*: LangSmith (native
  LangChain tracing) vs OpenTelemetry (vendor-neutral, fits the "avoid
  vendor lock-in" principle already applied to the LLM layer) vs both.
- [ ] Structured retries with bounded exponential backoff using the
  existing `tenacity` dependency, applied to model calls, tool calls, and
  publish attempts.
- [ ] Background worker (`app/workers/`, currently an empty placeholder) so
  long-running tasks don't block a request — implement as a plain asyncio
  loop polling PostgreSQL (`SELECT ... FOR UPDATE SKIP LOCKED`).
- [ ] CLI (`PROJECT.md` section 37): `agent-operator task/research/
  draft-x/approve/status`, calling the same services as the API — no
  duplicated business logic.
- [ ] CI pipeline (GitHub Actions): ruff + mypy + pytest on every PR; this
  repo currently has no `.github/workflows/`.
- [ ] Full test pyramid: `tests/browser/` and `tests/e2e/` are still empty
  directories; fill in per Phase 3/6 items above.
- [ ] Deployment documentation: how to run this in a real environment
  (managed Postgres, secrets, Playwright browser provisioning).
- [ ] `CLAUDE.md`: referenced by `PROJECT.md` section 35 and `AGENTS.md`
  section 1 as a first-class doc; doesn't exist in the repo yet.
- [ ] `skills/` packaging (PROJECT.md section 34): expose
  web-research/browser-control/content-generation/fact-checking/
  x-publishing/linkedin-publishing as composable, documented skills once
  their underlying capabilities are real.

---

## Needs a decision (flagging now, not guessing)

These materially affect architecture and are called out rather than
silently decided:

1. ~~**Orchestration style**~~ — **resolved**: LangGraph `create_react_agent`
   for all specialized agents. The outer orchestrator and task state machine
   stay; individual agent `decide`/`act` stubs are replaced by compiled
   LangGraph ReAct graphs.
2. ~~**Search provider** for Phase 4~~ — **resolved**: Tavily primary
   (`web_search`) + LangSearch fallback (`lang_search`); see `docs/phase-4-plan.md`.
3. **Credential storage** for OAuth tokens (X/LinkedIn) once real auth
   lands — encrypted DB column vs a secret manager (AWS Secrets Manager,
   Vault, etc.).
4. **Background worker technology** — plain asyncio poller vs Celery/RQ/Arq.
5. ~~**Observability backend**~~ — resolved: LangChain `BaseCallbackHandler` + LangSmith as the default backend; OTel export is a future option via a custom handler, not a parallel system.
6. ~~**Rate-limiting backend**~~ — resolved: `slowapi` in-process for now; revisit if multi-worker deployment is added.

Resolve each when its phase starts, not before — deciding early risks
guessing wrong before the surrounding code exists to validate the choice.
