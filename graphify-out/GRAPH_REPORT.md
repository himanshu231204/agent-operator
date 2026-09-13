# Graph Report - agent-operator  (2026-09-13)

## Corpus Check
- 166 files · ~71,451 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1773 nodes · 4879 edges · 134 communities (73 shown, 33 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 587 edges (avg confidence: 0.93)
- Token cost: 113,487 input · 0 output

## Community Hubs (Navigation)
- Content Generation & Tone Safety
- Browser Toolkit & Schemas
- Agent Subgraphs
- Agent Base Classes
- Model Router & LLM Config
- File System Tools
- Social Publishing Tools
- Base Tool Framework
- Database Models
- Audit & Tool Call Logs
- Error Handling & Social Base
- Callbacks & Observability
- LinkedIn Adapter
- Social API Routes
- CLI Commands
- Browser Session Manager
- Task State Machine
- Browser Session Tests
- Tool Executor Tests
- Browser Session Actions
- Research Pipeline
- Web Fetch & SSRF Protection
- Research Pipeline Tests
- API Router & Approvals
- LLM Base & Tone Safety
- Orchestrator
- Skills Packager
- Fact Check Tool
- Source Classification
- Callbacks & Logging
- Module Cluster 30
- Module Cluster 31
- Module Cluster 32
- Module Cluster 33
- Module Cluster 34
- Module Cluster 35
- Module Cluster 36
- Module Cluster 37
- Module Cluster 38
- Module Cluster 39
- Module Cluster 40
- Module Cluster 41
- Module Cluster 42
- Module Cluster 43
- Module Cluster 44
- Module Cluster 45
- Module Cluster 46
- Module Cluster 47
- Module Cluster 48
- Module Cluster 49
- Module Cluster 50
- Module Cluster 51
- Module Cluster 52
- Module Cluster 53
- Module Cluster 54
- Module Cluster 55
- Module Cluster 56
- Module Cluster 57
- Module Cluster 58
- Module Cluster 59
- Module Cluster 60
- Module Cluster 61
- Module Cluster 62
- Module Cluster 63
- Module Cluster 64
- Module Cluster 65
- Module Cluster 66
- Module Cluster 67
- Module Cluster 68
- Module Cluster 69
- Module Cluster 70
- Module Cluster 71
- Module Cluster 72
- Module Cluster 73
- Module Cluster 74
- Module Cluster 76
- Module Cluster 77
- Module Cluster 78
- Module Cluster 79
- Module Cluster 80
- Module Cluster 81
- Module Cluster 87
- Module Cluster 99
- Module Cluster 100
- Module Cluster 102
- Module Cluster 103
- Module Cluster 104
- Module Cluster 105
- Module Cluster 106
- Module Cluster 107
- Module Cluster 108
- Module Cluster 109
- Module Cluster 110
- Module Cluster 111
- Module Cluster 112
- Module Cluster 113
- Module Cluster 114
- Module Cluster 116
- Module Cluster 119
- Module Cluster 120
- Module Cluster 121
- Module Cluster 122
- Module Cluster 123
- Module Cluster 124
- Module Cluster 132
- Module Cluster 133

## God Nodes (most connected - your core abstractions)
1. `RiskLevel` - 94 edges
2. `ToolError` - 84 edges
3. `ToolExecutionEngine` - 75 edges
4. `ModelRouter` - 74 edges
5. `build_registry()` - 60 edges
6. `ToolRegistry` - 60 edges
7. `BrowserSessionManager` - 56 edges
8. `BrowserActionResult` - 49 edges
9. `ExecutionContext` - 47 edges
10. `Orchestrator` - 43 edges

## Surprising Connections (you probably didn't know these)
- `generator()` --uses--> `LLMContentGenerator`  [INFERRED]
  tests/integration/test_content_generator_real_llm.py → app/content/generator.py
- `generator()` --uses--> `LLMContentGenerator`  [INFERRED]
  tests/unit/test_llm_content_generator.py → app/content/generator.py
- `test_draft_tool_metadata()` --uses--> `RiskLevel`  [INFERRED]
  tests/unit/test_content_tools.py → app/policies/risk.py
- `test_validate_tool_metadata()` --uses--> `RiskLevel`  [INFERRED]
  tests/unit/test_content_tools.py → app/policies/risk.py
- `engine()` --uses--> `ToolExecutionEngine`  [INFERRED]
  tests/integration/test_content_graph.py → app/tools/executor.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Research Tool Pipeline (search + fetch + engine + registry)** — concept_web_search_tool, concept_web_fetch_tool, concept_tool_registry, skills_web_research_skill_md_web_research_skill [EXTRACTED 1.00]
- **Request → Execution Pipeline** — project_md_fastapi, project_md_orchestrator, claude_md_toolexecutionengine, project_md_basetool [EXTRACTED 1.00]
- **Draft → Approve → Publish → Verify Safety Pipeline** — skills_content_generation_skill_md_content_generation_skill, claude_md_approval_gate, project_md_social_agent, docs_autonomy_roadmap_md_verification_pipeline [EXTRACTED 1.00]
- **Autonomy Tier Progression** — docs_autonomy_roadmap_md_tier1_semi_autonomous, docs_autonomy_roadmap_md_tier2_self_improving, docs_autonomy_roadmap_md_tier3_fully_autonomous, docs_autonomy_roadmap_md_tier4_platform [EXTRACTED 1.00]

## Communities (134 total, 33 thin omitted)

### Community 0 - "Content Generation & Tone Safety"
Cohesion: 0.05
Nodes (76): create_draft(), post, TonePreference, Checks tone adherence and safety using the project model router., Return a list of issues; empty means the content passed., ToneSafetyChecker, TonePreference, Deterministic content validation (PROJECT.md section 17). Length, link well-… (+68 more)

### Community 1 - "Browser Toolkit & Schemas"
Cohesion: 0.09
Nodes (56): BrowserActionResult, Browser action/result schemas (PROJECT.md section 12)., BrowserClickInput, BrowserClickTool, BrowserDownloadInput, BrowserDownloadTool, BrowserExtractInput, BrowserExtractTool (+48 more)

### Community 2 - "Agent Subgraphs"
Cohesion: 0.11
Nodes (36): build_graph(), Browser agent subgraph (PROJECT.md section 8, phase 3). Builds a LangGraph…, Return the compiled browser ReAct subgraph., Content agent subgraph (PROJECT.md section 8, phase 5). Builds a LangGraph…, build_graph(), Fact-checker agent subgraph (PROJECT.md section 8, phase 4). Builds a LangGraph…, Return the compiled fact-checker ReAct subgraph., collect_tools() (+28 more)

### Community 3 - "Agent Base Classes"
Cohesion: 0.10
Nodes (40): Agent, AgentDecision, AgentObservation, AgentResult, ABC, Any, BaseModel, Base agent interfaces (PROJECT.md sections 8-9). Agents are not necessarily… (+32 more)

### Community 4 - "Model Router & LLM Config"
Cohesion: 0.06
Nodes (42): build_graph(), Return the compiled content-generation ReAct subgraph., build_graph(), Return the compiled research ReAct subgraph. Tools not yet registered are…, ModelRoutingSettings, Model names are LiteLLM model strings, e.g. ``"gpt-4o-mini"``,…, ModelRouter, generator() (+34 more)

### Community 5 - "File System Tools"
Cohesion: 0.12
Nodes (43): ToolError, FileDeleteInput, FileDeleteOutput, FileDeleteTool, FileEditInput, FileEditOutput, FileEditTool, FileReadInput (+35 more)

### Community 6 - "Social Publishing Tools"
Cohesion: 0.09
Nodes (23): content_hash(), SocialPost, Publish an approved draft to X/Twitter., XPublishToolInput, XPublishToolOutput, LinkedInPublishTool, UUID, Social publishing tools (Phase 6 — PROJECT.md sections 13, 18-20). HIGH-RISK:… (+15 more)

### Community 7 - "Base Tool Framework"
Cohesion: 0.07
Nodes (34): BaseTool, ABC, Base class for every tool. Subclasses declare ``name``, ``description``, and…, Perform the tool's action. Raise ``ToolError`` on failure., Inject the engine + registry (called by build_tool_engine)., _make_tool_retry(), Any, AsyncSession (+26 more)

### Community 8 - "Database Models"
Cohesion: 0.13
Nodes (36): Base, SQLAlchemy 2.x declarative base and shared column mixins., Declarative base shared by every ORM model., TimestampMixin, UUIDPrimaryKeyMixin, AgentRun, Agent run and tool-call ORM models (execution observability)., Human approval ORM model (PROJECT.md section 21, AGENTS.md section 13). (+28 more)

### Community 9 - "Audit & Tool Call Logs"
Cohesion: 0.07
Nodes (37): audit_secrets(), DbSessionDep, get, Scan recent tool calls for potential secret leakage. Returns findings with…, ToolCall, BaseModel, Audit API schemas (Phase 7 — Safety)., A potential secret leak found in a tool call record. (+29 more)

### Community 10 - "Error Handling & Social Base"
Cohesion: 0.09
Nodes (17): AuthenticationError, RateLimitError, Structured error hierarchy (PROJECT.md section 48). Every application error…, VerificationError, AdapterPublishResult, Return type for adapter publish calls., X/Twitter platform adapter (PROJECT.md section 18). Implements the…, Verify a tweet exists by re-fetching it from the X API. Args: external_id: The… (+9 more)

### Community 11 - "Callbacks & Observability"
Cohesion: 0.06
Nodes (27): _langsmith_enabled(), OperatorCallbackHandler, Any, UUID, Check if LangSmith tracing is configured., Structured-logging callback for LangGraph agent runs. Extends the LangChain…, extract_usage(), Any (+19 more)

### Community 12 - "LinkedIn Adapter"
Cohesion: 0.10
Nodes (14): LinkedInAdapter, Draft, LinkedIn platform adapter (PROJECT.md section 19). Implements the…, Verify a post exists by re-fetching it from the LinkedIn API. Args:…, Generate a stable idempotency key for a draft., Implements :class:`app.social.base.SocialPlatform` for LinkedIn., Create a draft object for LinkedIn. Note: This does not persist to the DB — the…, Publish a post via LinkedIn REST API. Args: draft_content: The text content to… (+6 more)

### Community 13 - "Social API Routes"
Cohesion: 0.12
Nodes (28): _load_approved_draft(), publish_linkedin(), publish_x(), ApprovalServiceDep, DbSessionDep, Draft, post, Social publishing routes (PROJECT.md sections 18-20, 36). Publishing requires… (+20 more)

### Community 14 - "CLI Commands"
Cohesion: 0.08
Nodes (20): ApprovalCLI, main(), UUID, CLI for agent operator (Phase 7 + 8). Provides command-line interface for: -…, Show current task state and result., Show recent agent runs for a task., Main entry point for the CLI., CLI client for the Agent Operator API. (+12 more)

### Community 15 - "Browser Session Manager"
Cohesion: 0.09
Nodes (15): BrowserSessionManager, Browser session abstraction over Playwright (PROJECT.md section 11). Keeps the…, Owns the Playwright lifecycle and open sessions., BrowserChannel, BrowserHeadlessMode, BrowserSettings, StrEnum, Chromium-based browser channels Playwright can launch. - ``chromium`` — bundled… (+7 more)

### Community 16 - "Task State Machine"
Cohesion: 0.16
Nodes (23): can_cancel(), can_transition(), StrEnum, Task state machine (PROJECT.md section 10, AGENTS.md section 6). Framework-…, Return whether ``current -> target`` is an allowed transition., Validate and perform a state transition, raising on invalid moves. Example:…, TaskState, transition() (+15 more)

### Community 17 - "Browser Session Tests"
Cohesion: 0.11
Nodes (31): BrowserSession, _make_session(), mock_page(), fixture, When a page has crashed, _recover_crashed_page creates a new page and re-…, Second crash after recovery should raise BrowserError., test_crash_handler_increments_count(), test_crash_handler_resets_on_load() (+23 more)

### Community 18 - "Tool Executor Tests"
Cohesion: 0.12
Nodes (23): _AlwaysFail, _AuthRequired, _Boom, engine(), _Flaky, _High, _In, _Low (+15 more)

### Community 19 - "Browser Session Actions"
Cohesion: 0.12
Nodes (12): BrowserSession, SelectorStrategy, Select an option from a <select> element., Trigger a download by clicking a link/button and capture the file path., Open a new page/tab in the same context, optionally navigating to a URL., Switch the active page to the tab at *index* in the context., List all open tabs (pages) in this session's context., A single isolated browser context + page (AGENTS.md rule 88). (+4 more)

### Community 20 - "Research Pipeline"
Cohesion: 0.11
Nodes (15): DefaultResearchPipeline, ExtractedClaim, BaseModel, One claim + evidence extracted from a text chunk., Concrete, tool-backed research pipeline. Drives the registered ``web_search`` /…, Fetch a source and extract candidate claims + evidence from it., Produce a final cited answer that never presents disputed claims as fact., Execute the full pipeline and return a structured result. (+7 more)

### Community 21 - "Web Fetch & SSRF Protection"
Cohesion: 0.14
Nodes (24): _extract_text(), _guard_url(), Web fetch tool (PROJECT.md section 8, phase 4). Implements WebFetchTool — an…, Raise ToolError if *url* targets a private/internal address., Strip HTML tags and truncate to _MAX_CONTENT_CHARS., WebFetchOutput, WebFetchTool, _mock_response() (+16 more)

### Community 22 - "Research Pipeline Tests"
Cohesion: 0.13
Nodes (26): _fake_engine(), _fake_registry(), _fake_router(), _fetch_output(), fixture, Unit + integration tests for DefaultResearchPipeline (Phase 4). All network/LLM…, Synthesize must pass disputed claims separately so the prompt can flag them., Stop all started patchers after each test (prevents cross-test leak). (+18 more)

### Community 23 - "API Router & Approvals"
Cohesion: 0.12
Nodes (18): decide_approval(), get_approval(), ApprovalServiceDep, get, post, UUID, Approval routes (PROJECT.md section 36, section 21)., Audit routes (Phase 7 — Safety). Provides endpoints for auditing system state,… (+10 more)

### Community 24 - "LLM Base & Tone Safety"
Cohesion: 0.15
Nodes (19): LLM-backed tone and safety semantic check (PROJECT.md section 12).…, ModelClass, ModelSelection, BaseModel, StrEnum, LangChain-compatible LLM abstraction. The application depends on…, Model classes the router picks between (PROJECT.md section 7)., Signals the model router uses to pick a model class. Mirrors the routing… (+11 more)

### Community 25 - "Orchestrator"
Cohesion: 0.18
Nodes (10): Orchestrator, OrchestratorState, Any, Exception, UUID, Invoke the compiled LangGraph subgraph for *step* in isolation. Each invocation…, Open a browser session if the plan includes browser steps. Returns the…, Close a browser session opened for this task. (+2 more)

### Community 26 - "Skills Packager"
Cohesion: 0.12
Nodes (17): _parse_skill_md(), BaseModel, Skills packager (Phase 8 — Production). Validates all SKILL.md contracts and…, Validate all SKILL.md contracts and return a manifest. Args: skills_dir: Path…, Parsed contract from a SKILL.md file., Manifest of all validated skills., Parse a SKILL.md file into a SkillContract., SkillContract (+9 more)

### Community 27 - "Fact Check Tool"
Cohesion: 0.18
Nodes (17): ResearchError, FactCheckTool, Search + fetch evidence for a single claim and classify it. Strategy…, Turn a claim into a search-friendly query (strip citations, quotes)., Return +1 (support), -1 (contradict), or 0 (neutral/no signal). Deterministic…, Unit tests for the fact_check tool (Phase 4). No real network: the engine is a…, test_fact_check_metadata(), test_fact_check_not_wired_raises() (+9 more)

### Community 28 - "Source Classification"
Cohesion: 0.18
Nodes (22): classify_source(), _extract_host(), freshness_score(), _last_suffix(), Source classification and freshness weighting for research (Phase 4).…, Return a ``[0.0, 1.0]`` freshness score for a publication timestamp. Uses…, Classify a source URL into a :class:`SourceType` bucket. The classification is…, _tld() (+14 more)

### Community 29 - "Callbacks & Logging"
Cohesion: 0.11
Nodes (15): LangChain callback handler for agent run instrumentation (PROJECT.md section…, bind_context(), get_logger(), Structured logging setup (PROJECT.md section 39, AGENTS.md section 19). Every…, Return a structlog bound logger, optionally namespaced., Bind correlation identifiers (request_id, task_id, run_id, ...) to context., UUID, Background task worker (PROJECT.md section 27). Polls PostgreSQL for pending… (+7 more)

### Community 30 - "Module Cluster 30"
Cohesion: 0.15
Nodes (20): ApplicationSettings, DatabaseSettings, LLMProviderSettings, LoggingSettings, Strongly typed application configuration. Settings are grouped by category…, Top-level settings aggregating every configuration category., Credentials/config for LangChain-compatible model providers. No single provider…, SecuritySettings (+12 more)

### Community 31 - "Module Cluster 31"
Cohesion: 0.17
Nodes (17): build_approval_request(), Approval policy (PROJECT.md section 21, AGENTS.md section 13). Pure,…, Build the approval request shown to the user (PROJECT.md section 21). Callers…, requires_approval(), StrEnum, Risk classification (PROJECT.md section 22). ``RiskLevel`` is the single…, LOW: read-only research. MEDIUM: logged-in interactions, drafts. HIGH: external…, RiskLevel (+9 more)

### Community 32 - "Module Cluster 32"
Cohesion: 0.18
Nodes (18): Plan, PlanStep, Any, BaseModel, One step in an execution plan., An ordered plan produced by :class:`PlannerAgent`., LimitSettings, Bounds preventing unbounded agent loops and runaway cost (PROJECT.md 9, 40). (+10 more)

### Community 33 - "Module Cluster 33"
Cohesion: 0.15
Nodes (7): RateLimiter, Rate limiting (token bucket per tool name). Provides in-process rate limiting…, Token bucket rate limiter. Each tool name gets its own bucket. Tokens refill at…, Attempt to acquire a token for *tool_name*. Returns ``True`` if the call is…, Reset the bucket for *tool_name*, or all buckets if ``None``., Unit tests for rate limiter., TestRateLimiter

### Community 34 - "Module Cluster 34"
Cohesion: 0.26
Nodes (17): LangSearchInput, LangSearchOutput, LangSearchTool, BaseModel, _api_data(), _mock_response(), fixture, Unit tests for LangSearchTool. (+9 more)

### Community 35 - "Module Cluster 35"
Cohesion: 0.19
Nodes (17): WebSearchTool, build_registry(), Tool registry factory. Centralises tool instantiation and registration so every…, Instantiate and register all built-in tools. Pass *session_manager* to also…, _social_settings(), _tone_safety_checker(), Unit tests for the tool registry factory., test_build_registry_registers_all_tools() (+9 more)

### Community 36 - "Module Cluster 36"
Cohesion: 0.23
Nodes (10): Approval, ApprovalDecision, ApprovalRequest, BaseModel, Approval API schemas (PROJECT.md section 21)., What is shown to the user before a consequential action executes., ApprovalService, AsyncSession (+2 more)

### Community 37 - "Module Cluster 37"
Cohesion: 0.15
Nodes (15): BaseModel, WebFetchInput, Adversarial web-content fixtures for prompt-injection testing (Phase 4). These…, _do_fetch(), _mock_fetch_response(), parametrize, Prompt-injection defense tests for the research path (Phase 4, AGANS rule 203).…, A search hit whose URL is a file:// or javascript: scheme must be guarded by… (+7 more)

### Community 38 - "Module Cluster 38"
Cohesion: 0.22
Nodes (5): AsyncSession, Verify a published post exists and content matches expectations. This is a…, SocialVerifyTool, asyncio, TestSocialVerifyTool

### Community 39 - "Module Cluster 39"
Cohesion: 0.17
Nodes (16): OperatorCallbackHandler, ToolExecutionEngine, Plugin System, Skill API, ResearchQualityScorer, BaseTool, Content Agent, FactCheck Agent (+8 more)

### Community 40 - "Module Cluster 40"
Cohesion: 0.27
Nodes (13): cancel_task(), create_task(), get_task(), get, post, UUID, Task routes (PROJECT.md section 36). Thin: all logic lives in…, BaseModel (+5 more)

### Community 41 - "Module Cluster 41"
Cohesion: 0.18
Nodes (13): ModelError, LLMProviderFactory, BaseChatModel, Protocol, Creates a LangChain ``BaseChatModel`` for a given model name., create_chat_model(), _fake_provider(), get_provider() (+5 more)

### Community 42 - "Module Cluster 42"
Cohesion: 0.14
Nodes (4): checker(), mock_model(), fixture, Unit tests for ToneSafetyChecker.

### Community 43 - "Module Cluster 43"
Cohesion: 0.20
Nodes (13): _browser_manager(), get_approval_service(), get_browser_manager(), get_task_service(), get_tool_engine(), get_tool_registry(), DbSessionDep, FastAPI dependency providers. Routes depend on these instead of constructing… (+5 more)

### Community 44 - "Module Cluster 44"
Cohesion: 0.23
Nodes (12): has_conflicting_evidence(), is_high_confidence(), Research evidence helpers (PROJECT.md section 15, section 44). Deterministic,…, A claim is only high-confidence if it clears the threshold *and* has no…, Bucket claims for a quick research-quality overview., summarize_confidence(), Claim, BaseModel (+4 more)

### Community 45 - "Module Cluster 45"
Cohesion: 0.33
Nodes (11): BaseModel, Shell execution tool for the local system agent. Runs commands via asyncio…, ShellRunInput, ShellRunOutput, ShellRunTool, test_shell_run_blocks_rm_rf_root(), test_shell_run_blocks_sudo(), test_shell_run_captures_stderr_and_nonzero_exit() (+3 more)

### Community 46 - "Module Cluster 46"
Cohesion: 0.19
Nodes (8): generator(), _make_claim(), mock_model(), fixture, Unit tests for LLMContentGenerator. LLM calls are mocked with AsyncMock., test_generate_draft_disputed_claim_marked(), test_generate_draft_research_claims_in_message(), test_generate_draft_returns_model_response()

### Community 47 - "Module Cluster 47"
Cohesion: 0.31
Nodes (13): FactCheckToolInput, SearchResult, _engine_returning(), _make_tool(), Build a fake engine that returns canned sub-tool outputs in order.…, _registry_with_subtools(), test_fact_check_checks_own_source_url(), test_fact_check_contradicted_claim() (+5 more)

### Community 48 - "Module Cluster 48"
Cohesion: 0.26
Nodes (11): BaseModel, WebSearchInput, WebSearchOutput, fixture, Unit tests for WebSearchTool., test_empty_results(), test_happy_path(), test_max_results_validation() (+3 more)

### Community 49 - "Module Cluster 49"
Cohesion: 0.24
Nodes (12): _claim(), _print(), Real LLM integration test for LLMContentGenerator (Phase 5). Requires…, LLM produces a non-empty draft for X/Twitter., LLM produces a non-empty draft for LinkedIn., LLM handles the no-research case gracefully (returns a draft, not an error)., LLM acknowledges contradicting evidence in its draft., test_real_llm_disputed_claim_surfaced() (+4 more)

### Community 50 - "Module Cluster 50"
Cohesion: 0.26
Nodes (10): get_settings(), Return the process-wide settings singleton. Cached so configuration is parsed…, Connection, _database_url(), _do_run_migrations(), Alembic environment configured for the application's async SQLAlchemy engine.…, run_migrations_offline(), run_migrations_online() (+2 more)

### Community 51 - "Module Cluster 51"
Cohesion: 0.24
Nodes (11): BrowserSettings, browser_session(), local_server(), fixture, Real-browser integration tests using Playwright. These tests start a local HTTP…, Serve *directory* on a random free port; yields the base URL., test_click_button_updates_dom(), test_extract_text_returns_page_content() (+3 more)

### Community 52 - "Module Cluster 52"
Cohesion: 0.18
Nodes (7): ABC, Abstract research pipeline contract (search -> extract -> cross-check ->…, Find candidate sources for a research question., Extract candidate claims + evidence from a single source., Cross-check claims against each other, filling in contradicting evidence., Produce a final cited answer. Never present an unsupported claim as verified., ResearchPipeline

### Community 53 - "Module Cluster 53"
Cohesion: 0.22
Nodes (11): AutoApprovalPolicy, AutonomousSocialManager, Autonomy Scales With Verification, ConfidenceEngine, FeedbackEngine, TaskScheduler, VerificationPipeline, Tier 1 Detailed Implementation Plan (+3 more)

### Community 54 - "Module Cluster 54"
Cohesion: 0.36
Nodes (8): EchoInput, EchoOutput, EchoTool, FailingTool, BaseModel, test_registry_lookup_and_missing_tool(), test_tool_call_returns_output(), test_tool_wraps_unexpected_exceptions_as_tool_error()

### Community 55 - "Module Cluster 55"
Cohesion: 0.20
Nodes (10): No Redis — PostgreSQL SKIP LOCKED, PostgresSaver, Docker Compose Services, OrchestratorCluster, Deployment Guide, LangSmith Tracing, CI Workflow (ruff + pytest), Test Workflow (multi-python pytest) (+2 more)

### Community 56 - "Module Cluster 56"
Cohesion: 0.24
Nodes (8): FactCheckClaimInput, FactCheckResult, FactCheckToolOutput, BaseModel, Fact-check tool (PROJECT.md section 17, AGANS.md rules 98-99). A read-only…, Invoke a registered sub-tool through the engine (permission-gated)., A single claim to verify, with optional provenance URL., The verdict for a single claim plus the evidence that backs it.

### Community 57 - "Module Cluster 57"
Cohesion: 0.25
Nodes (9): close_session(), get_session(), open_session(), get, post, BrowserSessionRead, BaseModel, BrowserManagerDep (+1 more)

### Community 58 - "Module Cluster 58"
Cohesion: 0.42
Nodes (8): get_draft(), DbSessionDep, get, UUID, Content draft routes (PROJECT.md sections 16-17, 36). Publishing is a separate,…, update_draft(), Draft, DraftRead

### Community 59 - "Module Cluster 59"
Cohesion: 0.31
Nodes (6): ContentGenerator, LLMContentGenerator, ABC, Platform, Generate a draft for ``platform``. Must never invent statistics, quotes,…, LLM-backed content generator using the project model router.

### Community 60 - "Module Cluster 60"
Cohesion: 0.33
Nodes (8): classify_source_obj(), Return a copy of *source* with ``source_type`` populated by heuristics., Rank sources: primary/official first, then by freshness. A cheap deterministic…, sort_by_confidence_and_freshness(), Find candidate sources for a research question (bounded, ranked)., Source, test_classify_source_obj_populates_and_returns_copy(), test_sort_ranks_primary_before_community()

### Community 61 - "Module Cluster 61"
Cohesion: 0.36
Nodes (7): get_db_session(), get_engine(), get_sessionmaker(), AsyncSession, Async SQLAlchemy engine/session foundation. The engine is created lazily so…, FastAPI dependency yielding a request-scoped async session., AsyncEngine

### Community 62 - "Module Cluster 62"
Cohesion: 0.33
Nodes (7): Human Approval Gate Rule, Approval Gate, Human Approval Gateway, Reliable over Autonomous Principle, Social Agent, Skill: LinkedIn Publishing, Skill: X/Twitter Publishing

### Community 63 - "Module Cluster 63"
Cohesion: 0.29
Nodes (6): Page, SelectorStrategy, Resilient selector strategy (PROJECT.md section 12, AGENTS.md rules 77-84).…, Build a Playwright ``Locator`` for the given strategy. ``coordinates`` has no…, resolve_locator(), Locator

### Community 64 - "Module Cluster 64"
Cohesion: 0.29
Nodes (4): Page, Increment the crash counter; the next navigation/operation will trigger a…, Clear the crash flag on successful load., BrowserContext

### Community 65 - "Module Cluster 65"
Cohesion: 0.29
Nodes (7): ModelRouter, AdaptiveModelRouter, CostEngine / BudgetManager, BrowserRecovery (Tier 2), Tier 2 Detailed Implementation Plan, LiteLLM, Model Router Classes (FAST/TOOL_CALLING/REASONING/STRONGEST)

### Community 66 - "Module Cluster 66"
Cohesion: 0.29
Nodes (7): MemoryStore, Tier 1: Semi-Autonomous, Tier 2: Self-Improving, Tier 3: Fully Autonomous, Tier 4: Platform / Ecosystem, Tier 3 Detailed Implementation Plan, Tier 4 Detailed Implementation Plan

### Community 67 - "Module Cluster 67"
Cohesion: 0.40
Nodes (5): _make_router(), build_skill(router, session_manager) must return a non-None compiled graph., BROWSER_CRITERIA must have requires_tools=True and MODERATE complexity., test_build_skill_returns_compiled_graph(), test_build_skill_uses_browser_criteria()

### Community 68 - "Module Cluster 68"
Cohesion: 0.80
Nodes (5): AGENTS.md Implementation Rules, Contributing Guide, Full Autonomy Implementation Roadmap, Agent Operator Platform, Agent Operator

### Community 69 - "Module Cluster 69"
Cohesion: 0.60
Nodes (5): SSRF Protection (_guard_url), ToolRegistry + build_registry() factory, WebFetchTool (SSRF-protected httpx fetcher), WebSearchTool (TavilySearchResults wrapper), Phase 4 Research Pipeline Implementation Plan

### Community 70 - "Module Cluster 70"
Cohesion: 0.50
Nodes (5): Browser Agent, Permission Levels (LOW/MEDIUM/HIGH), Playwright + Chromium, Skill: Browser Control, Skill: Local System

### Community 71 - "Module Cluster 71"
Cohesion: 0.40
Nodes (4): build_skill(), CompiledGraph, Fact Checking skill — compiled LangGraph subgraph. Contract: see SKILL.md in…, Return the compiled fact-checking skill subgraph.

### Community 72 - "Module Cluster 72"
Cohesion: 0.50
Nodes (4): Context Quarantine Rule, Permission Levels Policy, Context Quarantine Pattern, Pull Request Template

## Knowledge Gaps
- **35 isolated node(s):** `Production Roadmap (TODO.md)`, `Name Input (aria-label)`, `Test Page HTML Fixture`, `Click Me Button (#btn)`, `agent-operator` (+30 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 550 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RiskLevel` connect `Module Cluster 31` to `Content Generation & Tone Safety`, `Browser Toolkit & Schemas`, `Agent Subgraphs`, `Agent Base Classes`, `File System Tools`, `Social Publishing Tools`, `Base Tool Framework`, `Social API Routes`, `Tool Executor Tests`, `Research Pipeline`, `Web Fetch & SSRF Protection`, `LLM Base & Tone Safety`, `Orchestrator`, `Fact Check Tool`, `Module Cluster 34`, `Module Cluster 35`, `Module Cluster 38`, `Module Cluster 45`, `Module Cluster 48`, `Module Cluster 54`, `Module Cluster 56`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `ToolError` connect `File System Tools` to `Browser Toolkit & Schemas`, `Module Cluster 34`, `Agent Base Classes`, `Module Cluster 35`, `Agent Subgraphs`, `Social Publishing Tools`, `Base Tool Framework`, `Module Cluster 38`, `Module Cluster 37`, `Error Handling & Social Base`, `LinkedIn Adapter`, `Module Cluster 45`, `Social API Routes`, `Module Cluster 48`, `Tool Executor Tests`, `Web Fetch & SSRF Protection`, `Module Cluster 54`, `Module Cluster 31`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `ModelRouter` connect `Model Router & LLM Config` to `Content Generation & Tone Safety`, `Module Cluster 32`, `Agent Subgraphs`, `Agent Base Classes`, `Module Cluster 35`, `Module Cluster 71`, `Module Cluster 42`, `Module Cluster 46`, `Module Cluster 49`, `LLM Base & Tone Safety`, `Module Cluster 58`, `Module Cluster 59`, `Callbacks & Logging`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Are the 61 inferred relationships involving `RiskLevel` (e.g. with `Orchestrator` and `PlannerAgent`) actually correct?**
  _`RiskLevel` has 61 INFERRED edges - model-reasoned connections that need verification._
- **Are the 39 inferred relationships involving `ToolError` (e.g. with `LinkedInAdapter` and `XAdapter`) actually correct?**
  _`ToolError` has 39 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `ToolExecutionEngine` (e.g. with `build_graph()` and `build_graph()`) actually correct?**
  _`ToolExecutionEngine` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `ModelRouter` (e.g. with `build_graph()` and `build_graph()`) actually correct?**
  _`ModelRouter` has 21 INFERRED edges - model-reasoned connections that need verification._