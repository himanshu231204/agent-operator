# Agent Operator — Full Autonomy Implementation Plan

**Date:** 2026-09-12
**Status:** Planning
**Depends on:** PROJECT.md, AGENTS.md, TODO.md (Phases 1–8)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture Vision](#2-architecture-vision)
3. [Tier 1 — Semi-Autonomous (Remove Human Bottlenecks)](#3-tier-1--semi-autonomous)
4. [Tier 2 — Self-Improving (Learn and Adapt)](#4-tier-2--self-improving)
5. [Tier 3 — Fully Autonomous (Self-Running Operations)](#5-tier-3--fully-autonomous)
6. [Tier 4 — Platform / Ecosystem](#6-tier-4--platform--ecosystem)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Implementation Timeline](#8-implementation-timeline)
9. [Updated Repository Structure](#9-updated-repository-structure)

---

## 1. Overview

Agent Operator is currently a production-grade foundation with Phases 1–2 complete.
This document defines the path from "human-triggered, human-approved tasks" to
"a self-running, self-improving AI operations platform."

**Autonomy levels:**

| Tier | Name | Human Role | System Role |
|------|------|-----------|-------------|
| 1 | Semi-Autonomous | Approve final output | Execute full pipeline, auto-verify |
| 2 | Self-Improving | Review weekly summary | Learn from feedback, self-heal |
| 3 | Fully Autonomous | Set goals, collect reports | Monitor, decide, act, verify |
| 4 | Platform / Ecosystem | Consume as API | Expose skills, enable plugins |

**Guiding principle:** Autonomy scales with verification. Build robust
verification first, then gradually reduce approval gates as trust builds.

**Prerequisite:** All items in TODO.md Phases 3–8 must be complete before
Tier 1 work begins. This plan assumes that foundation is in place.

---

## 2. Architecture Vision

### 2.1 Current State (Phases 1–2)

```
User → API → Orchestrator → Planner → Subgraphs → Tools → External
                ↕
           PostgreSQL (state, checkpoints)
```

### 2.2 Target State (After All Tiers)

```
Triggers (cron, webhook, email, RSS, API)
    ↓
Scheduler → Orchestrator → Planner → Subgraphs → Tools → External
    ↕                ↕              ↕
PostgreSQL       Memory Store    Feedback DB
(state)          (vector)        (engagement)
    ↕                ↕              ↕
Observability    Cost Engine     Learning Pipeline
(LangSmith)      (budget ctrl)   (RLHF loop)
    ↓
Reports → User (Slack, email, dashboard)
```

### 2.3 New Subsystems

| Subsystem | Purpose | Location |
|-----------|---------|----------|
| Scheduler | Time-based and event-based task triggers | `app/scheduler/` |
| Memory Store | Cross-task knowledge recall (vector DB) | `app/memory/` |
| Feedback Engine | Track approval/rejection patterns, engagement | `app/feedback/` |
| Confidence Engine | LLM-based risk scoring for auto-approval | `app/confidence/` |
| Verification Pipeline | Multi-step external action verification | `app/verification/` |
| Cost Engine | Budget tracking, model routing optimization | `app/cost/` |
| Skill API | REST endpoints for composable skill consumption | `app/api/routes/skills.py` |
| Plugin System | Dynamic tool/platform registration | `app/plugins/` |
| Dashboard | Real-time task monitoring + draft review | `app/api/routes/dashboard.py` |

---

## 3. Tier 1 — Semi-Autonomous

**Goal:** Remove human bottlenecks from the execution pipeline while keeping
humans in control of final output quality.

**Prerequisite:** TODO.md Phases 3–8 complete.

---

### 3.1 Confidence-Based Approval

**Problem:** Currently ALL high-risk actions require human approval, which
creates a bottleneck when the system is operating correctly.

**Solution:** An LLM-based confidence engine scores each action. Low-risk
actions with high confidence auto-approve; high-risk actions with low
confidence still require human approval.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/confidence/__init__.py` | Package init |
| `app/confidence/engine.py` | `ConfidenceEngine` — scores action safety |
| `app/confidence/scorer.py` | `ActionScorer` — LLM-based confidence scoring |
| `app/confidence/policies.py` | `AutoApprovalPolicy` — rules for when auto-approve is allowed |
| `app/schemas/confidence.py` | `ConfidenceScore`, `AutoApprovalDecision` |

#### Implementation Details

```python
# app/confidence/engine.py

@dataclass
class ConfidenceEngine:
    """Scores actions and decides whether auto-approval is safe."""
    
    router: ModelRouter
    policy: AutoApprovalPolicy
    feedback: FeedbackEngine  # Tier 2 dependency; None until then
    
    async def evaluate(
        self,
        action: PlanStep,
        context: TaskContext,
    ) -> AutoApprovalDecision:
        """Return approve/reject/pending based on confidence score."""
        score = await self._score_action(action, context)
        
        if score.value >= self.policy.auto_approve_threshold:
            return AutoApprovalDecision(
                approved=True,
                confidence=score,
                reason="High confidence — auto-approved",
            )
        if score.value <= self.policy.never_auto_approve_threshold:
            return AutoApprovalDecision(
                approved=False,
                confidence=score,
                reason="Low confidence — requires human approval",
            )
        # Middle zone: check historical patterns (Tier 2) or require approval
        return AutoApprovalDecision(
            approved=False,
            confidence=score,
            reason="Medium confidence — defaulting to human approval",
        )
```

```python
# app/confidence/scorer.py

class ActionScorer:
    """LLM-based scoring of action safety and success likelihood."""
    
    async def score(self, action: PlanStep, context: TaskContext) -> ConfidenceScore:
        """Use FAST model to score: will this action succeed? Is it reversible?"""
        model = self.router.route(RoutingCriteria(
            task_complexity=TaskComplexity.SIMPLE,
            requires_reasoning=False,
        ))
        # Structured output: { confidence: float, risk_factors: list[str], 
        #                      reversible: bool, similar_past_actions: int }
        ...
```

```python
# app/confidence/policies.py

@dataclass
class AutoApprovalPolicy:
    """Deterministic rules for auto-approval (never LLM-inferred)."""
    
    auto_approve_threshold: float = 0.85
    never_auto_approve_threshold: float = 0.4
    
    # Actions that ALWAYS require human approval regardless of confidence
    always_require_approval: frozenset[str] = frozenset({
        "publish", "send", "purchase", "delete", "submit",
    })
    
    # Actions that can auto-approve if confidence is high enough
    eligible_for_auto_approve: frozenset[str] = frozenset({
        "research", "draft", "summarize", "extract", "classify",
    })
    
    def is_eligible(self, action: str) -> bool:
        return action in self.eligible_for_auto_approve
```

#### Integration with Orchestrator

Modify `app/agents/orchestrator.py`:

```python
# In _execute_plan, replace the current approval check:
async def _execute_plan(self, ...):
    for index, step in enumerate(plan.steps):
        if step.requires_approval and step.name not in approved_actions:
            # NEW: Check confidence before requesting human approval
            if self.confidence_engine and self.confience_policy.is_eligible(step.name):
                decision = await self.confidence_engine.evaluate(step, context)
                if decision.approved:
                    logger.info("auto_approved", step=step.name, confidence=decision.confidence)
                    continue  # Skip human approval
            
            # Fallback: existing human approval flow
            await self._request_approval(...)
```

#### Testing

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_confidence_engine.py` | Scoring logic, threshold behavior |
| `tests/unit/test_confidence_scorer.py` | LLM scoring with fake provider |
| `tests/unit/test_auto_approval_policy.py` | Policy rules, eligible actions |
| `tests/integration/test_auto_approval_flow.py` | Orchestrator + confidence engine |

#### Effort Estimate: **2–3 weeks**

---

### 3.2 Self-Verification Loops

**Problem:** After publishing, the system assumes success based on a 200 response.
Real verification (is the post live? did it render correctly?) is missing.

**Solution:** A dedicated verification pipeline that re-fetches published content,
confirms content/destination, and auto-retries or escalates on failure.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/verification/__init__.py` | Package init |
| `app/verification/pipeline.py` | `VerificationPipeline` — multi-step verification |
| `app/verification/checks.py` | `ContentCheck`, `DestinationCheck`, `RenderCheck` |
| `app/verification/retry.py` | `VerificationRetryPolicy` — retry/escalate logic |
| `app/schemas/verification.py` | `VerificationStep`, `VerificationReport` |

#### Implementation Details

```python
# app/verification/pipeline.py

@dataclass
class VerificationPipeline:
    """Verify external actions after execution."""
    
    checks: list[VerificationCheck]
    retry_policy: VerificationRetryPolicy
    
    async def verify(
        self,
        action: PublishedAction,
        context: TaskContext,
    ) -> VerificationReport:
        """Run all checks, retry on failure, escalate if unverifiable."""
        results = []
        for check in self.checks:
            result = await check.verify(action, context)
            results.append(result)
            
            if not result.passed and self.retry_policy.should_retry(result):
                retry_result = await self._retry_check(check, action, context)
                results.append(retry_result)
        
        overall = all(r.passed for r in results)
        return VerificationReport(
            action_id=action.id,
            verified=overall,
            steps=results,
            verified_at=datetime.utcnow(),
        )
```

```python
# app/verification/checks.py

class ContentCheck(VerificationCheck):
    """Re-fetch the published URL and confirm content matches."""
    
    async def verify(self, action: PublishedAction, ctx: TaskContext) -> VerificationStep:
        fetched = await self.fetch_tool.fetch(action.url)
        match = self._compare_content(action.expected_content, fetched.text)
        return VerificationStep(
            check="content_match",
            passed=match.score >= 0.9,
            details={"similarity": match.score, "differences": match.differences},
        )

class DestinationCheck(VerificationCheck):
    """Confirm the post appears at the expected destination."""
    
    async def verify(self, action: PublishedAction, ctx: TaskContext) -> VerificationStep:
        exists = await self._check_url_exists(action.url)
        return VerificationStep(
            check="destination_exists",
            passed=exists,
            details={"url": action.url, "status_code": exists.status_code},
        )

class RenderCheck(VerificationCheck):
    """Screenshot the published page and verify visual rendering."""
    
    async def verify(self, action: PublishedAction, ctx: TaskContext) -> VerificationStep:
        screenshot = await self.browser.screenshot(action.url)
        analysis = await self._analyze_screenshot(screenshot, action.expected_visual)
        return VerificationStep(
            check="render_quality",
            passed=analysis.acceptable,
            details={"visual_score": analysis.score},
        )
```

#### Integration with Social Agents

Modify `app/agents/graphs/social.py` to call verification after publish:

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

#### Testing

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_verification_pipeline.py` | Check orchestration, retry logic |
| `tests/unit/test_content_check.py` | Content comparison with mocked fetch |
| `tests/unit/test_destination_check.py` | URL existence with mocked browser |
| `tests/integration/test_verification_flow.py` | End-to-end with mock social adapter |

#### Effort Estimate: **2–3 weeks**

---

### 3.3 Scheduled Task Triggers

**Problem:** Every task requires a human to initiate it via API. The system
can't run on a schedule or respond to events.

**Solution:** A scheduler that triggers tasks from cron expressions, webhooks,
email monitors, and RSS feeds.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/scheduler/__init__.py` | Package init |
| `app/scheduler/scheduler.py` | `TaskScheduler` — cron + event-based triggers |
| `app/scheduler/triggers/` | Trigger implementations |
| `app/scheduler/triggers/cron.py` | `CronTrigger` — time-based scheduling |
| `app/scheduler/triggers/webhook.py` | `WebhookTrigger` — HTTP webhook receiver |
| `app/scheduler/triggers/rss.py` | `RSSTrigger` — RSS feed monitor |
| `app/scheduler/triggers/email.py` | `EmailTrigger` — email instruction ingestion |
| `app/scheduler/triggers/file.py` | `FileTrigger` — file system watcher |
| `app/db/models/schedule.py` | `Schedule`, `ScheduleRun` models |
| `app/schemas/schedule.py` | `ScheduleConfig`, `ScheduleStatus` |
| `app/api/routes/schedules.py` | CRUD API for schedules |

#### Implementation Details

```python
# app/scheduler/scheduler.py

@dataclass
class TaskScheduler:
    """Manages scheduled task triggers."""
    
    session_factory: async_sessionmaker
    task_service: TaskService
    triggers: dict[str, Trigger]
    
    async def start(self):
        """Load all active schedules and start trigger loops."""
        async with self.session_factory() as session:
            schedules = await self._load_active_schedules(session)
        
        tasks = [self._run_trigger_loop(s) for s in schedules]
        await asyncio.gather(*tasks)
    
    async def _run_trigger_loop(self, schedule: Schedule):
        """Poll a trigger; when it fires, create a task."""
        trigger = self.triggers[schedule.trigger_type]
        while True:
            event = await trigger.poll(schedule.config)
            if event is not None:
                await self._create_task_from_event(schedule, event)
            await asyncio.sleep(schedule.poll_interval_seconds)
    
    async def _create_task_from_event(self, schedule: Schedule, event: TriggerEvent):
        """Create a task from a trigger event."""
        async with self.session_factory() as session:
            task_service = TaskService(session)
            task = await task_service.create_task(
                instruction=event.instruction,
                metadata={
                    "trigger_id": schedule.id,
                    "trigger_type": schedule.trigger_type,
                    "event_data": event.data,
                },
            )
            # Start orchestrator in background
            asyncio.create_task(self._run_task(task.id, session))
```

```python
# app/scheduler/triggers/cron.py

class CronTrigger:
    """Fire tasks on a cron schedule."""
    
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
    
    async def poll(self, config: dict) -> TriggerEvent | None:
        """Check if the cron schedule has fired since last poll."""
        # Uses APScheduler or a simple cron parser
        ...

# app/scheduler/triggers/rss.py

class RSSTrigger:
    """Monitor RSS feeds for new entries matching keywords."""
    
    async def poll(self, config: dict) -> TriggerEvent | None:
        feed = await self._fetch_feed(config["feed_url"])
        new_entries = self._filter_new(feed, config.get("keywords", []))
        if new_entries:
            return TriggerEvent(
                instruction=config["instruction_template"].format(
                    entries=new_entries
                ),
                data={"entries": [e.link for e in new_entries]},
            )
        return None
```

#### Database Schema

```sql
-- app/db/models/schedule.py
class Schedule(Base):
    __tablename__ = "schedules"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    trigger_type: Mapped[str] = mapped_column(String(50))  # cron, webhook, rss, email, file
    config: Mapped[dict] = mapped_column(JSONB)  # trigger-specific config
    instruction_template: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    poll_interval_seconds: Mapped[int] = mapped_column(default=60)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now())

class ScheduleRun(Base):
    __tablename__ = "schedule_runs"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.id"))
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"))
    triggered_at: Mapped[datetime] = mapped_column(default=func.now())
    event_data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))  # success, failed, skipped
```

#### API Endpoints

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

#### Testing

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_scheduler.py` | Trigger loop, task creation |
| `tests/unit/test_cron_trigger.py` | Cron expression parsing |
| `tests/unit/test_rss_trigger.py` | Feed parsing, keyword filtering |
| `tests/integration/test_schedule_flow.py` | Schedule → trigger → task → completion |

#### Effort Estimate: **3–4 weeks**

---

### 3.4 Draft Review UI

**Problem:** Approvals are raw JSON via API. Humans need a visual interface
to review drafts before approving.

**Solution:** A simple web UI for viewing, editing, and approving drafts.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/api/routes/dashboard.py` | Dashboard API endpoints |
| `app/api/routes/drafts.py` | Draft CRUD + approval endpoints |
| `frontend/` | Simple web UI (or serve via FastAPI templates) |
| `frontend/drafts.html` | Draft review page |
| `frontend/approvals.html` | Approval queue page |
| `frontend/task-detail.html` | Task execution detail page |

#### API Endpoints

```
GET    /api/v1/drafts                  — List drafts pending review
GET    /api/v1/drafts/{id}             — Get draft with full context
PUT    /api/v1/drafts/{id}             — Edit draft content
POST   /api/v1/drafts/{id}/approve     — Approve draft
POST   /api/v1/drafts/{id}/reject      — Reject draft with reason
GET    /api/v1/dashboard/tasks         — Active tasks with status
GET    /api/v1/dashboard/approvals     — Pending approvals queue
```

#### Implementation Notes

- Serve via FastAPI with Jinja2 templates or a simple React/Vue SPA
- Show draft content side-by-side with research sources
- One-click approve/reject with optional feedback
- Real-time updates via WebSocket or SSE for task status

#### Effort Estimate: **2–3 weeks**

---

## 4. Tier 2 — Self-Improving

**Goal:** The system learns from its outcomes and improves over time without
explicit reprogramming.

---

### 4.1 Feedback Loop / RLHF

**Problem:** The system doesn't learn from approval/rejection patterns or
content performance metrics.

**Solution:** Track every human decision and content outcome, feed back into
model prompts and routing.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/feedback/__init__.py` | Package init |
| `app/feedback/collector.py` | `FeedbackCollector` — record decisions |
| `app/feedback/analyzer.py` | `FeedbackAnalyzer` — pattern detection |
| `app/feedback/prompt_updater.py` | `PromptUpdater` — adjust system prompts |
| `app/feedback/routing_optimizer.py` | `RoutingOptimizer` — optimize model selection |
| `app/db/models/feedback.py` | `FeedbackEvent`, `LearningRecord` models |
| `app/schemas/feedback.py` | `FeedbackEvent`, `LearningPattern` |

#### Implementation Details

```python
# app/feedback/collector.py

@dataclass
class FeedbackCollector:
    """Record human decisions for learning."""
    
    async def record_approval(self, task_id: uuid.UUID, step: PlanStep, approved: bool):
        """Record whether a human approved or rejected a step."""
        event = FeedbackEvent(
            task_id=task_id,
            step_name=step.name,
            agent=step.agent,
            action_type="approval",
            decision="approved" if approved else "rejected",
            step_description=step.description,
            recorded_at=datetime.utcnow(),
        )
        await self._persist(event)
    
    async def record_content_performance(self, post_id: str, metrics: dict):
        """Record engagement metrics for published content."""
        event = FeedbackEvent(
            post_id=post_id,
            action_type="performance",
            metrics=metrics,  # likes, shares, clicks, comments
            recorded_at=datetime.utcnow(),
        )
        await self._persist(event)
    
    async def record_revision(self, task_id: uuid.UUID, original: str, edited: str):
        """Record when a human edits a draft before approving."""
        event = FeedbackEvent(
            task_id=task_id,
            action_type="revision",
            original_content=original,
            edited_content=edited,
            recorded_at=datetime.utcnow(),
        )
        await self._persist(event)
```

```python
# app/feedback/analyzer.py

@dataclass
class FeedbackAnalyzer:
    """Detect patterns in human feedback."""
    
    async def analyze_approval_patterns(self, lookback_days: int = 30) -> list[LearningPattern]:
        """Find what types of content/approaches get approved vs rejected."""
        events = await self._load_events(lookback_days)
        
        patterns = []
        # Pattern: "Technical posts with code examples get approved 90% of the time"
        approval_by_type = self._group_by_approval_rate(events, key="content_type")
        for content_type, rate in approval_by_type.items():
            if rate > 0.8 or rate < 0.3:
                patterns.append(LearningPattern(
                    pattern_type="approval_preference",
                    content_type=content_type,
                    approval_rate=rate,
                    confidence=self._calc_confidence(events, content_type),
                ))
        
        # Pattern: "Long-form posts get more engagement"
        performance_by_format = self._group_by_performance(events, key="format")
        ...
        
        return patterns
    
    async def analyze_revision_patterns(self, lookback_days: int = 30) -> list[LearningPattern]:
        """Find what humans typically change in drafts."""
        revisions = await self._load_revisions(lookback_days)
        
        patterns = []
        # Pattern: "Humans always shorten my drafts by 30%"
        avg_length_change = self._avg_length_change(revisions)
        if abs(avg_length_change) > 0.2:
            patterns.append(LearningPattern(
                pattern_type="length_preference",
                avg_change_pct=avg_length_change,
            ))
        
        # Pattern: "Humans remove emojis from professional posts"
        emoji_removal_rate = self._emoji_removal_rate(revisions)
        ...
        
        return patterns
```

```python
# app/feedback/prompt_updater.py

@dataclass
class PromptUpdater:
    """Adjust system prompts based on learned patterns."""
    
    async def update_content_prompt(
        self,
        base_prompt: str,
        patterns: list[LearningPattern],
    ) -> str:
        """Inject learned preferences into the content generation prompt."""
        additions = []
        
        for p in patterns:
            if p.pattern_type == "approval_preference" and p.approval_rate > 0.8:
                additions.append(
                    f"Users prefer {p.content_type} content. Prioritize this format."
                )
            if p.pattern_type == "length_preference":
                if p.avg_change_pct < -0.2:
                    additions.append(
                        "Users consistently shorten drafts. Write more concisely."
                    )
                elif p.avg_change_pct > 0.2:
                    additions.append(
                        "Users consistently expand drafts. Write more detail."
                    )
        
        if additions:
            return base_prompt + "\n\nLearned preferences:\n" + "\n".join(
                f"- {a}" for a in additions
            )
        return base_prompt
```

#### Testing

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_feedback_collector.py` | Event recording, persistence |
| `tests/unit/test_feedback_analyzer.py` | Pattern detection with synthetic data |
| `tests/unit/test_prompt_updater.py` | Prompt modification logic |
| `tests/integration/test_feedback_loop.py` | Approval → analysis → prompt update flow |

#### Effort Estimate: **3–4 weeks**

---

### 4.2 Self-Healing Browser

**Problem:** Browser tasks fail silently when pages change, elements move,
or CAPTCHAs appear. Currently requires manual intervention.

**Solution:** Automatic recovery strategies with fallbacks.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/browser/recovery.py` | `BrowserRecovery` — failure detection + recovery |
| `app/browser/strategies.py` | `RetryStrategy`, `SelectorFallback`, `CAPTCHADetector` |
| `app/browser/health.py` | `BrowserHealthMonitor` — session health tracking |

#### Implementation Details

```python
# app/browser/recovery.py

@dataclass
class BrowserRecovery:
    """Detect and recover from browser failures."""
    
    strategies: list[RecoveryStrategy]
    
    async def recover(
        self,
        error: BrowserError,
        session: BrowserSession,
        original_action: BrowserAction,
    ) -> RecoveryResult:
        """Try recovery strategies in order until one succeeds."""
        for strategy in self.strategies:
            if strategy.can_handle(error):
                result = await strategy.recover(error, session, original_action)
                if result.success:
                    return result
        
        return RecoveryResult(
            success=False,
            error="All recovery strategies exhausted",
            attempts=[s.name for s in self.strategies if s.can_handle(error)],
        )

# app/browser/strategies.py

class SelectorFallback(RecoveryStrategy):
    """When an element can't be found, try alternative selectors."""
    
    name = "selector_fallback"
    
    async def recover(self, error, session, action):
        # Try ARIA role + accessible name
        alt_selector = await self._find_by_aria(action.target_element)
        if alt_selector:
            return await session.click(alt_selector)
        
        # Try text content
        alt_selector = await self._find_by_text(action.target_text)
        if alt_selector:
            return await session.click(alt_selector)
        
        # Try stable test attributes
        alt_selector = await self._find_by_test_id(action.test_id)
        ...

class CAPTCHADetector(RecoveryStrategy):
    """Detect CAPTCHAs and escalate to human."""
    
    name = "captcha_detection"
    
    async def recover(self, error, session, action):
        if await self._detect_captcha(session.page):
            return RecoveryResult(
                success=False,
                error="CAPTCHA detected — requires human intervention",
                escalate=True,
            )

class PageCrashRecovery(RecoveryStrategy):
    """Recover from crashed/unresponsive pages."""
    
    name = "page_crash"
    
    async def recover(self, error, session, action):
        await session.close_page()
        new_page = await session.new_page()
        await new_page.goto(action.url)
        # Re-run the original action on the new page
        return await self._rerun_action(action, new_page)
```

#### Testing

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_browser_recovery.py` | Strategy selection, fallback chain |
| `tests/unit/test_selector_fallback.py` | Alternative selector discovery |
| `tests/unit/test_captcha_detector.py` | CAPTCHA detection with fixtures |
| `tests/browser/test_recovery_flow.py` | Recovery with controlled test pages |

#### Effort Estimate: **2–3 weeks**

---

### 4.3 Research Quality Scoring

**Problem:** The system doesn't know which sources produce high-quality output.
All research sources are treated equally.

**Solution:** Track source → content → engagement pipeline. Learn which
sources and approaches produce the best results.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/research/quality.py` | `ResearchQualityScorer` — score source quality |
| `app/research/source_ranker.py` | `SourceRanker` — rank sources by historical performance |
| `app/db/models/research_quality.py` | `SourceQuality`, `ResearchOutcome` |

#### Implementation Details

```python
# app/research/quality.py

@dataclass
class ResearchQualityScorer:
    """Score research sources based on historical outcomes."""
    
    async def score_source(self, source: ResearchSource) -> SourceScore:
        """Score a source based on past performance."""
        historical = await self._load_source_history(source.url)
        
        if not historical:
            return SourceScore(value=0.5, confidence=0.0, reason="No history")
        
        # Metrics: approval rate of content using this source,
        #          engagement of published content, fact-check pass rate
        approval_rate = self._calc_approval_rate(historical)
        engagement_rate = self._calc_engagement_rate(historical)
        fact_check_rate = self._calc_fact_check_rate(historical)
        
        score = (
            0.4 * approval_rate +
            0.4 * engagement_rate +
            0.2 * fact_check_rate
        )
        
        return SourceScore(
            value=score,
            confidence=min(len(historical) / 10, 1.0),
            reason=f"Based on {len(historical)} historical uses",
        )
    
    async def get_top_sources(self, query: str, limit: int = 10) -> list[ResearchSource]:
        """Rank available sources by quality for a given query."""
        candidates = await self._search_sources(query)
        scored = []
        for source in candidates:
            score = await self.score_source(source)
            scored.append((source, score))
        
        scored.sort(key=lambda x: x[1].value, reverse=True)
        return [s for s, _ in scored[:limit]]
```

#### Effort Estimate: **2–3 weeks**

---

### 4.4 Dynamic Model Routing

**Problem:** Model routing is static — the same model class is used for
similar tasks regardless of historical cost/success tradeoffs.

**Solution:** Use historical performance data to dynamically choose models.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/llm/adaptive_router.py` | `AdaptiveModelRouter` — learns optimal model per task type |
| `app/llm/performance_tracker.py` | `PerformanceTracker` — track model outcomes |

#### Implementation Details

```python
# app/llm/adaptive_router.py

@dataclass
class AdaptiveModelRouter:
    """Extends ModelRouter with learning from outcomes."""
    
    base_router: ModelRouter
    tracker: PerformanceTracker
    
    def route(self, criteria: RoutingCriteria) -> ModelSelection:
        # Get base recommendation
        base = self.base_router.route(criteria)
        
        # Look up historical performance for this task type
        history = self.tracker.get_history(criteria.task_type)
        
        if history and history.sample_size >= 10:
            # Find the cheapest model that meets quality threshold
            for model_class in [ModelClass.FAST, ModelClass.TOOL_CALLING, ModelClass.REASONING]:
                perf = history.get_performance(model_class)
                if perf and perf.success_rate >= 0.9 and perf.avg_cost < base_cost * 0.5:
                    return ModelSelection(
                        model_class=model_class,
                        provider=base.provider,
                        model_name=self.base_router._model_name_for(model_class),
                        reasoning=f"Adaptive routing: {model_class.value} has {perf.success_rate:.0%} success rate at lower cost",
                    )
        
        return base  # Fall back to static routing
```

#### Effort Estimate: **2 weeks**

---

## 5. Tier 3 — Fully Autonomous

**Goal:** The system runs end-to-end operations with minimal human involvement.
Humans set goals and review reports; the system handles everything in between.

---

### 5.1 Autonomous Social Media Manager

**Problem:** Each social post requires manual triggering. The system can't
operate a content calendar autonomously.

**Solution:** A goal-driven social media manager that plans, creates, and
publishes content on a schedule with auto-verification.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/autonomy/__init__.py` | Package init |
| `app/autonomy/social_manager.py` | `AutonomousSocialManager` — full loop |
| `app/autonomy/content_calendar.py` | `ContentCalendar` — schedule + topics |
| `app/autonomy/topic_monitor.py` | `TopicMonitor` — trending topic detection |
| `app/autonomy/performance_reporter.py` | `PerformanceReporter` — weekly summaries |
| `app/db/models/calendar.py` | `CalendarEntry`, `ContentSlot` |

#### Implementation Details

```python
# app/autonomy/social_manager.py

@dataclass
class AutonomousSocialManager:
    """Full autonomous social media operations loop."""
    
    topic_monitor: TopicMonitor
    calendar: ContentCalendar
    research_agent: CompiledGraph
    content_agent: CompiledGraph
    fact_check_agent: CompiledGraph
    social_agent: CompiledGraph
    verification_pipeline: VerificationPipeline
    feedback: FeedbackCollector
    reporter: PerformanceReporter
    
    async def run_weekly_cycle(self):
        """Execute one full weekly content cycle."""
        # 1. Monitor trending topics
        topics = await self.topic_monitor.discover(
            keywords=self.calendar.focus_areas,
            min_relevance=0.7,
        )
        
        # 2. Plan content for the week
        content_plan = await self.calendar.plan_week(
            topics=topics,
            platform_budget=self._get_platform_budget(),
        )
        
        # 3. For each content slot
        for slot in content_plan.slots:
            try:
                await self._execute_content_pipeline(slot)
            except Exception as exc:
                logger.warning("content_pipeline.failed", slot=slot.id, error=str(exc))
                continue
        
        # 4. Generate performance report
        report = await self.reporter.generate_weekly_report()
        await self._deliver_report(report)
    
    async def _execute_content_pipeline(self, slot: ContentSlot):
        """Research → Draft → Fact Check → Publish → Verify for one slot."""
        # Research
        research_result = await self.research_agent.ainvoke(
            {"messages": [HumanMessage(content=f"Research: {slot.topic}")]},
        )
        
        # Draft
        draft_result = await self.content_agent.ainvoke(
            {"messages": [HumanMessage(content=f"Create {slot.platform} post about: {research_result}")]},
        )
        
        # Fact check
        fact_result = await self.fact_check_agent.ainvoke(
            {"messages": [HumanMessage(content=f"Verify claims: {draft_result}")]},
        )
        
        # Publish (auto-approve if confidence is high enough)
        publish_result = await self.social_agent.ainvoke(
            {"messages": [HumanMessage(content=f"Publish: {draft_result}")]},
        )
        
        # Verify
        verification = await self.verification_pipeline.verify(publish_result)
        
        # Record feedback
        await self.feedback.record_content_performance(
            publish_result.post_id,
            {"published_at": datetime.utcnow(), "verification": verification.verified},
        )
```

#### Effort Estimate: **4–6 weeks**

---

### 5.2 Multi-Platform Content Repurposing

**Problem:** Content is created per-platform. One research piece requires
separate drafting for X, LinkedIn, newsletter, etc.

**Solution:** An intelligent repurposing engine that adapts one source piece
into multiple platform-native formats.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/content/repurposer.py` | `ContentRepurposer` — adapt content per platform |
| `app/content/platform_formats.py` | Platform-specific format rules |
| `app/schemas/repurposing.py` | `RepurposingRequest`, `PlatformContent` |

#### Implementation Details

```python
# app/content/repurposer.py

@dataclass
class ContentRepurposer:
    """Adapt one research piece into multiple platform-native formats."""
    
    router: ModelRouter
    platform_formats: dict[str, PlatformFormat]
    
    async def repurpose(
        self,
        source_content: str,
        platforms: list[str],
        tone: str = "professional",
    ) -> dict[str, PlatformContent]:
        """Create platform-native versions of the source content."""
        results = {}
        
        for platform in platforms:
            fmt = self.platform_formats[platform]
            
            model = self.router.route(RoutingCriteria(
                task_complexity=TaskComplexity.MODERATE,
                requires_reasoning=True,
            ))
            
            prompt = fmt.build_repurpose_prompt(source_content, tone)
            result = await model.ainvoke(prompt)
            
            # Validate against platform constraints
            validated = fmt.validate(result)
            
            results[platform] = PlatformContent(
                platform=platform,
                content=validated.text,
                metadata=validated.metadata,
                char_count=len(validated.text),
                within_limits=validated.within_limits,
            )
        
        return results

# app/content/platform_formats.py

class XFormat(PlatformFormat):
    """X/Twitter format rules."""
    
    max_chars = 280
    supports_threads = True
    supports_media = True
    
    def build_repurpose_prompt(self, source: str, tone: str) -> str:
        return f"""Adapt this content for X/Twitter:
        
{source}

Rules:
- Max 280 characters per post
- If longer, create a thread (number posts 1/N, 2/N, etc.)
- {tone} tone
- Include 2-3 relevant hashtags
- End with a call to action or question"""

class LinkedInFormat(PlatformFormat):
    """LinkedIn format rules."""
    
    max_chars = 3000
    supports_threads = False
    supports_media = True
    
    def build_repurpose_prompt(self, source: str, tone: str) -> str:
        return f"""Adapt this content for LinkedIn:

{source}

Rules:
- Max 3000 characters
- Professional {tone} tone
- Start with a hook (first 2 lines visible before "see more")
- Use line breaks for readability
- Include 3-5 relevant hashtags
- Tag relevant people/companies if applicable"""

class NewsletterFormat(PlatformFormat):
    """Email newsletter format rules."""
    
    max_chars = 50000
    supports_sections = True
    
    def build_repurpose_prompt(self, source: str, tone: str) -> str:
        return f"""Expand this content into a newsletter format:

{source}

Rules:
- Subject line (max 60 chars)
- Preview text (max 100 chars)
- Opening hook (2-3 sentences)
- 3-5 main sections with headers
- Key takeaways section
- Call to action
- {tone} tone throughout"""
```

#### Effort Estimate: **3–4 weeks**

---

### 5.3 Competitive Intelligence Agent

**Problem:** No continuous monitoring of competitors or industry changes.

**Solution:** An agent that monitors competitor websites, social accounts,
and news, then auto-generates reports when significant changes are detected.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/autonomy/competitor_monitor.py` | `CompetitorMonitor` — track competitor activity |
| `app/autonomy/intel_reporter.py` | `IntelReporter` — generate intelligence reports |
| `app/db/models/intel.py` | `CompetitorProfile`, `IntelSnapshot`, `IntelReport` |

#### Implementation Details

```python
# app/autonomy/competitor_monitor.py

@dataclass
class CompetitorMonitor:
    """Continuously monitor competitor activity."""
    
    browser: BrowserSessionManager
    research_agent: CompiledGraph
    change_detector: ChangeDetector
    
    async def monitor_competitor(self, profile: CompetitorProfile):
        """Check a competitor for changes."""
        snapshots = []
        
        # Website changes
        if profile.website_url:
            current = await self._snapshot_website(profile.website_url)
            previous = await self._get_last_snapshot(profile.id, "website")
            if self.change_detector.has_significant_change(previous, current):
                snapshots.append(current)
        
        # Social media changes
        for platform in profile.social_urls:
            current = await self._snapshot_social(platform.url)
            previous = await self._get_last_snapshot(profile.id, f"social_{platform.name}")
            if self.change_detector.has_significant_change(previous, current):
                snapshots.append(current)
        
        # News mentions
        news = await self.research_agent.ainvoke(
            {"messages": [HumanMessage(content=f"Find recent news about {profile.name}")]},
        )
        
        if snapshots or news.has_new_results:
            await self._generate_alert(profile, snapshots, news)
    
    async def run_monitoring_cycle(self):
        """Check all competitors."""
        profiles = await self._load_competitor_profiles()
        for profile in profiles:
            await self.monitor_competitor(profile)
```

#### Effort Estimate: **3–4 weeks**

---

### 5.4 Agent-to-Agent Delegation

**Problem:** The orchestrator micromanages every step. Sub-agents can't
autonomously decide to delegate to other agents.

**Solution:** Allow sub-agents to request delegation to other specialized
agents when they encounter tasks outside their scope.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/agents/delegation.py` | `DelegationManager` — handle agent-to-agent handoffs |
| `app/agents/delegation_handler.py` | `DelegationHandler` — tool for agents to request delegation |

#### Implementation Details

```python
# app/agents/delegation_handler.py

class DelegateToAgentTool(BaseTool):
    """Allow an agent to delegate work to another specialized agent."""
    
    name = "delegate_to_agent"
    description = "Delegate a subtask to another specialized agent"
    risk_level = RiskLevel.MEDIUM
    
    class Input(BaseModel):
        target_agent: str  # research, browser, content, etc.
        instruction: str
        context: str
    
    async def run(self, input: Input, context: ExecutionContext) -> DelegateResult:
        """Request delegation to another agent."""
        # This tool doesn't execute directly — it returns a signal
        # to the orchestrator to invoke the target agent
        return DelegateResult(
            delegated=True,
            target_agent=input.target_agent,
            instruction=input.instruction,
            context=input.context,
        )

# In orchestrator.py, handle delegation results:
async def _invoke_subgraph(self, ...):
    result = await graph.ainvoke(...)
    
    # Check for delegation requests in the output
    messages = result.get("messages", [])
    for msg in messages:
        if hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                if tc["name"] == "delegate_to_agent":
                    # Invoke the target agent instead
                    target_step = PlanStep(
                        name=f"delegated_{tc['args']['target_agent']}",
                        agent=tc["args"]["target_agent"],
                        description=tc["args"]["instruction"],
                    )
                    return await self._invoke_subgraph(
                        task_id=task_id,
                        step=target_step,
                        approved_actions=approved_actions,
                    )
    
    return result
```

#### Effort Estimate: **2–3 weeks**

---

### 5.5 Memory & Context Persistence

**Problem:** The system doesn't remember previous tasks. Each task starts
from scratch.

**Solution:** Cross-task memory via vector store for knowledge recall.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/memory/__init__.py` | Package init |
| `app/memory/store.py` | `MemoryStore` — vector store abstraction |
| `app/memory/retriever.py` | `MemoryRetriever` — recall relevant memories |
| `app/memory/writer.py` | `MemoryWriter` — store new memories |
| `app/memory/embeddings.py` | `EmbeddingProvider` — text embeddings |

#### Implementation Details

```python
# app/memory/store.py

@dataclass
class MemoryStore:
    """Cross-task memory with semantic search."""
    
    retriever: MemoryRetriever
    writer: MemoryWriter
    
    async def recall(self, query: str, limit: int = 5) -> list[Memory]:
        """Recall memories relevant to a query."""
        return await self.retriever.search(query, limit=limit)
    
    async def remember(self, content: str, metadata: dict):
        """Store a new memory."""
        await self.writer.store(content, metadata)

# app/memory/retriever.py

class MemoryRetriever:
    """Semantic search over stored memories."""
    
    async def search(self, query: str, limit: int = 5) -> list[Memory]:
        embedding = await self.embeddings.embed(query)
        results = await self.vector_db.similarity_search(embedding, limit=limit)
        return [Memory.from_result(r) for r in results]

# In research agent, use memory:
async def _run_research_with_memory(self, query: str):
    # Recall relevant past research
    past_memories = await self.memory.recall(
        f"Previous research on: {query}",
        limit=3,
    )
    
    context = ""
    if past_memories:
        context = "\n\nPrevious related findings:\n" + "\n".join(
            f"- {m.content}" for m in past_memories
        )
    
    # Include memory context in research instruction
    instruction = f"Research: {query}{context}\n\nBuild on previous findings where relevant."
    ...
```

#### Effort Estimate: **3–4 weeks**

---

### 5.6 Cost-Aware Autonomous Operation

**Problem:** No budget constraints. The system uses whatever model is cheapest
per task, but doesn't optimize for overall cost.

**Solution:** Monthly/daily budget limits with automatic model downgrade
when budget is tight.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/cost/__init__.py` | Package init |
| `app/cost/budget.py` | `BudgetManager` — track and enforce budgets |
| `app/cost/optimizer.py` | `CostOptimizer` — optimize model selection |
| `app/db/models/cost.py` | `CostRecord`, `BudgetConfig` |

#### Implementation Details

```python
# app/cost/budget.py

@dataclass
class BudgetManager:
    """Track and enforce cost budgets."""
    
    async def get_remaining_budget(
        self,
        scope: str,  # "daily", "monthly", "task"
        user_id: uuid.UUID | None = None,
    ) -> BudgetStatus:
        """Check remaining budget for a scope."""
        spent = await self._get_spent(scope, user_id)
        limit = await self._get_limit(scope, user_id)
        
        return BudgetStatus(
            spent=spent,
            limit=limit,
            remaining=limit - spent,
            pct_used=spent / limit if limit > 0 else 0,
        )
    
    async def enforce_budget(self, estimated_cost: float) -> BudgetDecision:
        """Decide if an action is within budget."""
        daily = await self.get_remaining_budget("daily")
        monthly = await self.get_remaining_budget("monthly")
        
        if estimated_cost > daily.remaining or estimated_cost > monthly.remaining:
            return BudgetDecision(
                allowed=False,
                reason=f"Estimated cost ${estimated_cost:.2f} exceeds remaining budget",
                suggestion="Downgrade to cheaper model or skip this task",
            )
        
        return BudgetDecision(allowed=True)

# app/cost/optimizer.py

@dataclass
class CostOptimizer:
    """Optimize model selection based on budget constraints."""
    
    base_router: ModelRouter
    budget: BudgetManager
    
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
                    reasoning=f"Budget optimization: downgrading from REASONING to TOOL_CALLING",
                )
        
        return base
```

#### Effort Estimate: **2–3 weeks**

---

## 6. Tier 4 — Platform / Ecosystem

**Goal:** Make Agent Operator a reusable platform consumed by other systems.

---

### 6.1 Skill API

**Problem:** Skills are only usable within Agent Operator. External systems
(Claude Code, Codex) can't consume them.

**Solution:** Expose each skill as a REST endpoint with standardized I/O.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/api/routes/skills.py` | Skill API endpoints |
| `app/skills/registry.py` | `SkillRegistry` — discover and manage skills |
| `app/schemas/skill.py` | `SkillDefinition`, `SkillRequest`, `SkillResponse` |

#### API Endpoints

```
GET    /api/v1/skills                    — List available skills
GET    /api/v1/skills/{name}             — Get skill definition (SKILL.md content)
POST   /api/v1/skills/{name}/execute     — Execute a skill with input
GET    /api/v1/skills/{name}/status      — Get skill execution status
GET    /api/v1/skills/{name}/schema      — Get input/output JSON schema
```

#### Implementation Details

```python
# app/api/routes/skills.py

router = APIRouter(prefix="/skills", tags=["skills"])

@router.get("/")
async def list_skills(registry: SkillRegistry = Depends(get_skill_registry)):
    """List all available skills."""
    skills = await registry.list_skills()
    return [SkillDefinition(
        name=s.name,
        description=s.description,
        input_schema=s.input_schema,
        output_schema=s.output_schema,
        required_tools=s.required_tools,
    ) for s in skills]

@router.post("/{name}/execute")
async def execute_skill(
    name: str,
    request: SkillRequest,
    registry: SkillRegistry = Depends(get_skill_registry),
    session: AsyncSession = Depends(get_session),
):
    """Execute a skill and return the result."""
    skill = await registry.get_skill(name)
    
    # Create a task from the skill request
    task_service = TaskService(session)
    task = await task_service.create_task(
        instruction=skill.build_instruction(request),
        metadata={"skill_name": name, "skill_input": request.model_dump()},
    )
    
    # Run orchestrator
    orchestrator = build_orchestrator(session)
    await orchestrator.run(str(task.id))
    
    # Return result
    task = await task_service.get_task(task.id)
    return SkillResponse(
        task_id=str(task.id),
        status=task.state,
        result=task.result,
    )
```

#### Effort Estimate: **2–3 weeks**

---

### 6.2 Plugin System

**Problem:** Adding new tools or platform integrations requires modifying
core agent code.

**Solution:** A plugin system where new capabilities are discovered and
registered automatically.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/plugins/__init__.py` | Package init |
| `app/plugins/loader.py` | `PluginLoader` — discover and load plugins |
| `app/plugins/base.py` | `Plugin` — base class for plugins |
| `app/plugins/registry.py` | `PluginRegistry` — manage plugin lifecycle |

#### Implementation Details

```python
# app/plugins/base.py

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

# app/plugins/loader.py

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
            logger.info("plugin.loaded", name=plugin.name, version=plugin.version)
```

#### Effort Estimate: **2–3 weeks**

---

### 6.3 Multi-Agent Orchestration Mode

**Problem:** One orchestrator handles all task types. This doesn't scale
for high-throughput deployments.

**Solution:** Multiple orchestrators running in parallel, each specialized
for different task types.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/orchestration/cluster.py` | `OrchestratorCluster` — manage multiple orchestrators |
| `app/orchestration/load_balancer.py` | `LoadBalancer` — distribute tasks |
| `app/orchestration/worker_pool.py` | `WorkerPool` — manage worker processes |

#### Implementation Details

```python
# app/orchestration/cluster.py

@dataclass
class OrchestratorCluster:
    """Manage multiple specialized orchestrators."""
    
    orchestrators: dict[str, Orchestrator]  # task_type -> orchestrator
    load_balancer: LoadBalancer
    
    async def submit_task(self, task: Task) -> str:
        """Route a task to the appropriate orchestrator."""
        task_type = self._classify_task(task)
        orchestrator = self.orchestrators.get(task_type)
        
        if orchestrator is None:
            orchestrator = self.orchestrators["default"]
        
        # Add to the orchestrator's queue
        await self.load_balancer.enqueue(task_type, task)
        return str(task.id)
    
    async def start(self):
        """Start all orchestrator worker loops."""
        tasks = []
        for name, orch in self.orchestrators.items():
            for _ in range(orch.config.worker_count):
                tasks.append(self._worker_loop(name, orch))
        await asyncio.gather(*tasks)

# app/orchestration/load_balancer.py

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

#### Effort Estimate: **3–4 weeks**

---

### 6.4 Audit & Compliance API

**Problem:** No way to query the full history of what the system did.

**Solution:** Every action, approval, model call, and verification is
queryable with full provenance.

#### Files to Create

| File | Purpose |
|------|---------|
| `app/api/routes/audit.py` | Audit API endpoints |
| `app/audit/query.py` | `AuditQuery` — flexible audit log querying |
| `app/audit/reporter.py` | `ComplianceReporter` — generate compliance reports |

#### API Endpoints

```
GET    /api/v1/audit/actions            — Query all actions
GET    /api/v1/audit/actions/{id}       — Get action detail with provenance
GET    /api/v1/audit/tasks/{id}/timeline — Full task execution timeline
GET    /api/v1/audit/models             — Model usage statistics
GET    /api/v1/audit/approvals          — Approval history
GET    /api/v1/audit/compliance/report  — Generate compliance report
GET    /api/v1/audit/export             — Export audit log (CSV/JSON)
```

#### Effort Estimate: **2–3 weeks**

---

## 7. Cross-Cutting Concerns

### 7.1 Database Migrations

Each tier requires new database tables. Create Alembic migrations for:

**Tier 1:**
- `schedules`, `schedule_runs` — scheduled triggers
- `verification_steps` — verification pipeline results
- `confidence_scores` — auto-approval scoring

**Tier 2:**
- `feedback_events` — human decisions and outcomes
- `learning_records` — detected patterns
- `source_quality` — research source performance
- `model_performance` — model routing history

**Tier 3:**
- `competitor_profiles`, `intel_snapshots` — competitive intelligence
- `content_calendars`, `content_slots` — content scheduling
- `memories` — vector store metadata

**Tier 4:**
- `plugins` — installed plugins
- `skill_executions` — skill API usage
- `audit_logs` — comprehensive audit trail

### 7.2 Observability

Add structured logging for every new subsystem:

```python
# Pattern for all new subsystems:
logger.info(
    "subsystem.action",
    task_id=str(task_id),
    action="specific_action",
    result="success/failed",
    duration_ms=duration,
    metadata={...},
)
```

### 7.3 Testing Strategy

| Test Level | Scope | When |
|------------|-------|------|
| Unit | Individual functions, policies, scorers | Every PR |
| Integration | Subsystem interactions (e.g., scheduler → orchestrator) | Every PR |
| E2E | Full pipeline with mocked external services | Weekly |
| Load | Concurrent task execution, worker scaling | Pre-release |

### 7.4 Security Considerations

- **Plugin sandboxing:** Plugins run in the same process but with restricted tool access
- **Schedule authentication:** Webhook triggers require token authentication
- **Memory isolation:** Cross-task memory is per-tenant, not global
- **Audit immutability:** Audit logs are append-only, never modified
- **Budget enforcement:** Budget checks happen in application code, not just config

---

## 8. Implementation Timeline

### Phase Completion (from TODO.md)

| Phase | Status | Estimated |
|-------|--------|-----------|
| Phase 1 — Foundation | ✅ Done | — |
| Phase 2 — Agent Core | ✅ Done | — |
| Phase 3 — Browser | 🔲 Not started | 3–4 weeks |
| Phase 4 — Research | 🔲 Not started | 3–4 weeks |
| Phase 5 — Content | 🔲 Not started | 2–3 weeks |
| Phase 6 — Social | 🔲 Not started | 3–4 weeks |
| Phase 7 — Safety | 🔲 Not started | 2–3 weeks |
| Phase 8 — Production | 🔲 Not started | 3–4 weeks |

**Total for Phases 3–8:** ~16–22 weeks

### Tier 1 Implementation (after Phases 3–8)

| Feature | Dependencies | Effort |
|---------|-------------|--------|
| Confidence-Based Approval | Phase 7 (Safety) | 2–3 weeks |
| Self-Verification | Phase 6 (Social) | 2–3 weeks |
| Scheduled Triggers | Phase 8 (Workers) | 3–4 weeks |
| Draft Review UI | Phase 5 (Content) | 2–3 weeks |

**Total for Tier 1:** ~9–13 weeks (some parallelizable)

### Tier 2 Implementation (after Tier 1)

| Feature | Dependencies | Effort |
|---------|-------------|--------|
| Feedback Loop | Tier 1 (Confidence) | 3–4 weeks |
| Self-Healing Browser | Phase 3 (Browser) | 2–3 weeks |
| Research Quality Scoring | Phase 4 (Research) | 2–3 weeks |
| Dynamic Model Routing | Phase 8 (Observability) | 2 weeks |

**Total for Tier 2:** ~9–12 weeks (some parallelizable)

### Tier 3 Implementation (after Tier 2)

| Feature | Dependencies | Effort |
|---------|-------------|--------|
| Autonomous Social Manager | Tier 1+2 | 4–6 weeks |
| Content Repurposing | Tier 1 (Content) | 3–4 weeks |
| Competitive Intelligence | Tier 1 (Scheduler) | 3–4 weeks |
| Agent-to-Agent Delegation | Core orchestrator | 2–3 weeks |
| Memory & Context | Tier 2 (Feedback) | 3–4 weeks |
| Cost-Aware Operation | Tier 2 (Routing) | 2–3 weeks |

**Total for Tier 3:** ~17–24 weeks (some parallelizable)

### Tier 4 Implementation (after Tier 3)

| Feature | Dependencies | Effort |
|---------|-------------|--------|
| Skill API | Tier 3 (Skills) | 2–3 weeks |
| Plugin System | Core tools | 2–3 weeks |
| Multi-Agent Orchestration | Tier 3 (Scheduler) | 3–4 weeks |
| Audit & Compliance API | All tiers | 2–3 weeks |

**Total for Tier 4:** ~9–13 weeks (some parallelizable)

### Grand Total

| Section | Weeks |
|---------|-------|
| Phases 3–8 (Foundation) | 16–22 |
| Tier 1 (Semi-Autonomous) | 9–13 |
| Tier 2 (Self-Improving) | 9–12 |
| Tier 3 (Fully Autonomous) | 17–24 |
| Tier 4 (Platform) | 9–13 |
| **Total** | **60–84 weeks** |

**With parallelization (2–3 features at once):** ~30–40 weeks

---

## 9. Updated Repository Structure

```
agent-operator/
│
├── app/
│   ├── agents/
│   │   ├── orchestrator.py          # Modified: confidence engine integration
│   │   ├── delegation.py            # NEW: agent-to-agent delegation
│   │   ├── graphs/
│   │   │   ├── research.py
│   │   │   ├── browser.py
│   │   │   ├── content.py
│   │   │   ├── fact_checker.py
│   │   │   ├── social.py
│   │   │   └── verification.py
│   │   └── ...
│   │
│   ├── autonomy/                    # NEW: Tier 3
│   │   ├── __init__.py
│   │   ├── social_manager.py
│   │   ├── content_calendar.py
│   │   ├── topic_monitor.py
│   │   ├── competitor_monitor.py
│   │   ├── intel_reporter.py
│   │   └── performance_reporter.py
│   │
│   ├── confidence/                  # NEW: Tier 1
│   │   ├── __init__.py
│   │   ├── engine.py
│   │   ├── scorer.py
│   │   └── policies.py
│   │
│   ├── cost/                        # NEW: Tier 3
│   │   ├── __init__.py
│   │   ├── budget.py
│   │   └── optimizer.py
│   │
│   ├── feedback/                    # NEW: Tier 2
│   │   ├── __init__.py
│   │   ├── collector.py
│   │   ├── analyzer.py
│   │   ├── prompt_updater.py
│   │   └── routing_optimizer.py
│   │
│   ├── llm/
│   │   ├── adaptive_router.py       # NEW: Tier 2
│   │   ├── performance_tracker.py   # NEW: Tier 2
│   │   └── ...
│   │
│   ├── memory/                      # NEW: Tier 3
│   │   ├── __init__.py
│   │   ├── store.py
│   │   ├── retriever.py
│   │   ├── writer.py
│   │   └── embeddings.py
│   │
│   ├── orchestration/               # NEW: Tier 4
│   │   ├── __init__.py
│   │   ├── cluster.py
│   │   ├── load_balancer.py
│   │   └── worker_pool.py
│   │
│   ├── plugins/                     # NEW: Tier 4
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── loader.py
│   │   └── registry.py
│   │
│   ├── scheduler/                   # NEW: Tier 1
│   │   ├── __init__.py
│   │   ├── scheduler.py
│   │   └── triggers/
│   │       ├── cron.py
│   │       ├── webhook.py
│   │       ├── rss.py
│   │       ├── email.py
│   │       └── file.py
│   │
│   ├── verification/                # NEW: Tier 1
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── checks.py
│   │   └── retry.py
│   │
│   ├── audit/                       # NEW: Tier 4
│   │   ├── __init__.py
│   │   ├── query.py
│   │   └── reporter.py
│   │
│   ├── api/routes/
│   │   ├── skills.py                # NEW: Tier 4
│   │   ├── schedules.py             # NEW: Tier 1
│   │   ├── drafts.py                # NEW: Tier 1
│   │   ├── dashboard.py             # NEW: Tier 1
│   │   └── audit.py                 # NEW: Tier 4
│   │
│   ├── db/models/
│   │   ├── schedule.py              # NEW: Tier 1
│   │   ├── verification_step.py     # NEW: Tier 1
│   │   ├── feedback.py              # NEW: Tier 2
│   │   ├── learning.py              # NEW: Tier 2
│   │   ├── source_quality.py        # NEW: Tier 2
│   │   ├── competitor.py            # NEW: Tier 3
│   │   ├── calendar.py              # NEW: Tier 3
│   │   ├── memory.py                # NEW: Tier 3
│   │   ├── cost.py                  # NEW: Tier 3
│   │   ├── plugin.py                # NEW: Tier 4
│   │   └── audit.py                 # NEW: Tier 4
│   │
│   └── schemas/
│       ├── confidence.py            # NEW: Tier 1
│       ├── verification.py          # NEW: Tier 1
│       ├── schedule.py              # NEW: Tier 1
│       ├── feedback.py              # NEW: Tier 2
│       ├── repurposing.py           # NEW: Tier 3
│       ├── skill.py                 # NEW: Tier 4
│       └── audit.py                 # NEW: Tier 4
│
├── plugins/                         # NEW: Tier 4 — user plugins directory
│   └── example_plugin/
│       ├── plugin.py
│       └── SKILL.md
│
├── frontend/                        # NEW: Tier 1 — draft review UI
│   ├── index.html
│   ├── drafts.html
│   ├── approvals.html
│   └── task-detail.html
│
├── tests/
│   ├── unit/
│   │   ├── test_confidence_*.py
│   │   ├── test_verification_*.py
│   │   ├── test_scheduler_*.py
│   │   ├── test_feedback_*.py
│   │   ├── test_cost_*.py
│   │   ├── test_memory_*.py
│   │   ├── test_plugins_*.py
│   │   └── test_audit_*.py
│   ├── integration/
│   │   ├── test_auto_approval_flow.py
│   │   ├── test_verification_flow.py
│   │   ├── test_schedule_flow.py
│   │   ├── test_feedback_loop.py
│   │   └── test_skill_api.py
│   └── e2e/
│       ├── test_autonomous_social.py
│       └── test_competitor_intel.py
│
└── docs/
    └── autonomy-roadmap.md          # This file
```

---

## Appendix A: Configuration Extensions

Add to `app/config.py`:

```python
class ConfidenceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONFIDENCE_")
    
    auto_approve_threshold: float = 0.85
    never_auto_approve_threshold: float = 0.4
    scoring_model: str = "gpt-4o-mini"

class SchedulerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCHEDULER_")
    
    enabled: bool = False
    poll_interval_seconds: int = 60
    max_concurrent_triggers: int = 10

class BudgetSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BUDGET_")
    
    daily_limit_usd: float = 10.0
    monthly_limit_usd: float = 200.0
    alert_threshold_pct: float = 0.8

class MemorySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MEMORY_")
    
    enabled: bool = False
    vector_store_url: str | None = None
    embedding_model: str = "text-embedding-3-small"
    max_memories: int = 10000

class PluginSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLUGIN_")
    
    enabled: bool = False
    plugin_dir: str = "plugins"
    sandboxed: bool = True
```

## Appendix B: Key Design Decisions

1. **Confidence engine uses FAST model** — scoring is a simple classification task; no need for expensive models.

2. **Verification is synchronous within a task** — verification must complete before the task is marked COMPLETED. Async verification would create false positives.

3. **Scheduler uses PostgreSQL, not Redis** — consistent with the existing "no Redis dependency" principle (PROJECT.md section 6).

4. **Memory store is optional** — if `MEMORY_ENABLED=false`, the system works without it. Memory is an enhancement, not a requirement.

5. **Plugins are in-process** — no separate plugin process. Plugins share the same event loop but have restricted tool access via `ToolExecutionEngine`.

6. **Budget enforcement is soft** — when budget is exceeded, the system downgrades models, not refuses tasks. Hard budget limits are a deployment concern, not an application concern.

7. **Audit logs are append-only** — never modified or deleted. This is a compliance requirement, not a feature.

---

**Document version:** 1.0
**Last updated:** 2026-09-12
**Status:** Ready for review
