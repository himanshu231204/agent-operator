# Tier 2 — Self-Improving: Detailed Implementation Plan

**Date:** 2026-09-12
**Status:** Ready for Implementation
**Depends on:** Tier 1 complete (see Prerequisite Map below)
**Branch:** `feature/tier2-self-improving`

---

## Table of Contents

1. [Prerequisite Dependency Map](#1-prerequisite-dependency-map)
2. [Implementation Order](#2-implementation-order)
3. [Feature 4.1 — Feedback Loop / RLHF](#3-feature-41--feedback-loop--rlhf)
4. [Feature 4.2 — Self-Healing Browser](#4-feature-42--self-healing-browser)
5. [Feature 4.3 — Research Quality Scoring](#5-feature-43--research-quality-scoring)
6. [Feature 4.4 — Dynamic Model Routing](#6-feature-44--dynamic-model-routing)
7. [Migration Strategy](#7-migration-strategy)
8. [Risk Matrix](#8-risk-matrix)
9. [Acceptance Criteria Summary](#9-acceptance-criteria-summary)

---

## 1. Prerequisite Dependency Map

Each Tier 2 feature depends on specific Tier 1 and Phase work being complete.

| Tier 2 Feature | Tier 1 Prerequisites | Phase Prerequisites | Rationale |
|---|---|---|---|
| **4.1 Feedback Loop** | 3.1 Confidence Engine | Phase 5 (Content — draft model) | Needs confidence engine to record auto-approval decisions; needs draft model to track revisions |
| **4.2 Self-Healing Browser** | None | Phase 3 (Browser — session manager) | Extends browser session with recovery strategies; needs existing `BrowserSession` and `resolve_locator` |
| **4.3 Research Quality Scoring** | None | Phase 4 (Research — pipeline) | Needs `ResearchPipeline`, `Source`, and `Claim` schemas to score source quality |
| **4.4 Dynamic Model Routing** | 3.1 Confidence Engine | Phase 8 (Observability — structured logging) | Needs confidence engine's auto-approval logs to measure success rates; needs logging for routing decisions |

### Dependency Graph

```
Tier 1 (Confidence Engine) ──┬──→ 4.1 Feedback Loop
Phase 5 (Content) ───────────┘
                                 │
Phase 3 (Browser) ──────────────→ 4.2 Self-Healing Browser
                                 │
Phase 4 (Research) ─────────────→ 4.3 Research Quality Scoring
                                 │
Tier 1 (Confidence Engine) ──┬──→ 4.4 Dynamic Model Routing
Phase 8 (Observability) ─────┘
```

**Note:** Features 4.2 and 4.3 are independent of each other and can be built in parallel. Features 4.1 and 4.4 both depend on Tier 1 but are independent of each other.

---

## 2. Implementation Order

Build sequentially in this order. Each feature is a merge-ready PR.

| Step | Feature | Effort | Depends On |
|---|---|---|---|
| 1 | Feedback Loop / RLHF | 3–4 weeks | Tier 1 (Confidence), Phase 5 |
| 2 | Self-Healing Browser | 2–3 weeks | Phase 3 |
| 3 | Research Quality Scoring | 2–3 weeks | Phase 4 |
| 4 | Dynamic Model Routing | 2 weeks | Tier 1 (Confidence), Phase 8 |

**Rationale for ordering:**

- Feedback Loop is the foundation — it collects the data that powers all other learning features (4.4 uses feedback data for routing optimization)
- Self-Healing Browser is independent, build second to unblock browser-heavy tasks
- Research Quality Scoring is independent, build third to improve research pipeline quality
- Dynamic Model Routing benefits from feedback data collected by 4.1 — build last so it has maximum training data

---

## 3. Feature 4.1 — Feedback Loop / RLHF

### 3.1.1 Problem

The system doesn't learn from approval/rejection patterns or content performance metrics. Every task starts from scratch with no memory of what worked before.

### 3.1.2 Files to Create

```
app/feedback/__init__.py              — Package init
app/feedback/collector.py             — FeedbackCollector: record human decisions
app/feedback/analyzer.py              — FeedbackAnalyzer: pattern detection
app/feedback/prompt_updater.py        — PromptUpdater: adjust system prompts from patterns
app/feedback/routing_optimizer.py     — RoutingOptimizer: optimize model selection
app/db/models/feedback.py             — FeedbackEvent, LearningRecord ORM models
app/schemas/feedback.py               — FeedbackEvent, LearningPattern schemas
tests/unit/test_feedback_collector.py
tests/unit/test_feedback_analyzer.py
tests/unit/test_prompt_updater.py
tests/integration/test_feedback_loop.py
```

### 3.1.3 Files to Modify

| File | Change |
|---|---|
| `app/agents/orchestrator.py` | Call `FeedbackCollector.record_approval()` after each approval decision (auto or human) |
| `app/agents/graphs/social.py` | Call `FeedbackCollector.record_content_performance()` after publish + verification |
| `app/config.py` | Add `FeedbackSettings` dataclass |
| `app/api/router.py` | No new routes initially (data collection is internal) |

### 3.1.4 Orchestrator Integration

**Current approval flow (orchestrator.py:194):**

```python
if step.requires_approval and step.name not in approved_actions:
    if self.confidence_engine:
        decision = await self.confidence_engine.evaluate(step, context)
        if decision.approved:
            logger.info("auto_approved", ...)
            continue
    await self._request_approval(...)
    raise ApprovalRequiredError(...)
```

**New code with feedback collection:**

```python
if step.requires_approval and step.name not in approved_actions:
    if self.confidence_engine:
        decision = await self.confidence_engine.evaluate(step, context)
        if decision.approved:
            # NEW: Record auto-approval for learning
            if self.feedback_collector:
                await self.feedback_collector.record_approval(
                    task_id=task_id,
                    step=step,
                    approved=True,
                    auto_approved=True,
                    confidence_score=decision.confidence.value,
                )
            logger.info("auto_approved", ...)
            continue

    await self._request_approval(...)
    raise ApprovalRequiredError(...)
```

**Human approval callback (approval_service.py:69):**

```python
async def decide(self, approval_id: uuid.UUID, decision: ApprovalDecision) -> Approval:
    approval = await self.get_approval(approval_id)
    approval.status = "approved" if decision.approved else "rejected"
    approval.decided_by = decision.decided_by

    # NEW: Record human decision for learning
    if self.feedback_collector:
        await self.feedback_collector.record_approval(
            task_id=approval.task_id,
            step_name=approval.action,
            approved=decision.approved,
            auto_approved=False,
            decided_by=decision.decided_by,
        )

    next_state = TaskState.EXECUTING if decision.approved else TaskState.CANCELLED
    await self._tasks.transition_task(approval.task_id, next_state)
    ...
```

### 3.1.5 Database Schema

```sql
CREATE TABLE feedback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    step_name VARCHAR(128),
    agent VARCHAR(64),
    action_type VARCHAR(32) NOT NULL,       -- approval, performance, revision
    decision VARCHAR(16),                   -- approved, rejected (for approval type)
    auto_approved BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    decided_by VARCHAR(64),
    metrics JSONB,                          -- for performance type: likes, shares, etc.
    original_content TEXT,                  -- for revision type
    edited_content TEXT,                    -- for revision type
    recorded_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE learning_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(64) NOT NULL,      -- approval_preference, length_preference, etc.
    pattern_data JSONB NOT NULL,            -- pattern-specific data
    confidence FLOAT DEFAULT 0.0,
    sample_size INTEGER DEFAULT 0,
    discovered_at TIMESTAMPTZ DEFAULT now(),
    last_updated TIMESTAMPTZ DEFAULT now(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX ix_feedback_events_task ON feedback_events(task_id);
CREATE INDEX ix_feedback_events_type ON feedback_events(action_type);
CREATE INDEX ix_learning_records_type ON learning_records(pattern_type);
```

### 3.1.6 Key Design Decisions

1. **Three feedback types:** approval (human decision), performance (engagement metrics), revision (human edits before approval)
2. **Patterns are discovered, not configured:** `FeedbackAnalyzer` detects patterns from data; no manual pattern definition
3. **Prompt updates are additive:** `PromptUpdater` adds learned preferences to prompts, never removes existing instructions
4. **Routing optimization uses confidence engine data:** Auto-approval scores feed into success rate calculations

### 3.1.7 Configuration

```python
class FeedbackSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FEEDBACK_")

    enabled: bool = False
    lookback_days: int = 30
    min_samples_for_pattern: int = 10
    pattern_update_interval_hours: int = 24
```

### 3.1.8 Acceptance Criteria

- [ ] `FeedbackCollector.record_approval()` persists approval/rejection events with context
- [ ] `FeedbackCollector.record_content_performance()` persists engagement metrics
- [ ] `FeedbackCollector.record_revision()` persists original vs edited content
- [ ] `FeedbackAnalyzer.analyze_approval_patterns()` detects patterns with ≥ 10 samples
- [ ] `FeedbackAnalyzer.analyze_revision_patterns()` detects length/tone changes
- [ ] `PromptUpdater.update_content_prompt()` injects learned preferences into prompts
- [ ] `FEEDBACK_ENABLED=false` disables collection entirely (fallback to no learning)
- [ ] All feedback events logged with task_id, step_name, action_type for audit trail
- [ ] Unit tests pass for: collector persistence, analyzer pattern detection, prompt updater logic
- [ ] Integration test passes for: approval → analysis → prompt update end-to-end flow

---

## 4. Feature 4.2 — Self-Healing Browser

### 4.2.1 Problem

Browser tasks fail silently when pages change, elements move, or CAPTCHAs appear. Currently requires manual intervention to recover.

### 4.2.2 Files to Create

```
app/browser/recovery.py              — BrowserRecovery: failure detection + recovery
app/browser/strategies.py            — RecoveryStrategy ABC, SelectorFallback, CAPTCHADetector, PageCrashRecovery
app/browser/health.py                — BrowserHealthMonitor: session health tracking
app/schemas/browser.py               — Add RecoveryResult, RecoveryStrategy schemas
tests/unit/test_browser_recovery.py
tests/unit/test_selector_fallback.py
tests/unit/test_captcha_detector.py
tests/browser/test_recovery_flow.py
```

### 4.2.3 Files to Modify

| File | Change |
|---|---|
| `app/browser/session.py` | Add `recover()` method that delegates to `BrowserRecovery` |
| `app/browser/selectors.py` | Add `find_alternative_selectors()` for fallback discovery |
| `app/config.py` | Add `BrowserRecoverySettings` to `BrowserSettings` |

### 4.2.4 Integration with Browser Session

**Current crash handler (session.py:72):**

```python
def _install_crash_handler(self) -> None:
    self.page.on("crash", self._on_page_crash)
    self.page.on("close", self._on_page_close)
```

**New recovery integration:**

```python
async def recover_from_error(
    self,
    error: BrowserError,
    original_action: dict,
) -> RecoveryResult:
    """Attempt recovery from a browser error using configured strategies."""
    if not self.recovery:
        return RecoveryResult(
            success=False,
            error="No recovery strategies configured",
            escalate=True,
        )

    result = await self.recovery.recover(error, self, original_action)

    if result.success:
        self._health.record_recovery(error, result)
        logger.info(
            "browser.recovery.success",
            session_id=self.session_id,
            strategy=result.strategy_used,
            error_type=error.error_type,
        )
    else:
        self._health.record_failed_recovery(error)
        logger.warning(
            "browser.recovery.failed",
            session_id=self.session_id,
            strategies_attempted=result.attempts,
            error_type=error.error_type,
        )

    return result
```

### 4.2.5 Recovery Strategy Chain

```
BrowserError
    │
    ├─→ SelectorFallback     (element not found)
    │     Try: ARIA role → text content → test attributes → CSS
    │
    ├─→ PageCrashRecovery    (page crashed/unresponsive)
    │     Action: close page → new page → re-run action
    │
    ├─→ NavigationRecovery   (navigation timeout/failure)
    │     Action: retry with backoff → alternate URL → escalate
    │
    ├─→ CAPTCHADetector      (CAPTCHA detected)
    │     Action: escalate to human (never auto-bypass)
    │
    └─→ NetworkRecovery      (network errors)
          Action: retry with exponential backoff → escalate
```

### 4.2.6 Database Schema Extension

```sql
CREATE TABLE browser_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) NOT NULL,
    task_id UUID REFERENCES tasks(id),
    total_actions INTEGER DEFAULT 0,
    successful_actions INTEGER DEFAULT 0,
    failed_actions INTEGER DEFAULT 0,
    recoveries_attempted INTEGER DEFAULT 0,
    recoveries_succeeded INTEGER DEFAULT 0,
    last_error_type VARCHAR(64),
    last_error_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE browser_recovery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(64) NOT NULL,
    error_type VARCHAR(64) NOT NULL,
    strategy_used VARCHAR(64),
    success BOOLEAN NOT NULL,
    attempts JSONB,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### 4.2.7 Key Design Decisions

1. **CAPTCHAs always escalate** — never auto-bypass (AGENTS.md rule 172)
2. **Recovery is opt-in per session** — `BrowserSession` gets a `recovery` field, `None` means no recovery
3. **Health monitoring is passive** — tracks metrics without blocking actions
4. **Strategy chain is ordered** — first matching strategy runs; if it fails, next strategy runs

### 4.2.8 Acceptance Criteria

- [ ] `SelectorFallback` tries ARIA role → text → test attributes → CSS when element not found
- [ ] `PageCrashRecovery` closes crashed page, opens new one, re-runs action
- [ ] `CAPTCHADetector` detects CAPTCHAs and escalates (never auto-bypasses)
- [ ] `BrowserRecovery.recover()` tries strategies in order until one succeeds
- [ ] `BrowserHealthMonitor` tracks success/failure/recovery rates per session
- [ ] Recovery log persisted to DB with error type, strategy, success, attempts
- [ ] `BROWSER_RECOVERY_ENABLED=false` disables recovery (fallback to current behavior)
- [ ] Unit tests pass for: strategy selection, fallback chain, CAPTCHA detection
- [ ] Browser test passes for: recovery flow with controlled test pages

---

## 5. Feature 4.3 — Research Quality Scoring

### 5.3.1 Problem

The system doesn't know which sources produce high-quality output. All research sources are treated equally, regardless of historical performance.

### 5.3.2 Files to Create

```
app/research/quality.py              — ResearchQualityScorer: score source quality
app/research/source_ranker.py        — SourceRanker: rank sources by historical performance
app/db/models/research_quality.py    — SourceQuality, ResearchOutcome ORM models
app/schemas/research.py              — Add SourceScore, ResearchOutcome schemas
tests/unit/test_research_quality.py
tests/unit/test_source_ranker.py
tests/integration/test_research_quality_flow.py
```

### 5.3.3 Files to Modify

| File | Change |
|---|---|
| `app/agents/graphs/research.py` | Inject `SourceRanker` to rank sources before research; record outcomes after |
| `app/research/pipeline.py` | Add `score_source()` method to pipeline stages |
| `app/config.py` | Add `ResearchQualitySettings` |

### 5.3.4 Integration with Research Graph

**Current research graph (research.py):**

```python
# Research graph uses web_search and lang_search tools
# Sources are returned in search order, not ranked by quality
```

**New integration:**

```python
# In research graph, before processing sources:
ranked_sources = await source_ranker.rank_sources(
    sources=raw_sources,
    query=research_query,
)

# Process top-ranked sources first
for source in ranked_sources[:max_sources]:
    claims = await extract_evidence(source)
    ...

# After research completes, record outcome:
await quality_scorer.record_outcome(
    sources=used_sources,
    task_id=task_id,
    claims_extracted=len(claims),
    fact_check_passed=fact_check_passed,
)
```

### 5.3.5 Database Schema

```sql
CREATE TABLE source_quality (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url VARCHAR(2048) NOT NULL,
    source_type VARCHAR(32),                -- primary, official, secondary, etc.
    total_uses INTEGER DEFAULT 0,
    approval_rate FLOAT DEFAULT 0.0,        -- % of times content using this source was approved
    engagement_rate FLOAT DEFAULT 0.0,      -- avg engagement of content using this source
    fact_check_rate FLOAT DEFAULT 0.0,      -- % of times claims from this source passed fact-check
    composite_score FLOAT DEFAULT 0.5,      -- weighted average
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE research_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    source_urls JSONB NOT NULL,             -- list of source URLs used
    claims_extracted INTEGER DEFAULT 0,
    claims_fact_checked INTEGER DEFAULT 0,
    fact_check_passed BOOLEAN,
    content_approved BOOLEAN,
    engagement_metrics JSONB,
    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ix_source_quality_url ON source_quality(source_url);
CREATE INDEX ix_source_quality_score ON source_quality(composite_score DESC);
```

### 5.3.6 Scoring Formula

```python
composite_score = (
    0.4 * approval_rate +      # How often content using this source gets approved
    0.4 * engagement_rate +    # How well content using this source performs
    0.2 * fact_check_rate      # How often claims from this source pass fact-check
)

confidence = min(total_uses / 10, 1.0)  # More uses = higher confidence in score
```

### 5.3.7 Key Design Decisions

1. **Scores are URL-based** — same URL always gets the same score history
2. **Confidence increases with usage** — new sources start at 0.5 confidence, max out at 10+ uses
3. **Scores are additive** — each outcome updates the running average, never overwrites
4. **Source type is a signal** — `primary` and `official` sources get a small boost

### 5.3.8 Configuration

```python
class ResearchQualitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RESEARCH_QUALITY_")

    enabled: bool = False
    min_samples_for_ranking: int = 3
    approval_weight: float = 0.4
    engagement_weight: float = 0.4
    fact_check_weight: float = 0.2
    source_type_boost: float = 0.05        # boost for primary/official sources
```

### 5.3.9 Acceptance Criteria

- [ ] `ResearchQualityScorer.score_source()` returns score with confidence based on usage count
- [ ] `SourceRanker.rank_sources()` sorts sources by composite score descending
- [ ] New sources start at 0.5 score with 0.0 confidence
- [ ] Source type boost applied for primary/official sources
- [ ] `record_outcome()` updates running averages for all used sources
- [ ] `RESEARCH_QUALITY_ENABLED=false` disables scoring (fallback to unranked sources)
- [ ] Unit tests pass for: scoring formula, ranking order, confidence calculation
- [ ] Integration test passes for: research → outcome recording → score update

---

## 6. Feature 4.4 — Dynamic Model Routing

### 6.4.1 Problem

Model routing is static — the same model class is used for similar tasks regardless of historical cost/success tradeoffs. The system can't learn that a cheaper model works well enough for certain task types.

### 6.4.2 Files to Create

```
app/llm/adaptive_router.py           — AdaptiveModelRouter: learns optimal model per task type
app/llm/performance_tracker.py       — PerformanceTracker: track model outcomes
app/db/models/model_performance.py   — ModelPerformance ORM model
tests/unit/test_adaptive_router.py
tests/unit/test_performance_tracker.py
tests/integration/test_adaptive_routing_flow.py
```

### 6.4.3 Files to Modify

| File | Change |
|---|---|
| `app/llm/router.py` | Add `AdaptiveModelRouter` that wraps `ModelRouter` |
| `app/agents/orchestrator.py` | Inject `PerformanceTracker` to record model selection + outcome |
| `app/config.py` | Add `AdaptiveRoutingSettings` |

### 6.4.4 Integration with Orchestrator

**Current model selection (orchestrator._invoke_subgraph):**

```python
# Model selection happens inside each graph via resolve_model()
# No outcome tracking
```

**New integration:**

```python
# Before subgraph invocation:
model_selection = self.adaptive_router.route(criteria)
self.performance_tracker.record_selection(
    task_type=criteria.task_type,
    model_class=model_selection.model_class,
    task_id=task_id,
)

# After subgraph invocation:
self.performance_tracker.record_outcome(
    task_type=criteria.task_type,
    model_class=model_selection.model_class,
    success=result.success,
    cost=usage_info.total_cost,
    latency_ms=usage_info.latency_ms,
)
```

### 6.4.5 Database Schema

```sql
CREATE TABLE model_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR(64) NOT NULL,         -- research, content, browser, etc.
    model_class VARCHAR(32) NOT NULL,       -- fast, tool_calling, reasoning, strongest
    total_calls INTEGER DEFAULT 0,
    successful_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    success_rate FLOAT DEFAULT 0.0,
    avg_cost_usd FLOAT DEFAULT 0.0,
    avg_latency_ms FLOAT DEFAULT 0.0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX ix_model_performance_task_model ON model_performance(task_type, model_class);
```

### 6.4.6 Routing Logic

```python
class AdaptiveModelRouter:
    """Extends ModelRouter with learning from outcomes."""

    def route(self, criteria: RoutingCriteria) -> ModelSelection:
        # Get base recommendation from static router
        base = self.base_router.route(criteria)

        # Look up historical performance for this task type
        history = self.tracker.get_history(criteria.task_type)

        if history and history.sample_size >= 10:
            # Find the cheapest model that meets quality threshold
            for model_class in [ModelClass.FAST, ModelClass.TOOL_CALLING, ModelClass.REASONING]:
                perf = history.get_performance(model_class)
                if (
                    perf
                    and perf.success_rate >= 0.9
                    and perf.avg_cost < base_cost * 0.5
                ):
                    return ModelSelection(
                        model_class=model_class,
                        provider=base.provider,
                        model_name=self.base_router._model_name_for(model_class),
                        reasoning=(
                            f"Adaptive routing: {model_class.value} has "
                            f"{perf.success_rate:.0%} success rate at lower cost"
                        ),
                    )

        return base  # Fall back to static routing
```

### 6.4.7 Key Design Decisions

1. **Minimum 10 samples** before adaptive routing kicks in — prevents overfitting on small data
2. **Success rate threshold 90%** — only downgrade if cheaper model is highly reliable
3. **Cost threshold 50%** — only downgrade if cheaper model is significantly cheaper
4. **Fallback to static routing** — if no history or insufficient samples, use base router
5. **Routing decisions are logged** — every adaptive routing decision recorded for audit

### 6.4.8 Configuration

```python
class AdaptiveRoutingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ADAPTIVE_ROUTING_")

    enabled: bool = False
    min_samples: int = 10
    success_rate_threshold: float = 0.9
    cost_reduction_threshold: float = 0.5
    learning_rate: float = 0.1             # how fast scores adjust to new data
```

### 6.4.9 Acceptance Criteria

- [ ] `AdaptiveModelRouter.route()` uses base router when no history exists
- [ ] `AdaptiveModelRouter.route()` downgrades to cheaper model when success_rate ≥ 0.9 and avg_cost < 50% of base
- [ ] `PerformanceTracker.record_selection()` persists model selection with task_type
- [ ] `PerformanceTracker.record_outcome()` updates success_rate, avg_cost, avg_latency
- [ ] Minimum 10 samples required before adaptive routing activates
- [ ] `ADAPTIVE_ROUTING_ENABLED=false` disables adaptive routing (fallback to static)
- [ ] All routing decisions logged with reasoning for observability
- [ ] Unit tests pass for: routing logic, threshold behavior, fallback to static
- [ ] Integration test passes for: selection → outcome → routing update end-to-end

---

## 7. Migration Strategy

Run Alembic migrations in order:

| Order | Migration | Tables Affected |
|---|---|---|
| 1 | `add feedback events and learning records` | `feedback_events`, `learning_records` (new) |
| 2 | `add browser health and recovery log` | `browser_health`, `browser_recovery_log` (new) |
| 3 | `add source quality and research outcomes` | `source_quality`, `research_outcomes` (new) |
| 4 | `add model performance tracking` | `model_performance` (new) |

```bash
alembic revision --autogenerate -m "add feedback events and learning records"
alembic revision --autogenerate -m "add browser health and recovery log"
alembic revision --autogenerate -m "add source quality and research outcomes"
alembic revision --autogenerate -m "add model performance tracking"
```

---

## 8. Risk Matrix

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Feedback loop learns wrong patterns | HIGH | LOW | Minimum sample size (10); patterns reviewed by human in weekly summary |
| Self-healing browser bypasses security | HIGH | LOW | CAPTCHAs always escalate; recovery strategies are deterministic, not LLM-inferred |
| Research quality scoring biases sources | MEDIUM | MEDIUM | Confidence increases with usage; new sources start neutral (0.5) |
| Adaptive routing downgrades too aggressively | MEDIUM | LOW | 90% success threshold; 50% cost reduction required; fallback to static |
| Feedback collection adds latency | LOW | MEDIUM | Collection is async/fire-and-forget; doesn't block task execution |
| Browser recovery creates infinite loops | MEDIUM | LOW | Max recovery attempts configurable; escalation after exhausted strategies |

---

## 9. Acceptance Criteria Summary

### Feature 4.1: Feedback Loop

- [ ] Approval, performance, and revision events recorded
- [ ] Pattern detection works with ≥ 10 samples
- [ ] Prompt updater injects learned preferences
- [ ] `FEEDBACK_ENABLED=false` disables entirely
- [ ] Unit + integration tests pass

### Feature 4.2: Self-Healing Browser

- [ ] SelectorFallback tries alternative selectors
- [ ] PageCrashRecovery opens new page and re-runs action
- [ ] CAPTCHADetector escalates to human
- [ ] Health monitoring tracks success/failure rates
- [ ] Recovery log persisted to DB

### Feature 4.3: Research Quality Scoring

- [ ] Source scoring uses approval + engagement + fact-check weights
- [ ] Ranking sorts by composite score descending
- [ ] New sources start at 0.5 with 0.0 confidence
- [ ] Outcomes update running averages

### Feature 4.4: Dynamic Model Routing

- [ ] Adaptive routing activates after 10+ samples
- [ ] Downgrades to cheaper model when success ≥ 90% and cost < 50%
- [ ] Fallback to static routing when no history
- [ ] Routing decisions logged for audit

---

**Document version:** 1.0
**Last updated:** 2026-09-12
**Status:** Ready for implementation
