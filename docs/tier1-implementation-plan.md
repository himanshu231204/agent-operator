# Tier 1 — Semi-Autonomous: Detailed Implementation Plan

**Date:** 2026-09-12
**Status:** Ready for Implementation
**Depends on:** TODO.md Phases 3–8 (see Prerequisite Map below)
**Branch:** `feature/tier1-semi-autonomous`

---

## Table of Contents

1. [Prerequisite Dependency Map](#1-prerequisite-dependency-map)
2. [Implementation Order](#2-implementation-order)
3. [Feature 3.1 — Confidence-Based Approval](#3-feature-31--confidence-based-approval)
4. [Feature 3.2 — Self-Verification Pipeline](#4-feature-32--self-verification-pipeline)
5. [Feature 3.3 — Scheduled Task Triggers](#5-feature-33--scheduled-task-triggers)
6. [Feature 3.4 — Draft Review UI](#6-feature-34--draft-review-ui)
7. [Migration Strategy](#7-migration-strategy)
8. [Risk Matrix](#8-risk-matrix)
9. [Acceptance Criteria Summary](#9-acceptance-criteria-summary)

---

## 1. Prerequisite Dependency Map

Each Tier 1 feature depends on specific Phase 3–8 work being complete.

| Tier 1 Feature | Phase Prerequisites | Rationale |
|---|---|---|
| **3.1 Confidence Engine** | Phase 7 (Safety — approval API), Phase 8 (Observability — structured logging) | Needs approval flow to exist as fallback; needs logging for audit trail of auto-approval decisions |
| **3.2 Self-Verification** | Phase 6 (Social — publish adapters), Phase 3 (Browser — session manager) | Verification re-fetches published URLs via browser; needs real social adapters to verify against |
| **3.3 Scheduled Triggers** | Phase 8 (Production — background workers), Phase 5 (Content — content generator) | Scheduler needs a worker loop to poll triggers; needs content generation to produce task output |
| **3.4 Draft Review UI** | Phase 5 (Content — draft model + API), Phase 7 (Safety — approval API) | Needs draft CRUD endpoints and approval decision endpoints to exist |

### Dependency Graph

```
Phase 3 (Browser) ──────────┐
Phase 5 (Content) ─────┬────┤
Phase 6 (Social) ──────┤    ├──→ 3.2 Self-Verification
Phase 7 (Safety) ──┬───┤    │
Phase 8 (Workers) ─┤   │    │
                   │   │    │
                   ├───┴────┴──→ 3.1 Confidence Engine (first)
                   │
Phase 5 (Content) ─┤
Phase 8 (Workers) ─┤
                   ├──→ 3.3 Scheduler
                   │
Phase 5 (Content) ─┤
Phase 7 (Safety) ──┘──→ 3.4 Draft Review UI (last)
```

---

## 2. Implementation Order

Build sequentially in this order. Each feature is a merge-ready PR.

| Step | Feature | Effort | Depends On |
|---|---|---|---|
| 1 | Confidence Engine | 2–3 weeks | Phase 7, Phase 8 |
| 2 | Self-Verification Pipeline | 2–3 weeks | Step 1, Phase 6, Phase 3 |
| 3 | Scheduled Task Triggers | 3–4 weeks | Step 1, Phase 8, Phase 5 |
| 4 | Draft Review UI | 2–3 weeks | Phase 5, Phase 7 |

**Rationale for ordering:**

- Confidence Engine modifies the orchestrator core — build first so all subsequent features benefit from auto-approval
- Verification Pipeline depends on real social adapters — build after confidence so the orchestrator can auto-approve verification steps
- Scheduler is independent but benefits from confidence engine (scheduled tasks can auto-approve)
- Draft UI is the least technical, can be built last while other systems mature

---

## 3. Feature 3.1 — Confidence-Based Approval

### 3.1.1 Problem

All high-risk actions require human approval, creating a bottleneck when the system is operating correctly. Low-risk, high-confidence actions should auto-approve.

### 3.1.2 Files to Create

```
app/confidence/__init__.py          — Package init
app/confidence/engine.py            — ConfidenceEngine: scores actions, decides auto-approve
app/confidence/scorer.py            — ActionScorer: LLM-based confidence scoring
app/confidence/policies.py          — AutoApprovalPolicy: deterministic rules
app/schemas/confidence.py           — ConfidenceScore, AutoApprovalDecision schemas
tests/unit/test_confidence_engine.py
tests/unit/test_confidence_scorer.py
tests/unit/test_auto_approval_policy.py
tests/integration/test_auto_approval_flow.py
```

### 3.1.3 Files to Modify

| File | Change |
|---|---|
| `app/agents/orchestrator.py` | Add `ConfidenceEngine` field; call `evaluate()` before `_request_approval()` at line 194 |
| `app/config.py` | Add `ConfidenceSettings` dataclass |
| `app/api/router.py` | No new routes initially (schema import only) |

### 3.1.4 Orchestrator Integration

**Current code (orchestrator.py:194):**

```python
if step.requires_approval and step.name not in approved_actions:
    await self._request_approval(...)
    raise ApprovalRequiredError(...)
```

**New code:**

```python
if step.requires_approval and step.name not in approved_actions:
    if self.confidence_engine:
        decision = await self.confidence_engine.evaluate(step, context)
        if decision.approved:
            logger.info(
                "auto_approved",
                step=step.name,
                score=decision.confidence.value,
                reason=decision.reason,
            )
            continue
    await self._request_approval(...)
    raise ApprovalRequiredError(...)
```

### 3.1.5 Key Design Decisions

1. **ConfidenceEngine uses FAST model** — scoring is a simple classification task; no need for expensive models (roadmap Appendix B, decision 1)
2. **`always_require_approval` is deterministic** — frozenset of action names, never LLM-inferred (AGENTS.md rule 274)
3. **Auto-approval is logged** — every auto-approval record includes score, action, reason for audit trail
4. **Middle zone defaults to human** — scores between 0.4 and 0.85 require approval (conservative default)

### 3.1.6 Configuration

Add to `app/config.py`:

```python
class ConfidenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONFIDENCE_")

    enabled: bool = False
    auto_approve_threshold: float = 0.85
    never_auto_approve_threshold: float = 0.4
    scoring_model: str = "gpt-4o-mini"
```

### 3.1.7 Acceptance Criteria

- [ ] Actions in `eligible_for_auto_approve` with score ≥ 0.85 skip human approval
- [ ] Actions in `always_require_approval` ALWAYS require human approval regardless of score
- [ ] All auto-approval decisions logged with confidence score, action name, and reason
- [ ] Existing approval flow unchanged for non-eligible actions
- [ ] `CONFIDENCE_ENABLED=false` disables the engine entirely (fallback to current behavior)
- [ ] Unit tests pass for: threshold behavior, eligible action filtering, LLM scoring with fake provider
- [ ] Integration test passes for: orchestrator + confidence engine end-to-end flow

---

## 4. Feature 3.2 — Self-Verification Pipeline

### 4.2.1 Problem

After publishing, the system assumes success based on a 200 response. Real verification (is the post live? did it render correctly?) is missing.

### 4.2.2 Files to Create

```
app/verification/__init__.py        — Package init
app/verification/pipeline.py        — VerificationPipeline: multi-step verification
app/verification/checks.py          — ContentCheck, DestinationCheck, RenderCheck
app/verification/retry.py           — VerificationRetryPolicy: retry/escalate logic
app/schemas/verification.py         — VerificationStep, VerificationReport schemas
tests/unit/test_verification_pipeline.py
tests/unit/test_content_check.py
tests/unit/test_destination_check.py
tests/integration/test_verification_flow.py
```

### 4.2.3 Files to Modify

| File | Change |
|---|---|
| `app/agents/graphs/social.py` | Call `verification_pipeline.verify()` after publish step |
| `app/db/models/verification.py` | Add `VerificationStep` model (extend existing `VerificationResult`) |

### 4.2.4 Database Schema Extension

```sql
CREATE TABLE verification_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_result_id UUID REFERENCES verification_results(id) NOT NULL,
    check_name VARCHAR(64) NOT NULL,
    passed BOOLEAN NOT NULL,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 4.2.5 Integration Point in Social Graph

```python
# After publish step in social graph:
result = await social_platform.publish(draft)
verification = await verification_pipeline.verify(
    PublishedAction(
        id=result.post_id,
        url=result.url,
        expected_content=draft.content,
    ),
    context,
)
if not verification.verified:
    # Auto-retry or escalate
    ...
```

### 4.2.6 Acceptance Criteria

- [ ] ContentCheck re-fetches URL and compares with ≥ 0.9 similarity score
- [ ] DestinationCheck confirms URL returns HTTP 200
- [ ] RenderCheck screenshots page and analyzes visual quality
- [ ] Failed checks retry per `VerificationRetryPolicy` (configurable max retries)
- [ ] All verification results persisted to DB with step-level detail
- [ ] Verification report returned as part of task result
- [ ] Verification is synchronous within a task (must complete before COMPLETED state)

---

## 5. Feature 3.3 — Scheduled Task Triggers

### 5.3.1 Problem

Every task requires a human to initiate it via API. The system can't run on a schedule or respond to events.

### 5.3.2 Files to Create

```
app/scheduler/__init__.py           — Package init
app/scheduler/scheduler.py          — TaskScheduler: cron + event-based triggers
app/scheduler/triggers/__init__.py  — Trigger package
app/scheduler/triggers/base.py      — Trigger ABC, TriggerEvent schema
app/scheduler/triggers/cron.py      — CronTrigger: time-based scheduling
app/scheduler/triggers/webhook.py   — WebhookTrigger: HTTP webhook receiver
app/scheduler/triggers/rss.py       — RSSTrigger: RSS feed monitor
app/scheduler/triggers/email.py     — EmailTrigger: email instruction ingestion
app/scheduler/triggers/file.py      — FileTrigger: file system watcher
app/db/models/schedule.py           — Schedule, ScheduleRun ORM models
app/schemas/schedule.py             — ScheduleConfig, ScheduleStatus schemas
app/api/routes/schedules.py         — CRUD API for schedules
tests/unit/test_scheduler.py
tests/unit/test_cron_trigger.py
tests/unit/test_rss_trigger.py
tests/integration/test_schedule_flow.py
```

### 5.3.3 Files to Modify

| File | Change |
|---|---|
| `app/config.py` | Add `SchedulerSettings` dataclass |
| `app/api/router.py` | Include schedules router |
| `app/db/models/__init__.py` | Import new models |

### 5.3.4 Database Schema

```sql
CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    trigger_type VARCHAR(50) NOT NULL,       -- cron, webhook, rss, email, file
    config JSONB NOT NULL,                   -- trigger-specific config
    instruction_template TEXT NOT NULL,       -- template for task instruction
    is_active BOOLEAN DEFAULT TRUE,
    poll_interval_seconds INTEGER DEFAULT 60,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE schedule_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES schedules(id) NOT NULL,
    task_id UUID REFERENCES tasks(id),
    triggered_at TIMESTAMPTZ DEFAULT now(),
    event_data JSONB,
    status VARCHAR(20) NOT NULL              -- success, failed, skipped
);
```

### 5.3.5 API Endpoints

```
POST   /api/v1/schedules              — Create schedule
GET    /api/v1/schedules              — List schedules
GET    /api/v1/schedules/{id}         — Get schedule details
PUT    /api/v1/schedules/{id}         — Update schedule
DELETE /api/v1/schedules/{id}         — Delete schedule
POST   /api/v1/schedules/{id}/pause   — Pause schedule
POST   /api/v1/schedules/{id}/resume  — Resume schedule
GET    /api/v1/schedules/{id}/runs    — Schedule run history
POST   /api/v1/webhooks/{token}       — Webhook trigger endpoint
```

### 5.3.6 Configuration

```python
class SchedulerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHEDULER_")

    enabled: bool = False
    poll_interval_seconds: int = 60
    max_concurrent_triggers: int = 10
```

### 5.3.7 Acceptance Criteria

- [ ] CronTrigger fires on cron expressions (APScheduler integration)
- [ ] WebhookTrigger accepts POST with token authentication
- [ ] RSSTrigger polls feeds and filters by keywords
- [ ] Each trigger fire creates a Task via TaskService and runs orchestrator
- [ ] Schedule CRUD API endpoints functional
- [ ] Pause/resume toggles `is_active` flag
- [ ] Schedule run history queryable
- [ ] `SCHEDULER_ENABLED=false` disables the scheduler entirely

---

## 6. Feature 3.4 — Draft Review UI

### 6.4.1 Problem

Approvals are raw JSON via API. Humans need a visual interface to review drafts before approving.

### 6.4.2 Files to Create

```
app/api/routes/drafts.py            — Draft CRUD + approval endpoints
app/api/routes/dashboard.py         — Dashboard API endpoints
frontend/index.html                  — Dashboard home
frontend/drafts.html                 — Draft review page
frontend/approvals.html              — Approval queue page
frontend/task-detail.html            — Task execution detail page
tests/unit/test_drafts_api.py
tests/unit/test_dashboard_api.py
```

### 6.4.3 Files to Modify

| File | Change |
|---|---|
| `app/api/router.py` | Include drafts and dashboard routers |

### 6.4.4 API Endpoints

```
GET    /api/v1/drafts                  — List drafts pending review
GET    /api/v1/drafts/{id}             — Get draft with full context
PUT    /api/v1/drafts/{id}             — Edit draft content
POST   /api/v1/drafts/{id}/approve     — Approve draft
POST   /api/v1/drafts/{id}/reject      — Reject draft with reason
GET    /api/v1/dashboard/tasks         — Active tasks with status
GET    /api/v1/dashboard/approvals     — Pending approvals queue
```

### 6.4.5 Acceptance Criteria

- [ ] Draft list shows pending items with content preview
- [ ] Draft detail shows full content + research sources
- [ ] One-click approve/reject with optional feedback text
- [ ] Dashboard shows active tasks with real-time status
- [ ] Frontend served via FastAPI static files or Jinja2 templates
- [ ] Authentication required for all endpoints
- [ ] CORS restricted to configured origins

---

## 7. Migration Strategy

Run Alembic migrations in order:

| Order | Migration | Tables Affected |
|---|---|---|
| 1 | `add confidence settings` | No new tables (config only) |
| 2 | `add verification steps` | `verification_steps` (extend existing) |
| 3 | `add schedules and schedule_runs` | `schedules`, `schedule_runs` (new) |
| 4 | `add draft review endpoints` | No new tables (API only) |

```bash
alembic revision --autogenerate -m "add confidence settings"
alembic revision --autogenerate -m "add verification steps"
alembic revision --autogenerate -m "add schedules and schedule_runs"
alembic revision --autogenerate -m "add draft review endpoints"
```

---

## 8. Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Confidence engine auto-approves unsafe action | HIGH | LOW | `always_require_approval` frozenset is deterministic; all auto-approvals logged |
| Scheduler creates duplicate tasks | MEDIUM | MEDIUM | `schedule_runs` tracks triggered_at + event_data for deduplication |
| Verification pipeline false positives | MEDIUM | MEDIUM | Configurable similarity threshold; escalation on repeated failures |
| Draft UI exposes sensitive content | MEDIUM | LOW | Authentication required; CORS restricted |
| Scheduler triggers overwhelm system | MEDIUM | LOW | `max_concurrent_triggers` limit; `poll_interval_seconds` minimum |
| Confidence LLM scoring adds latency | LOW | MEDIUM | FAST model; scoring is synchronous before step execution |

---

## 9. Acceptance Criteria Summary

### Feature 3.1: Confidence Engine

- [ ] Auto-approval works for eligible actions with score ≥ 0.85
- [ ] Always-require-approval actions are never auto-approved
- [ ] All decisions logged for audit trail
- [ ] `CONFIDENCE_ENABLED=false` disables entirely
- [ ] Unit + integration tests pass

### Feature 3.2: Self-Verification

- [ ] Content, destination, and render checks functional
- [ ] Retry policy configurable
- [ ] Results persisted to DB
- [ ] Synchronous within task execution

### Feature 3.3: Scheduled Triggers

- [ ] Cron, webhook, RSS triggers functional
- [ ] Schedule CRUD API works
- [ ] Pause/resume toggles active state
- [ ] `SCHEDULER_ENABLED=false` disables entirely

### Feature 3.4: Draft Review UI

- [ ] Draft list, detail, approve, reject endpoints work
- [ ] Dashboard shows active tasks
- [ ] Frontend renders correctly
- [ ] Authentication enforced

---

**Document version:** 1.0
**Last updated:** 2026-09-12
**Status:** Ready for implementation
