# Graph Report - phase-5-content-generation  (2026-09-12)

## Corpus Check
- Corpus is ~35,121 words - fits in a single context window. You may not need a graph.

## Summary
- 1020 nodes · 2810 edges · 67 communities (36 shown, 7 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 318 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Web Fetch Tool & Errors
- Content API Routes
- LLM Content Generator
- Database Models
- Social Publishing API
- Agent Graph Builders
- LangSearch Tool
- Orchestrator & Recovery
- Browser Toolkit
- Architecture Concepts & Docs
- Model Routing Config
- Task State Machine
- Base Agent Interface
- Approval Policies
- LLM Provider Settings
- Browser API Routes
- Browser DOM Selectors
- Model Selection Helpers
- Orchestrator Core Logic
- API Dependency Injection
- Tool Executor Tests
- Approvals API Routes
- Planner & Plan Steps
- Task Management API
- Operator Callback Handler
- App Configuration
- Approval Service
- LLM Token Usage
- Tool Registry Tests
- Logging & Callbacks
- Settings Models
- Browser Control Skill
- Database Session
- Base Tool Interface
- Fact Checking Skill
- X Publishing Skill
- Browser Session
- Orchestrator Integration Tests
- Agent Graphs Package
- Builtin Tools Package
- Workers Package
- CI/CD Pipelines
- Package Metadata

## God Nodes (most connected - your core abstractions)
1. `ToolExecutionEngine` - 62 edges
2. `RiskLevel` - 61 edges
3. `ModelRouter` - 59 edges
4. `ToolError` - 56 edges
5. `ToolRegistry` - 46 edges
6. `TaskState` - 37 edges
7. `Orchestrator` - 35 edges
8. `ExecutionContext` - 34 edges
9. `TaskService` - 32 edges
10. `Base` - 31 edges

## Surprising Connections (you probably didn't know these)
- `test_content_tools_collectible()` --calls--> `collect_tools()`  [EXTRACTED]
  tests/integration/test_content_graph.py → app/agents/graphs/_helpers.py
- `test_planner_empty_instruction_returns_empty_plan()` --uses--> `Plan`  [INFERRED]
  tests/unit/test_planner.py → app/agents/planner.py
- `test_planner_fake_provider_falls_back_to_single_step()` --uses--> `Plan`  [INFERRED]
  tests/unit/test_planner.py → app/agents/planner.py
- `_build_orchestrator()` --uses--> `PlannerAgent`  [INFERRED]
  tests/integration/test_orchestrator.py → app/agents/planner.py
- `build_skill()` --uses--> `BrowserSessionManager`  [INFERRED]
  skills/browser-control/graph.py → app/browser/session.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Social Publishing Skills (X + LinkedIn)** — skills_x_publishing_skill_md_x_skill, skills_linkedin_publishing_skill_md_linkedin_skill, concept_social_platform_protocol, concept_approval_gate, concept_idempotency [INFERRED 0.95]
- **Research Tool Pipeline (search + fetch + engine + registry)** — concept_web_search_tool, concept_web_fetch_tool, concept_tool_execution_engine, concept_tool_registry, skills_web_research_skill_md_web_research_skill [EXTRACTED 1.00]
- **Agent Subgraph Infrastructure (LangGraph + PostgresSaver + Callbacks)** — concept_langgraph_subgraph, concept_postgres_saver, concept_operator_callback_handler, concept_context_quarantine [EXTRACTED 1.00]

## Communities (67 total, 7 thin omitted)

### Community 0 - "Web Fetch Tool & Errors"
Cohesion: 0.05
Nodes (92): ToolError, _extract_text(), _guard_url(), BaseModel, Web fetch tool (PROJECT.md section 8, phase 4). Implements WebFetchTool — an…, Raise ToolError if *url* targets a private/internal address., Strip HTML tags and truncate to _MAX_CONTENT_CHARS., WebFetchInput (+84 more)

### Community 1 - "Content API Routes"
Cohesion: 0.05
Nodes (74): create_draft(), get_draft(), DbSessionDep, get, post, UUID, Content draft routes (PROJECT.md sections 16-17, 36). Publishing is a separate,…, update_draft() (+66 more)

### Community 2 - "LLM Content Generator"
Cohesion: 0.05
Nodes (49): ContentGenerator, LLMContentGenerator, ABC, Platform, Content generation interface and LLM-backed implementation (PROJECT.md section…, Generate a draft for ``platform``. Must never invent statistics, quotes,…, LLM-backed content generator using the project model router., has_conflicting_evidence() (+41 more)

### Community 3 - "Database Models"
Cohesion: 0.13
Nodes (34): Base, SQLAlchemy 2.x declarative base and shared column mixins., Declarative base shared by every ORM model., TimestampMixin, UUIDPrimaryKeyMixin, AgentRun, Agent run and tool-call ORM models (execution observability)., ToolCall (+26 more)

### Community 4 - "Social Publishing API"
Cohesion: 0.10
Nodes (29): _load_approved_draft(), publish_linkedin(), publish_x(), ApprovalServiceDep, DbSessionDep, Draft, post, Social publishing routes (PROJECT.md sections 18-20, 36). Real publishing is… (+21 more)

### Community 5 - "Agent Graph Builders"
Cohesion: 0.10
Nodes (32): build_graph(), Browser agent subgraph (PROJECT.md section 8, phase 3). Builds a LangGraph…, Return the compiled browser ReAct subgraph., Content agent subgraph (PROJECT.md section 8, phase 5). Builds a LangGraph…, build_graph(), Fact-checker agent subgraph (PROJECT.md section 8, phase 4). Builds a LangGraph…, Return the compiled fact-checker ReAct subgraph., collect_tools() (+24 more)

### Community 6 - "LangSearch Tool"
Cohesion: 0.13
Nodes (34): LangSearchInput, LangSearchOutput, LangSearchTool, BaseModel, LangSearch web-search tool. Wraps the LangSearch REST API…, BaseModel, Web search tool (PROJECT.md section 8, phase 4). Implements WebSearchTool — a…, SearchResult (+26 more)

### Community 7 - "Orchestrator & Recovery"
Cohesion: 0.14
Nodes (28): Agent orchestrator (PROJECT.md sections 8-9, AGENTS.md rules 56-59). Drives the…, Any, StrEnum, Recovery agent (PROJECT.md section 29). Given a failure, decides whether the…, RecoveryAction, RecoveryAgent, LimitSettings, Bounds preventing unbounded agent loops and runaway cost (PROJECT.md 9, 40). (+20 more)

### Community 8 - "Browser Toolkit"
Cohesion: 0.09
Nodes (27): build_browser_tools(), StructuredTool, Playwright browser toolkit wrapper (PROJECT.md section 8, phase 3). Wraps…, Return permission-aware StructuredTools for each browser action., AsyncSession, Executes registered tools while enforcing permissions + audit., ToolExecutionEngine, _input_model_for() (+19 more)

### Community 9 - "Architecture Concepts & Docs"
Cohesion: 0.10
Nodes (33): Agent Operator Platform (AGENTS.md), Claude Code Operating Guide (CLAUDE.md), Human Approval Gateway (NodeInterrupt), Content Generation Pipeline (Research→Draft→Fact Check→Approval→Publish), Context Quarantine Pattern, Idempotency (action_id + content_hash), LangGraph ReAct Subgraph (create_react_agent), Model Classes (FAST/TOOL_CALLING/REASONING/STRONGEST) (+25 more)

### Community 10 - "Model Routing Config"
Cohesion: 0.11
Nodes (23): build_graph(), Return the compiled content-generation ReAct subgraph., build_graph(), Return the compiled research ReAct subgraph. Tools not yet registered are…, ModelRoutingSettings, Model names are LiteLLM model strings, e.g. ``"gpt-4o-mini"``,…, ModelRouter, engine() (+15 more)

### Community 11 - "Task State Machine"
Cohesion: 0.17
Nodes (23): can_cancel(), can_transition(), StrEnum, Task state machine (PROJECT.md section 10, AGENTS.md section 6). Framework-…, Return whether ``current -> target`` is an allowed transition., Validate and perform a state transition, raising on invalid moves. Example:…, TaskState, transition() (+15 more)

### Community 12 - "Base Agent Interface"
Cohesion: 0.14
Nodes (19): Agent, AgentDecision, AgentObservation, AgentResult, ABC, Any, BaseModel, Base agent interfaces (PROJECT.md sections 8-9). Agents are not necessarily… (+11 more)

### Community 13 - "Approval Policies"
Cohesion: 0.14
Nodes (19): build_approval_request(), Approval policy (PROJECT.md section 21, AGENTS.md section 13). Pure,…, Build the approval request shown to the user (PROJECT.md section 21). Callers…, requires_approval(), StrEnum, Risk classification (PROJECT.md section 22). ``RiskLevel`` is the single…, LOW: read-only research. MEDIUM: logged-in interactions, drafts. HIGH: external…, RiskLevel (+11 more)

### Community 14 - "LLM Provider Settings"
Cohesion: 0.14
Nodes (21): LLMProviderSettings, Credentials/config for LangChain-compatible model providers. No single provider…, LLMProviderFactory, BaseChatModel, Protocol, Creates a LangChain ``BaseChatModel`` for a given model name., build_litellm_provider(), LiteLLM-backed provider (PROJECT.md section 6, AGENTS.md section 3).… (+13 more)

### Community 15 - "Browser API Routes"
Cohesion: 0.12
Nodes (18): close_session(), get_session(), open_session(), get, post, Browser session routes (PROJECT.md sections 11, 36). Foundation only: opening a…, health(), get (+10 more)

### Community 16 - "Browser DOM Selectors"
Cohesion: 0.15
Nodes (13): Page, SelectorStrategy, Resilient selector strategy (PROJECT.md section 12, AGENTS.md rules 77-84).…, Build a Playwright ``Locator`` for the given strategy. ``coordinates`` has no…, resolve_locator(), BrowserSession, SelectorStrategy, Browser session abstraction over Playwright (PROJECT.md section 11). Keeps the… (+5 more)

### Community 17 - "Model Selection Helpers"
Cohesion: 0.19
Nodes (19): Shared utilities for building LangGraph agent subgraphs. Every…, ModelClass, ModelSelection, BaseModel, StrEnum, LangChain-compatible LLM abstraction. The application depends on…, Model classes the router picks between (PROJECT.md section 7)., Signals the model router uses to pick a model class. Mirrors the routing… (+11 more)

### Community 18 - "Orchestrator Core Logic"
Cohesion: 0.22
Nodes (8): Orchestrator, OrchestratorState, Any, Exception, UUID, Invoke the compiled LangGraph subgraph for *step* in isolation. Each invocation…, In-memory execution state for one ``run()`` invocation., Wires compiled LangGraph subgraphs together under configured limits. ``graphs``…

### Community 19 - "API Dependency Injection"
Cohesion: 0.13
Nodes (16): _browser_manager(), get_approval_service(), get_browser_manager(), get_task_service(), get_tool_engine(), get_tool_registry(), DbSessionDep, FastAPI dependency providers. Routes depend on these instead of constructing… (+8 more)

### Community 20 - "Tool Executor Tests"
Cohesion: 0.19
Nodes (15): _AuthRequired, _Boom, engine(), _High, _In, _Low, _Out, BaseModel (+7 more)

### Community 21 - "Approvals API Routes"
Cohesion: 0.23
Nodes (13): decide_approval(), get_approval(), ApprovalServiceDep, get, post, UUID, Approval routes (PROJECT.md section 36, section 21)., ApprovalDecision (+5 more)

### Community 22 - "Planner & Plan Steps"
Cohesion: 0.33
Nodes (13): Plan, PlanStep, BaseModel, One step in an execution plan., An ordered plan produced by :class:`PlannerAgent`., _build_orchestrator(), Orchestrator loop: end-to-end run against an in-memory SQLite db and stub…, A step with no matching graph key produces a failed step, not a crash. (+5 more)

### Community 23 - "Task Management API"
Cohesion: 0.30
Nodes (12): cancel_task(), create_task(), get_task(), get, post, UUID, Task routes (PROJECT.md section 36). Thin: all logic lives in…, BaseModel (+4 more)

### Community 24 - "Operator Callback Handler"
Cohesion: 0.23
Nodes (6): OperatorCallbackHandler, Any, UUID, Structured-logging callback for LangGraph agent runs. Phase 8 implementation:…, BaseCallbackHandler, BaseException

### Community 25 - "App Configuration"
Cohesion: 0.26
Nodes (10): get_settings(), Return the process-wide settings singleton. Cached so configuration is parsed…, Connection, _database_url(), _do_run_migrations(), Alembic environment configured for the application's async SQLAlchemy engine.…, run_migrations_offline(), run_migrations_online() (+2 more)

### Community 26 - "Approval Service"
Cohesion: 0.36
Nodes (6): Approval, ValidationError, ApprovalService, AsyncSession, UUID, Approval service (PROJECT.md section 21). Approving a request resumes the task…

### Community 27 - "LLM Token Usage"
Cohesion: 0.24
Nodes (9): extract_usage(), Any, LLM usage extraction (PROJECT.md section 40). LiteLLM (and LangChain over it)…, Return a normalized :class:`TokenUsage` for a LangChain/LiteLLM reply. Silently…, TokenUsage, Token usage extraction (PROJECT.md section 40)., test_extract_usage_from_ai_message_usage_metadata(), test_extract_usage_from_response_metadata_token_usage() (+1 more)

### Community 28 - "Tool Registry Tests"
Cohesion: 0.36
Nodes (8): EchoInput, EchoOutput, EchoTool, FailingTool, BaseModel, test_registry_lookup_and_missing_tool(), test_tool_call_returns_output(), test_tool_wraps_unexpected_exceptions_as_tool_error()

### Community 29 - "Logging & Callbacks"
Cohesion: 0.22
Nodes (7): LangChain callback handler for agent run instrumentation (PROJECT.md section…, bind_context(), get_logger(), Structured logging setup (PROJECT.md section 39, AGENTS.md section 19). Every…, Return a structlog bound logger, optionally namespaced., Bind correlation identifiers (request_id, task_id, run_id, ...) to context., BoundLogger

### Community 30 - "Settings Models"
Cohesion: 0.31
Nodes (9): ApplicationSettings, DatabaseSettings, LoggingSettings, Strongly typed application configuration. Settings are grouped by category…, Top-level settings aggregating every configuration category., SecuritySettings, Settings, SocialSettings (+1 more)

### Community 31 - "Browser Control Skill"
Cohesion: 0.18
Nodes (8): build_skill(), CompiledGraph, Browser Control skill — compiled LangGraph subgraph. Contract: see SKILL.md in…, Return the compiled browser-control skill subgraph., build_skill(), CompiledGraph, Content Generation skill — compiled LangGraph subgraph. Contract: see SKILL.md…, Return the compiled content-generation skill subgraph.

### Community 32 - "Database Session"
Cohesion: 0.36
Nodes (7): get_db_session(), get_engine(), get_sessionmaker(), AsyncSession, Async SQLAlchemy engine/session foundation. The engine is created lazily so…, FastAPI dependency yielding a request-scoped async session., AsyncEngine

### Community 33 - "Base Tool Interface"
Cohesion: 0.60
Nodes (3): Perform the tool's action. Raise ``ToolError`` on failure., ToolInput, ToolOutput

### Community 34 - "Fact Checking Skill"
Cohesion: 0.40
Nodes (4): build_skill(), CompiledGraph, Fact Checking skill — compiled LangGraph subgraph. Contract: see SKILL.md in…, Return the compiled fact-checking skill subgraph.

### Community 35 - "X Publishing Skill"
Cohesion: 0.40
Nodes (4): build_skill(), CompiledGraph, X/Twitter Publishing skill — compiled LangGraph subgraph. Contract: see…, Return the compiled X/Twitter publishing skill subgraph.

## Knowledge Gaps
- **8 isolated node(s):** `agent-operator`, `CI Pipeline (ruff + pytest)`, `Test Pipeline (pytest multi-python)`, `Docker Compose Infrastructure`, `Skill: Browser Control` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 304 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RiskLevel` connect `Approval Policies` to `Web Fetch Tool & Errors`, `Content API Routes`, `LangSearch Tool`, `Orchestrator & Recovery`, `Browser Toolkit`, `Base Agent Interface`, `Model Selection Helpers`, `Orchestrator Core Logic`, `Tool Executor Tests`, `Tool Registry Tests`?**
  _High betweenness centrality (0.117) - this node is a cross-community bridge._
- **Why does `ModelRouter` connect `Model Routing Config` to `LLM Content Generator`, `Fact Checking Skill`, `X Publishing Skill`, `Agent Graph Builders`, `Browser Toolkit`, `Base Agent Interface`, `Model Selection Helpers`, `Planner & Plan Steps`, `Browser Control Skill`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `ToolExecutionEngine` connect `Browser Toolkit` to `Web Fetch Tool & Errors`, `Fact Checking Skill`, `Database Models`, `Social Publishing API`, `Agent Graph Builders`, `X Publishing Skill`, `Orchestrator & Recovery`, `Model Routing Config`, `Approval Policies`, `Model Selection Helpers`, `API Dependency Injection`, `Tool Executor Tests`, `Browser Control Skill`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `ToolExecutionEngine` (e.g. with `build_graph()` and `build_graph()`) actually correct?**
  _`ToolExecutionEngine` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `RiskLevel` (e.g. with `Orchestrator` and `PlannerAgent`) actually correct?**
  _`RiskLevel` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `ModelRouter` (e.g. with `build_graph()` and `build_graph()`) actually correct?**
  _`ModelRouter` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 27 inferred relationships involving `ToolError` (e.g. with `BaseTool` and `WebFetchTool`) actually correct?**
  _`ToolError` has 27 INFERRED edges - model-reasoned connections that need verification._