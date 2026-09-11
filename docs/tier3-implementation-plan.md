# Tier 3 — Fully Autonomous: Detailed Implementation Plan

**Date:** 2026-09-12
**Status:** Ready for Implementation
**Depends on:** Tier 1 + Tier 2 complete (see Prerequisite Map below)
**Branch:** `feature/tier3-fully-autonomous`

---

## Table of Contents

1. [Prerequisite Dependency Map](#1-prerequisite-dependency-map)
2. [Implementation Order](#2-implementation-order)
3. [Feature 5.1 — Autonomous Social Media Manager](#3-feature-51--autonomous-social-media-manager)
4. [Feature 5.2 — Multi-Platform Content Repurposing](#4-feature-52--multi-platform-content-repurposing)
5. [Feature 5.3 — Competitive Intelligence Agent](#5-feature-53--competitive-intelligence-agent)
6. [Feature 5.4 — Agent-to-Agent Delegation](#6-feature-54--agent-to-agent-delegation)
7. [Feature 5.5 — Memory & Context Persistence](#7-feature-55--memory--context-persistence)
8. [Feature 5.6 — Cost-Aware Autonomous Operation](#8-feature-56--cost-aware-autonomous-operation)
9. [Migration Strategy](#9-migration-strategy)
10. [Risk Matrix](#10-risk-matrix)
11. [Acceptance Criteria Summary](#11-acceptance-criteria-summary)

---

## 1. Prerequisite Dependency Map

Each Tier 3 feature depends on specific Tier 1–2 work being complete.

| Tier 3 Feature | Tier 1 Prerequisites | Tier 2 Prerequisites | Rationale |
|---|---|---|---|
| **5.1 Autonomous Social Manager** | 3.2 Self-Verification, 3.3 Scheduler | 4.1 Feedback Loop | Needs scheduler for weekly cycles, verification for publish confirmation, feedback for performance tracking |
| **5.2 Content Repurposing** | 3.1 Confidence Engine | None | Needs confidence engine to auto-approve repurposed content; needs content generation from Phase 5 |
| **5.3 Competitive Intelligence** | 3.3 Scheduler | 4.2 Self-Healing Browser | Needs scheduler for periodic monitoring, browser for website snapshots |
| **5.4 Agent-to-Agent Delegation** | None | None | Core orchestrator extension; needs all subgraphs to exist |
| **5.5 Memory & Context** | None | 4.1 Feedback Loop | Needs feedback data to know what to remember; needs vector store infrastructure |
| **5.6 Cost-Aware Operation** | None | 4.4 Dynamic Routing | Needs performance tracker data for cost calculations; needs budget enforcement |

### Dependency Graph

```
Tier 1 (Scheduler, Verification) ──┬──→ 5.1 Autonomous Social Manager
Tier 2 (Feedback Loop) ────────────┘
                                     │
Tier 1 (Confidence Engine) ─────────→ 5.2 Content Repurposing
                                     │
Tier 1 (Scheduler) ──────────────────┤
Tier 2 (Self-Healing Browser) ───────┘──→ 5.3 Competitive Intelligence
                                     │
Core Orchestrator ───────────────────→ 5.4 Agent-to-Agent Delegation
                                     │
Tier 2 (Feedback Loop) ─────────────→ 5.5 Memory & Context
                                     │
Tier 2 (Dynamic Routing) ───────────→ 5.6 Cost-Aware Operation
```

**Parallelizable:** Features 5.2, 5.3, 5.4, 5.5, 5.6 can be built in parallel after 5.1 is complete (or after their specific prerequisites).

---

## 2. Implementation Order

Build sequentially in this order. Each feature is a merge-ready PR.

| Step | Feature | Effort | Depends On |
|---|---|---|---|
| 1 | Autonomous Social Media Manager | 4–6 weeks | Tier 1+2 |
| 2 | Content Repurposing | 3–4 weeks | Tier 1 |
| 3 | Competitive Intelligence Agent | 3–4 weeks | Tier 1, Tier 2 |
| 4 | Agent-to-Agent Delegation | 2–3 weeks | Core orchestrator |
| 5 | Memory & Context Persistence | 3–4 weeks | Tier 2 |
| 6 | Cost-Aware Autonomous Operation | 2–3 weeks | Tier 2 |

**Rationale for ordering:**

- Autonomous Social Manager is the capstone — it orchestrates all previous work (scheduler, verification, feedback, research, content, social)
- Content Repurposing is independent, builds on confidence engine
- Competitive Intelligence is independent, builds on scheduler + browser
- Agent-to-Agent Delegation is a core orchestrator extension, do it before memory
- Memory & Context builds on feedback data, do it after feedback loop is proven
- Cost-Aware Operation builds on dynamic routing, do it last

---

## 3. Feature 5.1 — Autonomous Social Media Manager

### 3.1.1 Problem

Each social post requires manual triggering. The system can't operate a content calendar autonomously.

### 3.1.2 Files to Create

```
app/autonomy/__init__.py             — Package init
app/autonomy/social_manager.py       — AutonomousSocialManager: full loop
app/autonomy/content_calendar.py     — ContentCalendar: schedule + topics
app/autonomy/topic_monitor.py        — TopicMonitor: trending topic detection
app/autonomy/performance_reporter.py — PerformanceReporter: weekly summaries
app/db/models/calendar.py            — CalendarEntry, ContentSlot ORM models
app/schemas/calendar.py              — CalendarEntry, ContentSlot, ContentPlan schemas
app/api/routes/calendar.py           — Calendar CRUD API
tests/unit/test_social_manager.py
tests/unit/test_content_calendar.py
tests/unit/test_topic_monitor.py
tests/integration/test_autonomous_social_flow.py
```

### 3.1.3 Files to Modify

| File | Change |
|---|---|
| `app/config.py` | Add `AutonomySettings` dataclass |
| `app/api/router.py` | Include calendar router |
| `app/scheduler/scheduler.py` | Register `WeeklyCycleTrigger` for autonomous social manager |

### 3.1.4 Weekly Cycle Flow

```
WeeklyCycleTrigger fires
    │
    ├─→ TopicMonitor.discover()
    │     Search trending topics matching focus areas
    │     Filter by relevance ≥ 0.7
    │
    ├─→ ContentCalendar.plan_week()
    │     Assign topics to content slots
    │     Balance across platforms (X, LinkedIn, newsletter)
    │     Respect platform budgets
    │
    ├─→ For each ContentSlot:
    │     ├─→ Research Agent (web search + source ranking)
    │     ├─→ Content Agent (draft generation)
    │     ├─→ Fact Check Agent (claim verification)
    │     ├─→ Social Agent (publish via platform adapter)
    │     ├─→ VerificationPipeline (confirm publish)
    │     └─→ FeedbackCollector (record performance)
    │
    └─→ PerformanceReporter.generate_weekly_report()
          Aggregate metrics, generate summary
          Deliver via email/Slack/webhook
```

### 3.1.5 Database Schema

```sql
CREATE TABLE content_calendars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    focus_areas JSONB NOT NULL,              -- list of topic keywords
    platform_budget JSONB NOT NULL,          -- {x: 5, linkedin: 3, newsletter: 1}
    week_start_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE content_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID REFERENCES content_calendars(id) NOT NULL,
    topic VARCHAR(500) NOT NULL,
    platform VARCHAR(32) NOT NULL,           -- x, linkedin, newsletter
    scheduled_date DATE,
    status VARCHAR(32) DEFAULT 'planned',    -- planned, in_progress, published, failed
    task_id UUID REFERENCES tasks(id),
    post_id VARCHAR(128),                    -- platform post ID after publish
    engagement_metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_content_slots_calendar ON content_slots(calendar_id);
CREATE INDEX ix_content_slots_status ON content_slots(status);
```

### 3.1.6 Configuration

```python
class AutonomySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTONOMY_")

    enabled: bool = False
    weekly_cycle_day: str = "monday"         # day to run weekly cycle
    weekly_cycle_hour: int = 9               # hour to run (UTC)
    max_posts_per_week: int = 10
    min_relevance_score: float = 0.7
    focus_areas: list[str] = Field(default_factory=list)
    report_delivery: str = "webhook"         # email, slack, webhook
    report_webhook_url: str | None = None
```

### 3.1.7 Acceptance Criteria

- [ ] `TopicMonitor.discover()` finds trending topics matching focus areas
- [ ] `ContentCalendar.plan_week()` creates balanced content plan across platforms
- [ ] Full pipeline (research → draft → fact-check → publish → verify) runs autonomously
- [ ] `PerformanceReporter` generates weekly summary with engagement metrics
- [ ] Weekly cycle triggered by scheduler (cron or manual)
- [ ] `AUTONOMY_ENABLED=false` disables autonomous operation
- [ ] Failed content slots don't block other slots (error isolation)
- [ ] All actions logged with task_id, slot_id, platform for audit trail

---

## 4. Feature 5.2 — Multi-Platform Content Repurposing

### 4.2.1 Problem

Content is created per-platform. One research piece requires separate drafting for X, LinkedIn, newsletter, etc.

### 4.2.2 Files to Create

```
app/content/repurposer.py            — ContentRepurposer: adapt content per platform
app/content/platform_formats.py      — PlatformFormat ABC, XFormat, LinkedInFormat, NewsletterFormat
app/schemas/repurposing.py           — RepurposingRequest, PlatformContent schemas
tests/unit/test_repurposer.py
tests/unit/test_platform_formats.py
tests/integration/test_repurposing_flow.py
```

### 4.2.3 Files to Modify

| File | Change |
|---|---|
| `app/content/generator.py` | Add `repurpose()` method that delegates to `ContentRepurposer` |
| `app/config.py` | Add `RepurposingSettings` |

### 4.2.4 Platform Format Rules

| Platform | Max Chars | Threads | Media | Hashtags | Tone |
|---|---|---|---|---|---|
| X/Twitter | 280 | Yes | Yes | 2-3 | Casual/Professional |
| LinkedIn | 3000 | No | Yes | 3-5 | Professional |
| Newsletter | 50000 | Sections | No | None | Professional |

### 4.2.5 Acceptance Criteria

- [ ] `ContentRepurposer.repurpose()` creates platform-native versions
- [ ] X format enforces 280 char limit, creates threads when longer
- [ ] LinkedIn format enforces 3000 char limit, starts with hook
- [ ] Newsletter format creates structured sections with subject line
- [ ] Each platform version validated against constraints
- [ ] `within_limits` flag indicates if content fits platform constraints
- [ ] Unit tests pass for: repurposing logic, format validation, constraint enforcement

---

## 5. Feature 5.3 — Competitive Intelligence Agent

### 5.3.1 Problem

No continuous monitoring of competitors or industry changes.

### 5.3.2 Files to Create

```
app/autonomy/competitor_monitor.py    — CompetitorMonitor: track competitor activity
app/autonomy/intel_reporter.py        — IntelReporter: generate intelligence reports
app/autonomy/change_detector.py       — ChangeDetector: detect significant changes
app/db/models/intel.py                — CompetitorProfile, IntelSnapshot, IntelReport ORM models
app/schemas/intel.py                  — CompetitorProfile, IntelSnapshot, IntelReport schemas
app/api/routes/intel.py               — Competitor CRUD API
tests/unit/test_competitor_monitor.py
tests/unit/test_change_detector.py
tests/integration/test_intel_flow.py
```

### 5.3.3 Files to Modify

| File | Change |
|---|---|
| `app/config.py` | Add `IntelSettings` |
| `app/api/router.py` | Include intel router |
| `app/scheduler/scheduler.py` | Register `CompetitorMonitorTrigger` for periodic checks |

### 5.3.4 Database Schema

```sql
CREATE TABLE competitor_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    website_url VARCHAR(2048),
    social_urls JSONB,                      -- [{platform: "x", url: "..."}]
    focus_areas JSONB,                      -- topics to monitor
    check_interval_hours INTEGER DEFAULT 24,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE intel_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES competitor_profiles(id) NOT NULL,
    source_type VARCHAR(32) NOT NULL,       -- website, social, news
    source_url VARCHAR(2048),
    content_hash VARCHAR(64),               -- SHA-256 for change detection
    content_summary TEXT,
    is_significant BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE intel_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    competitor_id UUID REFERENCES competitor_profiles(id),
    report_type VARCHAR(32) NOT NULL,       -- change_alert, weekly_summary
    title VARCHAR(500),
    summary TEXT,
    details JSONB,
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_intel_snapshots_competitor ON intel_snapshots(competitor_id);
CREATE INDEX ix_intel_snapshots_hash ON intel_snapshots(content_hash);
```

### 5.3.5 Change Detection

```python
class ChangeDetector:
    """Detect significant changes between snapshots."""

    def has_significant_change(
        self,
        previous: IntelSnapshot | None,
        current: IntelSnapshot,
    ) -> bool:
        if previous is None:
            return True  # First snapshot is always significant

        # Hash-based change detection
        if previous.content_hash == current.content_hash:
            return False  # No change

        # Content similarity threshold
        similarity = self._calculate_similarity(
            previous.content_summary,
            current.content_summary,
        )

        # Significant if less than 80% similar
        return similarity < 0.8
```

### 5.3.6 Acceptance Criteria

- [ ] `CompetitorMonitor.monitor_competitor()` checks website, social, news
- [ ] `ChangeDetector.has_significant_change()` detects meaningful changes
- [ ] `IntelReporter` generates alerts for significant changes
- [ ] Competitor profiles CRUD API functional
- [ ] Monitoring runs on configurable schedule
- [ ] `INTEL_ENABLED=false` disables competitive intelligence
- [ ] Snapshots stored with content hash for efficient change detection

---

## 6. Feature 5.4 — Agent-to-Agent Delegation

### 6.4.1 Problem

The orchestrator micromanages every step. Sub-agents can't autonomously decide to delegate to other agents.

### 6.4.2 Files to Create

```
app/agents/delegation.py              — DelegationManager: handle agent-to-agent handoffs
app/agents/delegation_handler.py      — DelegateToAgentTool: tool for agents to request delegation
tests/unit/test_delegation.py
tests/integration/test_delegation_flow.py
```

### 6.4.3 Files to Modify

| File | Change |
|---|---|
| `app/agents/orchestrator.py` | Handle delegation results in `_invoke_subgraph()` |
| `app/agents/graphs/_helpers.py` | Add `delegate_to_agent` tool to all subgraphs |
| `app/tools/registry.py` | Register `DelegateToAgentTool` |

### 6.4.4 Delegation Flow

```
Sub-agent runs graph
    │
    ├─→ Calls delegate_to_agent tool
    │     target_agent: "research"
    │     instruction: "Research X topic"
    │     context: "I'm creating content about X"
    │
    ├─→ Tool returns DelegateResult (not executed directly)
    │
    └─→ Orchestrator intercepts delegation signal
          ├─→ Creates PlanStep for target agent
          ├─→ Invokes target agent subgraph
          └─→ Returns result to original agent
```

### 6.4.5 Key Design Decisions

1. **Delegation is a tool call, not a direct invocation** — agents use the same tool interface
2. **Orchestrator intercepts delegation signals** — sub-agents don't invoke other subgraphs directly
3. **Delegation depth is limited** — prevents infinite delegation loops (max 3 levels)
4. **Delegation is logged** — every delegation recorded with source, target, instruction

### 6.4.6 Acceptance Criteria

- [ ] `DelegateToAgentTool` available to all subgraphs
- [ ] Orchestrator intercepts delegation signals and invokes target agent
- [ ] Delegation depth limited to 3 levels
- [ ] All delegations logged with source, target, instruction
- [ ] Delegation results returned to original agent
- [ ] Unit tests pass for: delegation tool, orchestrator interception, depth limiting

---

## 7. Feature 5.5 — Memory & Context Persistence

### 7.5.1 Problem

The system doesn't remember previous tasks. Each task starts from scratch.

### 7.5.2 Files to Create

```
app/memory/__init__.py                — Package init
app/memory/store.py                   — MemoryStore: vector store abstraction
app/memory/retriever.py               — MemoryRetriever: recall relevant memories
app/memory/writer.py                  — MemoryWriter: store new memories
app/memory/embeddings.py              — EmbeddingProvider: text embeddings
app/db/models/memory.py               — Memory ORM model (metadata only)
app/schemas/memory.py                 — Memory, MemoryQuery schemas
tests/unit/test_memory_store.py
tests/unit/test_memory_retriever.py
tests/integration/test_memory_flow.py
```

### 7.5.3 Files to Modify

| File | Change |
|---|---|
| `app/agents/graphs/research.py` | Inject `MemoryStore` to recall past research before new research |
| `app/agents/graphs/content.py` | Inject `MemoryStore` to recall past content patterns |
| `app/config.py` | Add `MemorySettings` |

### 7.5.4 Database Schema

```sql
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding_id VARCHAR(128),              -- reference to vector store entry
    metadata JSONB,                         -- task_id, agent, content_type, etc.
    memory_type VARCHAR(32) NOT NULL,       -- research, content, feedback, decision
    importance FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ                  -- optional TTL for stale memories
);

CREATE INDEX ix_memories_type ON memories(memory_type);
CREATE INDEX ix_memories_importance ON memories(importance DESC);
```

### 7.5.5 Memory Usage in Research

```python
# In research agent, before starting new research:
async def _run_research_with_memory(self, query: str):
    # 1. Recall relevant past research
    past_memories = await self.memory.recall(
        f"Previous research on: {query}",
        limit=3,
    )

    # 2. Build context from memories
    context = ""
    if past_memories:
        context = "\n\nPrevious related findings:\n" + "\n".join(
            f"- {m.content}" for m in past_memories
        )

    # 3. Include memory context in research instruction
    instruction = f"Research: {query}{context}\n\nBuild on previous findings where relevant."

    # 4. After research, store new findings
    await self.memory.remember(
        content=new_finding,
        metadata={"task_id": task_id, "agent": "research", "query": query},
    )
```

### 7.5.6 Acceptance Criteria

- [ ] `MemoryStore.recall()` returns relevant memories by semantic similarity
- [ ] `MemoryStore.remember()` stores new memories with metadata
- [ ] Research agent recalls past research before starting new research
- [ ] Content agent recalls past content patterns
- [ ] Memories have optional TTL for automatic expiration
- [ ] `MEMORY_ENABLED=false` disables memory (fallback to no recall)
- [ ] Memory is per-tenant, not global (isolation)
- [ ] Unit tests pass for: store, retriever, writer, embedding provider

---

## 8. Feature 5.6 — Cost-Aware Autonomous Operation

### 8.6.1 Problem

No budget constraints. The system uses whatever model is cheapest per task, but doesn't optimize for overall cost.

### 8.6.2 Files to Create

```
app/cost/__init__.py                  — Package init
app/cost/budget.py                    — BudgetManager: track and enforce budgets
app/cost/optimizer.py                 — CostOptimizer: optimize model selection
app/db/models/cost.py                 — CostRecord, BudgetConfig ORM models
app/schemas/cost.py                   — BudgetStatus, BudgetDecision schemas
app/api/routes/budget.py              — Budget CRUD API
tests/unit/test_budget_manager.py
tests/unit/test_cost_optimizer.py
tests/integration/test_cost_aware_flow.py
```

### 8.6.3 Files to Modify

| File | Change |
|---|---|
| `app/llm/router.py` | Inject `BudgetManager` into `AdaptiveModelRouter` |
| `app/config.py` | Add `BudgetSettings` |
| `app/api/router.py` | Include budget router |

### 8.6.4 Database Schema

```sql
CREATE TABLE cost_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    model_class VARCHAR(32) NOT NULL,
    model_name VARCHAR(128),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd FLOAT DEFAULT 0.0,
    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE budget_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope VARCHAR(32) NOT NULL,            -- daily, monthly, task
    limit_usd FLOAT NOT NULL,
    alert_threshold_pct FLOAT DEFAULT 0.8,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_cost_records_task ON cost_records(task_id);
CREATE INDEX ix_cost_records_at ON cost_records(recorded_at);
```

### 8.6.5 Budget Enforcement Logic

```python
class CostOptimizer:
    """Optimize model selection based on budget constraints."""

    def route_with_budget(self, criteria: RoutingCriteria) -> ModelSelection:
        base = self.base_router.route(criteria)
        budget_status = await self.budget.get_remaining_budget("daily")

        if budget_status.pct_used > 0.8:
            # Budget nearly exhausted — downgrade to cheapest viable model
            return ModelSelection(
                model_class=ModelClass.FAST,
                provider=base.provider,
                model_name=self.base_router._model_name_for(ModelClass.FAST),
                reasoning=f"Budget constraint: {budget_status.pct_used:.0%} used, downgrading to FAST",
            )

        if budget_status.pct_used > 0.5:
            # Half budget used — prefer TOOL_CALLING over REASONING
            if base.model_class == ModelClass.REASONING:
                return ModelSelection(
                    model_class=ModelClass.TOOL_CALLING,
                    provider=base.provider,
                    model_name=self.base_router._model_name_for(ModelClass.TOOL_CALLING),
                    reasoning="Budget optimization: downgrading from REASONING to TOOL_CALLING",
                )

        return base
```

### 8.6.6 Configuration

```python
class BudgetSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BUDGET_")

    enabled: bool = False
    daily_limit_usd: float = 10.0
    monthly_limit_usd: float = 200.0
    alert_threshold_pct: float = 0.8
    hard_limit: bool = False                # True = refuse tasks over budget; False = downgrade
```

### 8.6.7 Acceptance Criteria

- [ ] `BudgetManager.get_remaining_budget()` returns daily/monthly spending
- [ ] `BudgetManager.enforce_budget()` decides if action is within budget
- [ ] `CostOptimizer.route_with_budget()` downgrades models when budget tight
- [ ] Budget alerts triggered at threshold (80% by default)
- [ ] Cost records persisted per task with model, tokens, cost
- [ ] `BUDGET_ENABLED=false` disables budget enforcement
- [ ] Budget CRUD API functional
- [ ] Unit tests pass for: budget tracking, enforcement, model downgrade logic

---

## 9. Migration Strategy

Run Alembic migrations in order:

| Order | Migration | Tables Affected |
|---|---|---|
| 1 | `add content calendars and slots` | `content_calendars`, `content_slots` (new) |
| 2 | `add competitor profiles and intel` | `competitor_profiles`, `intel_snapshots`, `intel_reports` (new) |
| 3 | `add memories` | `memories` (new) |
| 4 | `add cost records and budgets` | `cost_records`, `budget_configs` (new) |

```bash
alembic revision --autogenerate -m "add content calendars and slots"
alembic revision --autogenerate -m "add competitor profiles and intel"
alembic revision --autogenerate -m "add memories"
alembic revision --autogenerate -m "add cost records and budgets"
```

---

## 10. Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Autonomous social manager posts inappropriate content | HIGH | LOW | Confidence engine + human approval for high-risk; verification pipeline confirms publish |
| Content repurposing loses meaning across platforms | MEDIUM | MEDIUM | Platform format rules enforce constraints; quality scoring tracks approval rates |
| Competitive intelligence creates noise | MEDIUM | MEDIUM | Change detector uses 80% similarity threshold; only significant changes trigger alerts |
| Delegation creates infinite loops | HIGH | LOW | Max delegation depth of 3; all delegations logged |
| Memory store grows unbounded | MEDIUM | LOW | TTL for stale memories; importance-based pruning; max memory limit |
| Budget enforcement breaks critical tasks | HIGH | LOW | Soft budget by default (downgrade, not refuse); hard limit is opt-in |

---

## 11. Acceptance Criteria Summary

### Feature 5.1: Autonomous Social Manager

- [ ] Weekly cycle runs autonomously via scheduler
- [ ] Full pipeline (research → draft → fact-check → publish → verify) works
- [ ] Performance reports generated weekly
- [ ] `AUTONOMY_ENABLED=false` disables entirely

### Feature 5.2: Content Repurposing

- [ ] Platform-native versions created for X, LinkedIn, newsletter
- [ ] Constraint validation (char limits, threads, hashtags)
- [ ] `within_limits` flag indicates fit

### Feature 5.3: Competitive Intelligence

- [ ] Competitor monitoring runs on schedule
- [ ] Change detection identifies significant changes
- [ ] Intelligence reports generated and delivered

### Feature 5.4: Agent-to-Agent Delegation

- [ ] Delegation tool available to all subgraphs
- [ ] Orchestrator intercepts and handles delegation signals
- [ ] Depth limited to 3 levels

### Feature 5.5: Memory & Context

- [ ] Semantic recall works for research and content
- [ ] Memories stored with metadata and optional TTL
- [ ] `MEMORY_ENABLED=false` disables entirely

### Feature 5.6: Cost-Aware Operation

- [ ] Budget tracking works for daily/monthly scopes
- [ ] Model downgrade when budget > 80% used
- [ ] Cost records persisted per task

---

**Document version:** 1.0
**Last updated:** 2026-09-12
**Status:** Ready for implementation
