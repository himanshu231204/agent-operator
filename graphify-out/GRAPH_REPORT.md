# Graph Report - phase-5-content-generation  (2026-09-12)

## Corpus Check
- 20 files · ~41,233 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1143 nodes · 3021 edges · 93 communities (48 shown, 19 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 331 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Content API Routes
- Filesystem Tools
- Content Generation Engine
- Social Publishing API
- URL Fetch Tools
- Database Models
- Architecture & Documentation
- Browser Session Management
- Task State Machine
- Agent Orchestration
- CI/CD Workflows
- Agent Graphs & Model Routing
- Browser Toolkit Tools
- Agent Subgraph Registry
- LLM Provider Config
- Browser API Routes
- Agent Decision Framework
- LLM Model Selection
- Tool Base Classes
- Tool Execution & LangChain Adapter
- Tool Executor Internals
- Orchestrator Core
- Planning & Plan Steps
- Tool Executor Tests
- Language Search Tool
- Browser & Fact-Checker Graphs
- Approval Policies
- API Dependencies
- Browser Session Actions
- Task API Routes
- Operator Callback Handler
- Browser Integration Tests
- Tool Registry & Factory
- Agent Callbacks & Planner
- Config & Migrations
- Error Hierarchy
- LLM Usage Tracking
- Browser Session Unit Tests
- Application Settings
- Validation & Approval Service
- Tool Registry Tests
- Approvals API
- Browser Selectors
- Local System Agent
- Database Session
- Browser Control Skill Tests
- Content Generation Skill
- X Publishing Skill
- Browser Click Tool
- Browser Navigate Tool
- Agent Graphs Init
- Builtin Tools Init
- Workers Init
- Browser Test Fixtures
- Browser Page Type
- Selector Strategy Type
- Browser Structured Tool
- Tool Factory Session
- BrowserExtractTool Doc
- BrowserInspectTool Doc
- BrowserNavigateTool Doc
- BrowserScreenshotTool Doc
- BrowserScrollTool Doc
- BrowserTypeTool Doc
- BrowserWaitTool Doc
- Package Metadata
- Browser Control Rationale

## God Nodes (most connected - your core abstractions)
1. `ModelRouter` - 57 edges
2. `RiskLevel` - 57 edges
3. `ToolExecutionEngine` - 56 edges
4. `ToolError` - 50 edges
5. `ToolRegistry` - 43 edges
6. `TaskState` - 37 edges
7. `Orchestrator` - 35 edges
8. `BrowserSessionManager` - 34 edges
9. `BrowserActionResult` - 33 edges
10. `TaskService` - 32 edges

## Surprising Connections (you probably didn't know these)
- `Browser Safety Constraints` --semantically_similar_to--> `Selector Preference Strategy (aria_role first)`  [INFERRED] [semantically similar]
  skills/browser_control/SKILL.md → docs/superpowers/plans/2026-09-12-phase-3-browser-agent.md
- `test_tool_error_translates_and_propagates()` --uses--> `ToolError`  [INFERRED]
  tests/unit/test_tool_executor.py → app/errors.py
- `test_tool_wraps_unexpected_exceptions_as_tool_error()` --uses--> `ToolError`  [INFERRED]
  tests/unit/test_tool_registry.py → app/errors.py
- `test_disallowed_schemes_blocked()` --uses--> `ToolError`  [INFERRED]
  tests/unit/test_web_fetch_tool.py → app/errors.py
- `test_ssrf_private_ip_blocked()` --uses--> `ToolError`  [INFERRED]
  tests/unit/test_web_fetch_tool.py → app/errors.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Agent Subgraph Infrastructure (LangGraph + PostgresSaver + Callbacks)** — concept_langgraph_subgraph, concept_postgres_saver, concept_operator_callback_handler, concept_context_quarantine [EXTRACTED 1.00]
- **Research Tool Pipeline (search + fetch + engine + registry)** — concept_web_search_tool, concept_web_fetch_tool, concept_tool_execution_engine, concept_tool_registry, skills_web_research_skill_md_web_research_skill [EXTRACTED 1.00]
- **Social Publishing Skills (X + LinkedIn)** — skills_x_publishing_skill_md_x_skill, skills_linkedin_publishing_skill_md_linkedin_skill, concept_social_platform_protocol, concept_approval_gate, concept_idempotency [INFERRED 0.95]
- **8 Browser BaseTool Implementations** — docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browsernavigatetool, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browserinspecttool, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browserclicktool, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browsertypetool, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browserextracttool, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browserscrolltool, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browserscreenshottool, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browserwaittool [EXTRACTED 1.00]
- **CI Browser Marker Exclusion Pattern** — _github_workflows_ci_yml_browser_marker_exclusion, _github_workflows_test_yml_pytest_step, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browser_marker [INFERRED 0.95]
- **Browser Session Delegation Flow** — docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browsersessionmanager, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browsersession, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_toolexecutionengine, docs_superpowers_plans_2026_09_12_phase_3_browser_agent_browseractionresult [EXTRACTED 1.00]

## Communities (93 total, 19 thin omitted)

### Community 0 - "Content API Routes"
Cohesion: 0.06
Nodes (70): create_draft(), get_draft(), DbSessionDep, get, post, UUID, Content draft routes (PROJECT.md sections 16-17, 36). Publishing is a separate,…, update_draft() (+62 more)

### Community 1 - "Filesystem Tools"
Cohesion: 0.09
Nodes (54): ToolError, FileDeleteInput, FileDeleteOutput, FileDeleteTool, FileEditInput, FileEditOutput, FileEditTool, FileReadInput (+46 more)

### Community 2 - "Content Generation Engine"
Cohesion: 0.05
Nodes (47): ContentGenerator, LLMContentGenerator, ABC, Platform, Content generation interface and LLM-backed implementation (PROJECT.md section…, Generate a draft for ``platform``. Must never invent statistics, quotes,…, LLM-backed content generator using the project model router., has_conflicting_evidence() (+39 more)

### Community 3 - "Social Publishing API"
Cohesion: 0.10
Nodes (29): _load_approved_draft(), publish_linkedin(), publish_x(), ApprovalServiceDep, DbSessionDep, Draft, post, Social publishing routes (PROJECT.md sections 18-20, 36). Real publishing is… (+21 more)

### Community 4 - "URL Fetch Tools"
Cohesion: 0.09
Nodes (42): _extract_text(), _guard_url(), BaseModel, Web fetch tool (PROJECT.md section 8, phase 4). Implements WebFetchTool — an…, Raise ToolError if *url* targets a private/internal address., Strip HTML tags and truncate to _MAX_CONTENT_CHARS., WebFetchInput, WebFetchOutput (+34 more)

### Community 5 - "Database Models"
Cohesion: 0.16
Nodes (30): Base, SQLAlchemy 2.x declarative base and shared column mixins., Declarative base shared by every ORM model., TimestampMixin, UUIDPrimaryKeyMixin, AgentRun, Agent run and tool-call ORM models (execution observability)., ToolCall (+22 more)

### Community 6 - "Architecture & Documentation"
Cohesion: 0.10
Nodes (32): Agent Operator Platform (AGENTS.md), Claude Code Operating Guide (CLAUDE.md), Human Approval Gateway (NodeInterrupt), Content Generation Pipeline (Research→Draft→Fact Check→Approval→Publish), Context Quarantine Pattern, Idempotency (action_id + content_hash), LangGraph ReAct Subgraph (create_react_agent), Model Classes (FAST/TOOL_CALLING/REASONING/STRONGEST) (+24 more)

### Community 7 - "Browser Session Management"
Cohesion: 0.10
Nodes (14): BrowserSessionManager, Browser session abstraction over Playwright (PROJECT.md section 11). Keeps the…, Owns the Playwright lifecycle and open sessions., BrowserExtractTool, BrowserScreenshotTool, BrowserScrollTool, BrowserTypeTool, BrowserWaitTool (+6 more)

### Community 8 - "Task State Machine"
Cohesion: 0.17
Nodes (23): can_cancel(), can_transition(), StrEnum, Task state machine (PROJECT.md section 10, AGENTS.md section 6). Framework-…, Return whether ``current -> target`` is an allowed transition., Validate and perform a state transition, raising on invalid moves. Example:…, TaskState, transition() (+15 more)

### Community 9 - "Agent Orchestration"
Cohesion: 0.19
Nodes (22): AgentObservation, Base agent interfaces (PROJECT.md sections 8-9). Agents are not necessarily…, What an agent sees before deciding on an action., Agent orchestrator (PROJECT.md sections 8-9, AGENTS.md rules 56-59). Drives the…, Any, StrEnum, Recovery agent (PROJECT.md section 29). Given a failure, decides whether the…, RecoveryAction (+14 more)

### Community 10 - "CI/CD Workflows"
Cohesion: 0.09
Nodes (28): Browser Marker Exclusion (-m not browser), CI Pipeline, pytest Step (CI), Ruff Lint Step, pytest Step (Tests), Tests Pipeline, Browser Integration Tests (Task 5), pytest.mark.browser Marker (+20 more)

### Community 11 - "Agent Graphs & Model Routing"
Cohesion: 0.12
Nodes (23): build_graph(), Return the compiled content-generation ReAct subgraph., build_graph(), Return the compiled research ReAct subgraph. Tools not yet registered are…, ModelRoutingSettings, Model names are LiteLLM model strings, e.g. ``"gpt-4o-mini"``,…, ModelRouter, generator() (+15 more)

### Community 12 - "Browser Toolkit Tools"
Cohesion: 0.21
Nodes (24): BrowserClickInput, BrowserExtractInput, BrowserInspectInput, BrowserInspectTool, BrowserNavigateInput, BrowserScreenshotInput, BrowserScrollInput, BrowserTypeInput (+16 more)

### Community 13 - "Agent Subgraph Registry"
Cohesion: 0.17
Nodes (12): Browser agent subgraph (PROJECT.md section 8, phase 3). Builds a LangGraph…, Content agent subgraph (PROJECT.md section 8, phase 5). Builds a LangGraph…, Fact-checker agent subgraph (PROJECT.md section 8, phase 4). Builds a LangGraph…, Shared utilities for building LangGraph agent subgraphs. Every…, Research agent subgraph (PROJECT.md section 8, phase 4). Builds a LangGraph…, Social agent subgraph (PROJECT.md section 8, phase 6). Builds a LangGraph ReAct…, Verification agent subgraph (PROJECT.md section 8, phase 6). Builds a LangGraph…, Centralized model router (PROJECT.md section 7, AGENTS.md section 4). The… (+4 more)

### Community 14 - "LLM Provider Config"
Cohesion: 0.13
Nodes (22): LLMProviderSettings, Credentials/config for LangChain-compatible model providers. No single provider…, ModelError, LLMProviderFactory, BaseChatModel, Protocol, Creates a LangChain ``BaseChatModel`` for a given model name., build_litellm_provider() (+14 more)

### Community 15 - "Browser API Routes"
Cohesion: 0.12
Nodes (18): close_session(), get_session(), open_session(), get, post, Browser session routes (PROJECT.md sections 11, 36). Foundation only: opening a…, health(), get (+10 more)

### Community 16 - "Agent Decision Framework"
Cohesion: 0.13
Nodes (15): Agent, AgentDecision, AgentResult, ABC, Any, BaseModel, An agent's proposed next action. ``requires_approval`` must be set by the agent…, Base class for every specialized agent. (+7 more)

### Community 17 - "LLM Model Selection"
Cohesion: 0.18
Nodes (17): ModelClass, ModelSelection, BaseModel, StrEnum, LangChain-compatible LLM abstraction. The application depends on…, Model classes the router picks between (PROJECT.md section 7)., Signals the model router uses to pick a model class. Mirrors the routing…, The router's decision, recorded for observability (PROJECT.md section 39). (+9 more)

### Community 18 - "Tool Base Classes"
Cohesion: 0.13
Nodes (15): BaseTool, ABC, BaseModel, Tool architecture foundation (PROJECT.md sections 32-33). Every agent…, Metadata the orchestrator uses to enforce policy centrally., Base class for every tool. Subclasses declare ``name``, ``description``, and…, Perform the tool's action. Raise ``ToolError`` on failure., ToolPermissions (+7 more)

### Community 19 - "Tool Execution & LangChain Adapter"
Cohesion: 0.16
Nodes (18): ExecutionContext, Runtime facts about who is executing what. ``approved_actions`` names actions…, _input_model_for(), BaseModel, StructuredTool, Adapter turning ``app.tools.base.BaseTool`` instances into…, Wrap a :class:`BaseTool` for use with LangChain chat-model tool calling. The…, Locate the pydantic input model declared as ``BaseTool[Input, Output]``. Falls… (+10 more)

### Community 20 - "Tool Executor Internals"
Cohesion: 0.13
Nodes (16): Any, AsyncSession, BaseModel, The outcome of a single tool invocation, plus the persisted row id., Executes registered tools while enforcing permissions + audit., _serialize(), ToolExecutionEngine, ToolExecutionResult (+8 more)

### Community 21 - "Orchestrator Core"
Cohesion: 0.22
Nodes (8): Orchestrator, OrchestratorState, Any, Exception, UUID, Invoke the compiled LangGraph subgraph for *step* in isolation. Each invocation…, In-memory execution state for one ``run()`` invocation., Wires compiled LangGraph subgraphs together under configured limits. ``graphs``…

### Community 22 - "Planning & Plan Steps"
Cohesion: 0.20
Nodes (17): Plan, PlanStep, BaseModel, One step in an execution plan., An ordered plan produced by :class:`PlannerAgent`., ApprovalDecision, Approval API schemas (PROJECT.md section 21)., _build_orchestrator() (+9 more)

### Community 23 - "Tool Executor Tests"
Cohesion: 0.19
Nodes (15): _AuthRequired, _Boom, engine(), _High, _In, _Low, _Out, BaseModel (+7 more)

### Community 24 - "Language Search Tool"
Cohesion: 0.26
Nodes (16): LangSearchInput, LangSearchOutput, LangSearchTool, BaseModel, LangSearch web-search tool. Wraps the LangSearch REST API…, _api_data(), _mock_response(), Unit tests for LangSearchTool. (+8 more)

### Community 25 - "Browser & Fact-Checker Graphs"
Cohesion: 0.14
Nodes (17): build_graph(), Return the compiled browser ReAct subgraph., build_graph(), Return the compiled fact-checker ReAct subgraph., collect_tools(), StructuredTool, Return StructuredTool wrappers for every registered tool in *names*. Tools not…, Route and instantiate a LangChain BaseChatModel. (+9 more)

### Community 26 - "Approval Policies"
Cohesion: 0.23
Nodes (13): build_approval_request(), Approval policy (PROJECT.md section 21, AGENTS.md section 13). Pure,…, Build the approval request shown to the user (PROJECT.md section 21). Callers…, requires_approval(), StrEnum, Risk classification (PROJECT.md section 22). ``RiskLevel`` is the single…, LOW: read-only research. MEDIUM: logged-in interactions, drafts. HIGH: external…, RiskLevel (+5 more)

### Community 27 - "API Dependencies"
Cohesion: 0.17
Nodes (15): _browser_manager(), get_approval_service(), get_browser_manager(), get_task_service(), get_tool_engine(), get_tool_registry(), DbSessionDep, FastAPI dependency providers. Routes depend on these instead of constructing… (+7 more)

### Community 28 - "Browser Session Actions"
Cohesion: 0.21
Nodes (6): BrowserSession, A single isolated browser context + page (AGENTS.md rule 88)., BrowserActionResult, BrowserContext, Page, SelectorStrategy

### Community 29 - "Task API Routes"
Cohesion: 0.30
Nodes (12): cancel_task(), create_task(), get_task(), get, post, UUID, Task routes (PROJECT.md section 36). Thin: all logic lives in…, BaseModel (+4 more)

### Community 30 - "Operator Callback Handler"
Cohesion: 0.23
Nodes (6): OperatorCallbackHandler, Any, UUID, Structured-logging callback for LangGraph agent runs. Phase 8 implementation:…, BaseCallbackHandler, BaseException

### Community 31 - "Browser Integration Tests"
Cohesion: 0.22
Nodes (11): BrowserSettings, browser_session(), local_server(), fixture, Real-browser integration tests using Playwright. These tests start a local HTTP…, Serve *directory* on a random free port; yields the base URL., test_click_button_updates_dom(), test_extract_text_returns_page_content() (+3 more)

### Community 32 - "Tool Registry & Factory"
Cohesion: 0.27
Nodes (12): build_registry(), Instantiate and register all built-in tools. Pass *session_manager* to also…, Unit tests for the tool registry factory., test_build_registry_registers_all_tools(), test_build_registry_with_browser_tools(), test_build_registry_without_browser_tools_has_no_browser_tools(), test_content_draft_in_registry(), test_content_validate_in_registry() (+4 more)

### Community 33 - "Agent Callbacks & Planner"
Cohesion: 0.20
Nodes (8): LangChain callback handler for agent run instrumentation (PROJECT.md section…, Planner agent (PROJECT.md section 8). Turns a validated task instruction into…, bind_context(), get_logger(), Structured logging setup (PROJECT.md section 39, AGENTS.md section 19). Every…, Return a structlog bound logger, optionally namespaced., Bind correlation identifiers (request_id, task_id, run_id, ...) to context., BoundLogger

### Community 34 - "Config & Migrations"
Cohesion: 0.26
Nodes (10): get_settings(), Return the process-wide settings singleton. Cached so configuration is parsed…, Connection, _database_url(), _do_run_migrations(), Alembic environment configured for the application's async SQLAlchemy engine.…, run_migrations_offline(), run_migrations_online() (+2 more)

### Community 35 - "Error Hierarchy"
Cohesion: 0.24
Nodes (9): AgentOperatorError, AuthorizationError, BrowserError, Any, Exception, Structured error hierarchy (PROJECT.md section 48). Every application error…, Base class for all application-raised errors., ResearchError (+1 more)

### Community 36 - "LLM Usage Tracking"
Cohesion: 0.24
Nodes (9): extract_usage(), Any, LLM usage extraction (PROJECT.md section 40). LiteLLM (and LangChain over it)…, Return a normalized :class:`TokenUsage` for a LangChain/LiteLLM reply. Silently…, TokenUsage, Token usage extraction (PROJECT.md section 40)., test_extract_usage_from_ai_message_usage_metadata(), test_extract_usage_from_response_metadata_token_usage() (+1 more)

### Community 37 - "Browser Session Unit Tests"
Cohesion: 0.29
Nodes (11): _make_session(), mock_page(), fixture, test_extract_text_raises_browser_error(), test_extract_text_returns_truncated_body(), test_scroll_down_calls_evaluate(), test_scroll_raises_browser_error(), test_scroll_right_calls_evaluate() (+3 more)

### Community 38 - "Application Settings"
Cohesion: 0.29
Nodes (10): ApplicationSettings, BrowserSettings, DatabaseSettings, LoggingSettings, Strongly typed application configuration. Settings are grouped by category…, Top-level settings aggregating every configuration category., SecuritySettings, Settings (+2 more)

### Community 39 - "Validation & Approval Service"
Cohesion: 0.33
Nodes (5): ValidationError, ApprovalService, AsyncSession, UUID, Approval service (PROJECT.md section 21). Approving a request resumes the task…

### Community 40 - "Tool Registry Tests"
Cohesion: 0.36
Nodes (8): EchoInput, EchoOutput, EchoTool, FailingTool, BaseModel, test_registry_lookup_and_missing_tool(), test_tool_call_returns_output(), test_tool_wraps_unexpected_exceptions_as_tool_error()

### Community 41 - "Approvals API"
Cohesion: 0.31
Nodes (9): decide_approval(), get_approval(), ApprovalServiceDep, get, post, UUID, Approval routes (PROJECT.md section 36, section 21)., ApprovalRead (+1 more)

### Community 42 - "Browser Selectors"
Cohesion: 0.22
Nodes (7): Page, SelectorStrategy, Resilient selector strategy (PROJECT.md section 12, AGENTS.md rules 77-84).…, Build a Playwright ``Locator`` for the given strategy. ``coordinates`` has no…, resolve_locator(), Browser action/result schemas (PROJECT.md section 12)., Locator

### Community 43 - "Local System Agent"
Cohesion: 0.32
Nodes (6): build_graph(), Local system agent subgraph (PROJECT.md section 8). Builds a LangGraph ReAct…, Return the compiled local-system ReAct subgraph., build_skill(), Local-system skill. Reusable compiled LangGraph subgraph for terminal +…, Return the compiled local-system ReAct subgraph as a reusable skill.

### Community 44 - "Database Session"
Cohesion: 0.36
Nodes (7): get_db_session(), get_engine(), get_sessionmaker(), AsyncSession, Async SQLAlchemy engine/session foundation. The engine is created lazily so…, FastAPI dependency yielding a request-scoped async session., AsyncEngine

### Community 45 - "Browser Control Skill Tests"
Cohesion: 0.40
Nodes (5): _make_router(), build_skill(router, session_manager) must return a non-None compiled graph., BROWSER_CRITERIA must have requires_tools=True and MODERATE complexity., test_build_skill_returns_compiled_graph(), test_build_skill_uses_browser_criteria()

### Community 46 - "Content Generation Skill"
Cohesion: 0.40
Nodes (4): build_skill(), CompiledGraph, Content Generation skill — compiled LangGraph subgraph. Contract: see SKILL.md…, Return the compiled content-generation skill subgraph.

### Community 47 - "X Publishing Skill"
Cohesion: 0.40
Nodes (4): build_skill(), CompiledGraph, X/Twitter Publishing skill — compiled LangGraph subgraph. Contract: see…, Return the compiled X/Twitter publishing skill subgraph.

## Knowledge Gaps
- **20 isolated node(s):** `Model Classes (FAST/TOOL_CALLING/REASONING/STRONGEST)`, `OperatorCallbackHandler (Observability)`, `Task State Machine (TaskState StrEnum)`, `Docker Compose Infrastructure`, `agent-operator` (+15 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 332 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RiskLevel` connect `Approval Policies` to `Content API Routes`, `Agent Callbacks & Planner`, `Filesystem Tools`, `URL Fetch Tools`, `Tool Registry Tests`, `Agent Orchestration`, `Agent Subgraph Registry`, `Agent Decision Framework`, `LLM Model Selection`, `Tool Base Classes`, `Tool Execution & LangChain Adapter`, `Tool Executor Internals`, `Orchestrator Core`, `Tool Executor Tests`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `ToolExecutionEngine` connect `Tool Executor Internals` to `Filesystem Tools`, `Social Publishing API`, `Database Models`, `Agent Orchestration`, `Agent Graphs & Model Routing`, `Local System Agent`, `Agent Subgraph Registry`, `Content Generation Skill`, `X Publishing Skill`, `Tool Execution & LangChain Adapter`, `Tool Executor Tests`, `Browser & Fact-Checker Graphs`, `Approval Policies`, `API Dependencies`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `ModelRouter` connect `Agent Graphs & Model Routing` to `Agent Callbacks & Planner`, `Content Generation Engine`, `Local System Agent`, `Agent Subgraph Registry`, `Content Generation Skill`, `X Publishing Skill`, `Agent Decision Framework`, `LLM Model Selection`, `Tool Executor Internals`, `Planning & Plan Steps`, `Browser & Fact-Checker Graphs`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `ModelRouter` (e.g. with `build_graph()` and `build_graph()`) actually correct?**
  _`ModelRouter` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 34 inferred relationships involving `RiskLevel` (e.g. with `Orchestrator` and `PlannerAgent`) actually correct?**
  _`RiskLevel` has 34 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `ToolExecutionEngine` (e.g. with `build_graph()` and `build_graph()`) actually correct?**
  _`ToolExecutionEngine` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `ToolError` (e.g. with `BaseTool` and `WebFetchTool`) actually correct?**
  _`ToolError` has 24 INFERRED edges - model-reasoned connections that need verification._