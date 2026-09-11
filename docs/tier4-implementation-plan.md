# Tier 4 — Platform / Ecosystem: Detailed Implementation Plan

**Date:** 2026-09-12
**Status:** Ready for Implementation
**Depends on:** Tier 1–3 complete (see Prerequisite Map below)
**Branch:** `feature/tier4-platform-ecosystem`

---

## Table of Contents

1. [Prerequisite Dependency Map](#1-prerequisite-dependency-map)
2. [Implementation Order](#2-implementation-order)
3. [Feature 6.1 — Skill API](#3-feature-61--skill-api)
4. [Feature 6.2 — Plugin System](#4-feature-62--plugin-system)
5. [Feature 6.3 — Multi-Agent Orchestration Mode](#5-feature-63--multi-agent-orchestration-mode)
6. [Feature 6.4 — Audit & Compliance API](#6-feature-64--audit--compliance-api)
7. [Migration Strategy](#7-migration-strategy)
8. [Risk Matrix](#8-risk-matrix)
9. [Acceptance Criteria Summary](#9-acceptance-criteria-summary)

---

## 1. Prerequisite Dependency Map

Each Tier 4 feature depends on specific Tier 1–3 work being complete.

| Tier 4 Feature | Tier 1–3 Prerequisites | Rationale |
|---|---|---|
| **6.1 Skill API** | Tier 3 (Agent-to-Agent Delegation) | Skills are invoked via the same delegation mechanism; needs all subgraphs to exist |
| **6.2 Plugin System** | Tier 1 (Confidence Engine), Tier 2 (Feedback Loop) | Plugins register tools and social platforms; needs confidence engine for approval, feedback for learning |
| **6.3 Multi-Agent Orchestration** | Tier 3 (Scheduler), Tier 6 (Cost-Aware) | Needs scheduler for worker loops; needs cost engine for budget-aware routing across orchestrators |
| **6.4 Audit & Compliance API** | All Tiers | Needs data from all subsystems (approvals, feedback, cost, verification, scheduling) |

### Dependency Graph

```
Tier 3 (Delegation) ────────────────→ 6.1 Skill API
                                     │
Tier 1 (Confidence) ──┬──→ 6.2 Plugin System
Tier 2 (Feedback) ────┘
                                     │
Tier 3 (Scheduler) ───┬──→ 6.3 Multi-Agent Orchestration
Tier 3 (Cost-Aware) ──┘
                                     │
All Tiers ──────────────────────────→ 6.4 Audit & Compliance API
```

**Parallelizable:** Features 6.1, 6.2, 6.3 can be built in parallel after their prerequisites. Feature 6.4 should be built last (needs data from all subsystems).

---

## 2. Implementation Order

Build sequentially in this order. Each feature is a merge-ready PR.

| Step | Feature | Effort | Depends On |
|---|---|---|---|
| 1 | Skill API | 2–3 weeks | Tier 3 |
| 2 | Plugin System | 2–3 weeks | Tier 1, Tier 2 |
| 3 | Multi-Agent Orchestration | 3–4 weeks | Tier 3 |
| 4 | Audit & Compliance API | 2–3 weeks | All Tiers |

**Rationale for ordering:**

- Skill API is the simplest — expose existing skills as REST endpoints
- Plugin System is next — extend tool/social/trigger registration
- Multi-Agent Orchestration is complex — needs scheduler + cost engine
- Audit & Compliance API is last — needs data from all subsystems to query

---

## 3. Feature 6.1 — Skill API

### 3.1.1 Problem

Skills are only usable within Agent Operator. External systems (Claude Code, Codex) can't consume them.

### 3.1.2 Files to Create

```
app/api/routes/skills.py              — Skill API endpoints
app/skills/registry.py                — SkillRegistry: discover and manage skills
app/schemas/skill.py                  — SkillDefinition, SkillRequest, SkillResponse schemas
tests/unit/test_skill_api.py
tests/unit/test_skill_registry.py
tests/integration/test_skill_api_flow.py
```

### 3.1.3 Files to Modify

| File | Change |
|---|---|
| `app/api/router.py` | Include skills router |
| `app/config.py` | Add `SkillAPISettings` |

### 3.1.4 API Endpoints

```
GET    /api/v1/skills                    — List available skills
GET    /api/v1/skills/{name}             — Get skill definition (SKILL.md content)
POST   /api/v1/skills/{name}/execute     — Execute a skill with input
GET    /api/v1/skills/{name}/status      — Get skill execution status
GET    /api/v1/skills/{name}/schema      — Get input/output JSON schema
```

### 3.1.5 Skill Registry

```python
class SkillRegistry:
    """Discover and manage skills from the skills/ directory."""

    def __init__(self, skills_dir: str = "skills"):
        self._skills_dir = Path(skills_dir)
        self._skills: dict[str, SkillDefinition] = {}

    async def discover(self) -> list[SkillDefinition]:
        """Scan skills/ directory for SKILL.md files."""
        skills = []
        for skill_dir in self._skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_md = skill_dir / "SKILL.md"
                if skill_md.exists():
                    definition = self._parse_skill_md(skill_md)
                    self._skills[definition.name] = definition
                    skills.append(definition)
        return skills

    async def get_skill(self, name: str) -> SkillDefinition:
        """Get a skill by name."""
        if name not in self._skills:
            await self.discover()
        return self._skills.get(name, raise SkillNotFound(name))

    def build_instruction(self, skill: SkillDefinition, request: SkillRequest) -> str:
        """Build an orchestrator instruction from skill + input."""
        return f"Execute skill '{skill.name}': {request.instruction}"
```

### 3.1.6 Database Schema

```sql
CREATE TABLE skill_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name VARCHAR(128) NOT NULL,
    task_id UUID REFERENCES tasks(id),
    input JSONB,
    output JSONB,
    status VARCHAR(32) NOT NULL,           -- pending, running, completed, failed
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX ix_skill_executions_name ON skill_executions(skill_name);
CREATE INDEX ix_skill_executions_status ON skill_executions(status);
```

### 3.1.7 Acceptance Criteria

- [ ] `SkillRegistry.discover()` finds all skills with SKILL.md
- [ ] `GET /skills` returns list of available skills with schemas
- [ ] `POST /skills/{name}/execute` creates task and runs orchestrator
- [ ] `GET /skills/{name}/status` returns execution status
- [ ] Skill execution tracked in `skill_executions` table
- [ ] `SKILL_API_ENABLED=false` disables skill API
- [ ] Authentication required for all endpoints
- [ ] Unit tests pass for: registry discovery, API endpoints, execution flow

---

## 4. Feature 6.2 — Plugin System

### 4.2.1 Problem

Adding new tools or platform integrations requires modifying core agent code.

### 4.2.2 Files to Create

```
app/plugins/__init__.py                — Package init
app/plugins/base.py                    — Plugin ABC: base class for plugins
app/plugins/loader.py                  — PluginLoader: discover and load plugins
app/plugins/registry.py                — PluginRegistry: manage plugin lifecycle
app/schemas/plugin.py                  — PluginDefinition, PluginContext schemas
plugins/example_plugin/                — Example plugin directory
plugins/example_plugin/plugin.py       — Example plugin implementation
plugins/example_plugin/SKILL.md        — Example plugin documentation
tests/unit/test_plugin_loader.py
tests/unit/test_plugin_registry.py
tests/integration/test_plugin_flow.py
```

### 4.2.3 Files to Modify

| File | Change |
|---|---|
| `app/config.py` | Add `PluginSettings` |
| `app/tools/registry.py` | Add `register_plugin_tools()` method |
| `app/social/` | Add plugin social platform registration |

### 4.2.4 Plugin Base Class

```python
class Plugin(ABC):
    """Base class for Agent Operator plugins."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    async def activate(self, context: PluginContext) -> None:
        """Called when the plugin is loaded."""
        ...

    def get_tools(self) -> list[BaseTool]:
        """Return tools this plugin provides."""
        return []

    def get_social_platforms(self) -> list[SocialPlatform]:
        """Return social platforms this plugin provides."""
        return []

    def get_triggers(self) -> list[Trigger]:
        """Return scheduler triggers this plugin provides."""
        return []
```

### 4.2.5 Plugin Loader

```python
class PluginLoader:
    """Discover and load plugins from the plugins/ directory."""

    async def discover_plugins(self, plugin_dir: str = "plugins") -> list[Plugin]:
        """Scan directory for plugin modules."""
        plugins = []
        for path in Path(plugin_dir).glob("*/plugin.py"):
            module = importlib.import_module(str(path.with_suffix("")))
            if hasattr(module, "PluginClass"):
                plugins.append(module.PluginClass())
        return plugins

    async def load_plugins(self, context: PluginContext) -> None:
        """Load all discovered plugins."""
        plugins = await self.discover_plugins()
        for plugin in plugins:
            await plugin.activate(context)
            # Register tools
            for tool in plugin.get_tools():
                context.registry.register(tool)
            # Register social platforms
            for platform in plugin.get_social_platforms():
                context.social_registry.register(platform)
            # Register triggers
            for trigger in plugin.get_triggers():
                context.scheduler.register_trigger(trigger)
            logger.info("plugin.loaded", name=plugin.name, version=plugin.version)
```

### 4.2.6 Plugin Security

```python
class PluginContext:
    """Restricted context passed to plugins."""

    def __init__(
        self,
        registry: ToolRegistry,
        social_registry: SocialRegistry,
        scheduler: TaskScheduler,
    ):
        self.registry = registry
        self.social_registry = social_registry
        self.scheduler = scheduler
        # Plugins CANNOT access:
        # - Database directly (must use services)
        # - Orchestrator directly (must use tools)
        # - Configuration directly (must use context)
```

### 4.2.7 Database Schema

```sql
CREATE TABLE plugins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL UNIQUE,
    version VARCHAR(32) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    loaded_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 4.2.8 Acceptance Criteria

- [ ] `PluginLoader.discover_plugins()` finds plugins in plugins/ directory
- [ ] `PluginLoader.load_plugins()` activates plugins and registers tools
- [ ] Plugin tools available via `ToolExecutionEngine`
- [ ] Plugin social platforms available via social adapters
- [ ] Plugin triggers available via scheduler
- [ ] Plugins cannot access database directly (security)
- [ ] `PLUGIN_ENABLED=false` disables plugin loading
- [ ] Example plugin provided as reference
- [ ] Unit tests pass for: loader, registry, security boundaries

---

## 5. Feature 6.3 — Multi-Agent Orchestration Mode

### 5.3.1 Problem

One orchestrator handles all task types. This doesn't scale for high-throughput deployments.

### 5.3.2 Files to Create

```
app/orchestration/__init__.py          — Package init
app/orchestration/cluster.py           — OrchestratorCluster: manage multiple orchestrators
app/orchestration/load_balancer.py     — LoadBalancer: distribute tasks
app/orchestration/worker_pool.py       — WorkerPool: manage worker processes
app/db/models/task_queue.py            — TaskQueue ORM model
app/schemas/orchestration.py           — TaskQueueEntry, WorkerStatus schemas
tests/unit/test_orchestrator_cluster.py
tests/unit/test_load_balancer.py
tests/integration/test_multi_agent_flow.py
```

### 5.3.3 Files to Modify

| File | Change |
|---|---|
| `app/config.py` | Add `OrchestrationSettings` |
| `app/api/router.py` | Add cluster status endpoint |

### 5.3.4 Database Schema

```sql
CREATE TABLE task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) NOT NULL,
    task_type VARCHAR(64) NOT NULL,        -- research, content, browser, etc.
    priority INTEGER DEFAULT 0,
    status VARCHAR(32) DEFAULT 'queued',   -- queued, running, completed, failed
    worker_id VARCHAR(64),
    enqueued_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX ix_task_queue_status ON task_queue(status);
CREATE INDEX ix_task_queue_type_priority ON task_queue(task_type, priority DESC);
```

### 5.3.5 Load Balancer

```python
class LoadBalancer:
    """Distribute tasks across workers using PostgreSQL SKIP LOCKED."""

    async def enqueue(self, task_type: str, task: Task):
        """Add a task to the queue."""
        async with self.session_factory() as session:
            await session.execute(
                insert(TaskQueue).values(
                    task_id=task.id,
                    task_type=task_type,
                    priority=task.priority,
                    status="queued",
                )
            )
            await session.commit()

    async def dequeue(self, task_type: str, worker_id: str) -> Task | None:
        """Pick up the next available task."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(TaskQueue)
                .where(TaskQueue.task_type == task_type, TaskQueue.status == "queued")
                .order_by(TaskQueue.priority.desc(), TaskQueue.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            row = result.scalar_one_or_none()
            if row:
                row.status = "running"
                row.worker_id = worker_id
                await session.commit()
                return await self._load_task(session, row.task_id)
        return None
```

### 5.3.6 Orchestrator Cluster

```python
class OrchestratorCluster:
    """Manage multiple specialized orchestrators."""

    def __init__(
        self,
        orchestrators: dict[str, Orchestrator],  # task_type -> orchestrator
        load_balancer: LoadBalancer,
        worker_count: int = 2,
    ):
        self.orchestrators = orchestrators
        self.load_balancer = load_balancer
        self.worker_count = worker_count

    async def submit_task(self, task: Task) -> str:
        """Route a task to the appropriate orchestrator."""
        task_type = self._classify_task(task)
        await self.load_balancer.enqueue(task_type, task)
        return str(task.id)

    async def start(self):
        """Start all orchestrator worker loops."""
        tasks = []
        for name, orch in self.orchestrators.items():
            for i in range(self.worker_count):
                worker_id = f"{name}:worker:{i}"
                tasks.append(self._worker_loop(name, orch, worker_id))
        await asyncio.gather(*tasks)

    async def _worker_loop(self, name: str, orch: Orchestrator, worker_id: str):
        """Continuous worker loop picking tasks from queue."""
        while True:
            task = await self.load_balancer.dequeue(name, worker_id)
            if task:
                await orch.run(str(task.id))
            else:
                await asyncio.sleep(1)  # No tasks, wait before polling
```

### 5.3.7 Configuration

```python
class OrchestrationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORCHESTRATION_")

    enabled: bool = False
    worker_count: int = 2
    task_types: list[str] = Field(
        default_factory=lambda: ["research", "content", "browser", "social"]
    )
    poll_interval_seconds: int = 1
    max_queue_size: int = 100
```

### 5.3.8 Acceptance Criteria

- [ ] `OrchestratorCluster` manages multiple orchestrators by task type
- [ ] `LoadBalancer.enqueue()` adds tasks to queue with priority
- [ ] `LoadBalancer.dequeue()` picks tasks using `SKIP LOCKED` (no double-processing)
- [ ] Worker loops run continuously, processing queued tasks
- [ ] Task classification routes to appropriate orchestrator
- [ ] `ORCHESTRATION_ENABLED=false` uses single orchestrator (current behavior)
- [ ] Queue size limit prevents memory exhaustion
- [ ] Unit tests pass for: cluster, load balancer, worker loop

---

## 6. Feature 6.4 — Audit & Compliance API

### 6.4.1 Problem

No way to query the full history of what the system did.

### 6.4.2 Files to Create

```
app/api/routes/audit.py                — Audit API endpoints
app/audit/__init__.py                  — Package init
app/audit/query.py                     — AuditQuery: flexible audit log querying
app/audit/reporter.py                  — ComplianceReporter: generate compliance reports
app/db/models/audit.py                 — AuditLog ORM model
app/schemas/audit.py                   — AuditEntry, AuditTimeline, ComplianceReport schemas
tests/unit/test_audit_query.py
tests/unit/test_compliance_reporter.py
tests/integration/test_audit_flow.py
```

### 6.4.3 Files to Modify

| File | Change |
|---|---|
| `app/api/router.py` | Include audit router |
| `app/config.py` | Add `AuditSettings` |

### 6.4.4 API Endpoints

```
GET    /api/v1/audit/actions            — Query all actions
GET    /api/v1/audit/actions/{id}       — Get action detail with provenance
GET    /api/v1/audit/tasks/{id}/timeline — Full task execution timeline
GET    /api/v1/audit/models             — Model usage statistics
GET    /api/v1/audit/approvals          — Approval history
GET    /api/v1/audit/compliance/report  — Generate compliance report
GET    /api/v1/audit/export             — Export audit log (CSV/JSON)
```

### 6.4.5 Database Schema

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(64) NOT NULL,       -- task.created, approval.auto_approved, model.selected, etc.
    entity_type VARCHAR(32),               -- task, approval, model, verification, etc.
    entity_id UUID,
    task_id UUID,
    run_id UUID,
    actor VARCHAR(64),                     -- user, system, plugin
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_audit_logs_event ON audit_logs(event_type);
CREATE INDEX ix_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX ix_audit_logs_task ON audit_logs(task_id);
CREATE INDEX ix_audit_logs_created ON audit_logs(created_at);
```

### 6.4.6 Audit Query

```python
class AuditQuery:
    """Flexible audit log querying."""

    async def query(
        self,
        event_type: str | None = None,
        entity_type: str | None = None,
        task_id: uuid.UUID | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit logs with flexible filters."""
        stmt = select(AuditLog)

        if event_type:
            stmt = stmt.where(AuditLog.event_type == event_type)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if task_id:
            stmt = stmt.where(AuditLog.task_id == task_id)
        if start_time:
            stmt = stmt.where(AuditLog.created_at >= start_time)
        if end_time:
            stmt = stmt.where(AuditLog.created_at <= end_time)

        stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return [AuditEntry.from_orm(row) for row in result.scalars()]

    async def get_task_timeline(self, task_id: uuid.UUID) -> AuditTimeline:
        """Get full execution timeline for a task."""
        entries = await self.query(task_id=task_id, limit=1000)
        return AuditTimeline(
            task_id=task_id,
            entries=entries,
            duration_ms=self._calculate_duration(entries),
        )
```

### 6.4.7 Compliance Reporter

```python
class ComplianceReporter:
    """Generate compliance reports."""

    async def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> ComplianceReport:
        """Generate a compliance report for a date range."""
        # Gather data from all subsystems
        tasks = await self._get_tasks(start_date, end_date)
        approvals = await self._get_approvals(start_date, end_date)
        model_usage = await self._get_model_usage(start_date, end_date)
        verifications = await self._get_verifications(start_date, end_date)

        return ComplianceReport(
            period_start=start_date,
            period_end=end_date,
            total_tasks=len(tasks),
            completed_tasks=len([t for t in tasks if t.state == "completed"]),
            failed_tasks=len([t for t in tasks if t.state == "failed"]),
            auto_approvals=len([a for a in approvals if a.auto_approved]),
            human_approvals=len([a for a in approvals if not a.auto_approved]),
            model_usage_summary=model_usage,
            verification_success_rate=self._calc_verification_rate(verifications),
            generated_at=datetime.utcnow(),
        )
```

### 6.4.8 Key Design Decisions

1. **Audit logs are append-only** — never modified or deleted (compliance requirement)
2. **All subsystems emit audit events** — confidence engine, feedback loop, scheduler, etc.
3. **Compliance report is generated on-demand** — not cached (always fresh data)
4. **Export supports CSV and JSON** — for external analysis tools

### 6.4.9 Acceptance Criteria

- [ ] `AuditQuery.query()` filters by event_type, entity_type, task_id, time range
- [ ] `AuditQuery.get_task_timeline()` returns full execution timeline
- [ ] `ComplianceReporter.generate_report()` aggregates data from all subsystems
- [ ] `GET /audit/actions` returns filtered audit entries
- [ ] `GET /audit/tasks/{id}/timeline` returns task execution timeline
- [ ] `GET /audit/compliance/report` generates compliance report
- [ ] `GET /audit/export` exports audit log as CSV/JSON
- [ ] Audit logs are append-only (no update/delete operations)
- [ ] `AUDIT_ENABLED=false` disables audit logging (not recommended)
- [ ] Unit tests pass for: query, timeline, compliance report, export

---

## 7. Migration Strategy

Run Alembic migrations in order:

| Order | Migration | Tables Affected |
|---|---|---|
| 1 | `add skill executions` | `skill_executions` (new) |
| 2 | `add plugins` | `plugins` (new) |
| 3 | `add task queue` | `task_queue` (new) |
| 4 | `add audit logs` | `audit_logs` (new) |

```bash
alembic revision --autogenerate -m "add skill executions"
alembic revision --autogenerate -m "add plugins"
alembic revision --autogenerate -m "add task queue"
alembic revision --autogenerate -m "add audit logs"
```

---

## 8. Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Plugin executes malicious code | HIGH | LOW | Plugins run in-process with restricted context; no direct DB access |
| Multi-agent orchestrator creates duplicates | MEDIUM | MEDIUM | `SKIP LOCKED` prevents double-processing; task_queue tracks status |
| Audit log storage grows unbounded | MEDIUM | LOW | Configurable retention policy; archival to cold storage |
| Skill API exposes sensitive skills | MEDIUM | LOW | Authentication required; skill-level access control |
| Load balancer starves low-priority tasks | MEDIUM | LOW | Priority queue with aging (priority increases over time) |
| Plugin conflicts with core tools | MEDIUM | LOW | Tool namespaced by plugin name; conflict detection on registration |

---

## 9. Acceptance Criteria Summary

### Feature 6.1: Skill API

- [ ] Skills discoverable via SKILL.md
- [ ] REST endpoints for list, execute, status, schema
- [ ] Skill execution tracked in DB
- [ ] `SKILL_API_ENABLED=false` disables entirely

### Feature 6.2: Plugin System

- [ ] Plugins discovered from plugins/ directory
- [ ] Tools, social platforms, triggers registered
- [ ] Security: no direct DB access
- [ ] Example plugin provided

### Feature 6.3: Multi-Agent Orchestration

- [ ] Multiple orchestrators managed by cluster
- [ ] Load balancer uses SKIP LOCKED
- [ ] Worker loops process tasks continuously
- [ ] `ORCHESTRATION_ENABLED=false` uses single orchestrator

### Feature 6.4: Audit & Compliance API

- [ ] Flexible query by event, entity, task, time
- [ ] Task execution timeline works
- [ ] Compliance report generated on-demand
- [ ] Export as CSV/JSON
- [ ] Audit logs append-only

---

**Document version:** 1.0
**Last updated:** 2026-09-12
**Status:** Ready for implementation
