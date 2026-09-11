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
  PostgreSQL, Redis, migrations, Docker).
- **Phase 2 — Agent Core**: ✅ done. Model router runs on **LiteLLM** via
  `langchain-litellm` (`ChatLiteLLM`). Orchestrator loop, tool execution
  engine (permission-checked, audited), planner with structured output,
  agent wiring, HITL approvals, and cost/usage hooks are in place. See
  "Decisions already made" below.
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

## Phase 3 — Browser

- [ ] Browser session pooling/reuse across steps of one task (currently
  `BrowserSessionManager` opens a session per API call).
- [ ] Structured page observation: bounded, targeted extraction (visible
  text, interactive elements, ARIA tree) instead of raw DOM — PROJECT.md
  section 13 explicitly warns against sending oversized DOM to the model.
- [ ] `select`, `scroll`, `wait`, `download`, new-tab/switch-tab actions
  (only navigate/inspect/click/type/screenshot exist today).
- [ ] Browser error recovery: crashed page/context detection + safe restart
  (AGENTS.md rule 188).
- [ ] Session isolation guarantees between concurrent tasks/users
  (AGENTS.md rule 88) — currently one shared `BrowserSessionManager`
  singleton; needs per-task/user scoping.
- [ ] `BrowserAgent.decide`/`act`: turn planner steps into bounded
  browser-tool call sequences (still explicitly **not** autonomous
  multi-site workflows at this stage — keep scope narrow and test-page
  driven per PROJECT.md section 47).
- [ ] Browser tests against controlled local test pages (`tests/browser/`
  is empty) — never against live third-party sites in CI.

## Phase 4 — Research

- [ ] **Search integration** — *Needs a decision*: which search API
  (Tavily, Serper/SerpAPI, Bing Search, Exa, ...)? Affects `WebSearchTool`
  and `.env.example`.
- [ ] `WebSearchTool` / `WebFetchTool` with SSRF protections (AGENTS.md
  rule 168–169: validate/restrict fetch targets).
- [ ] Document loaders + text splitters (`langchain-text-splitters`,
  already pulled in transitively) for extracting evidence from fetched
  pages — only where it improves retrieval quality (AGENTS.md rule 101).
- [ ] Implement `ResearchPipeline` (`app/research/pipeline.py`): search →
  extract → cross-check → synthesize, backed by real tools and the
  `REASONING` model class.
- [ ] Source classification (primary/official/secondary/community/
  unverified) and freshness weighting.
- [ ] Fact-checking agent: verify claims against sources before they reach
  content generation; never let a claim through without recorded evidence
  (AGENTS.md rules 98–99, 115).
- [ ] Prompt-injection tests: fetched content containing "ignore previous
  instructions" style payloads must never change agent behavior (AGENTS.md
  rule 203) — add adversarial fixtures.
- [ ] Research tests: source ranking, conflict surfacing, citation
  correctness.

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
  (AGENTS.md rules 185–186) — *needs a decision* on backend (Redis token
  bucket vs a library).

## Phase 8 — Production Hardening

- [ ] Observability/tracing — *needs a decision*: LangSmith (native
  LangChain tracing) vs OpenTelemetry (vendor-neutral, fits the "avoid
  vendor lock-in" principle already applied to the LLM layer) vs both.
- [ ] Structured retries with bounded exponential backoff using the
  existing `tenacity` dependency, applied to model calls, tool calls, and
  publish attempts.
- [ ] Background worker (`app/workers/`, currently an empty placeholder) so
  long-running tasks don't block a request — *needs a decision*: plain
  asyncio worker polling Postgres/Redis vs Celery/RQ/Arq.
- [ ] CLI (`PROJECT.md` section 37): `agent-operator task/research/
  draft-x/approve/status`, calling the same services as the API — no
  duplicated business logic.
- [ ] CI pipeline (GitHub Actions): ruff + mypy + pytest on every PR; this
  repo currently has no `.github/workflows/`.
- [ ] Full test pyramid: `tests/browser/` and `tests/e2e/` are still empty
  directories; fill in per Phase 3/6 items above.
- [ ] Deployment documentation: how to run this in a real environment
  (managed Postgres/Redis, secrets, Playwright browser provisioning).
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

1. **Orchestration style** — a hand-rolled loop over `app.agents` vs
   adopting LangGraph for the planner/orchestrator's branching and
   checkpointing. LangGraph would replace parts of `app/agents/orchestrator.py`
   and `app/domain/state_machine.py`'s runtime role (the state machine's
   states themselves stay either way).
2. **Search provider** for Phase 4 (Tavily / Serper / Bing / Exa / other).
3. **Credential storage** for OAuth tokens (X/LinkedIn) once real auth
   lands — encrypted DB column vs a secret manager (AWS Secrets Manager,
   Vault, etc.).
4. **Background worker technology** — plain asyncio poller vs Celery/RQ/Arq.
5. **Observability backend** — LangSmith vs OpenTelemetry vs both.
6. **Rate-limiting backend** — Redis-based token bucket vs a library
   (e.g. `slowapi`, `limits`).

Resolve each when its phase starts, not before — deciding early risks
guessing wrong before the surrounding code exists to validate the choice.
