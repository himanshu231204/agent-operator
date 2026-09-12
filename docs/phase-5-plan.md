# Phase 5 — Content: Detailed Implementation Plan

Branch: `phase-5-content`

## What already exists (no-op)

| Item | File |
|------|------|
| `ContentGenerator` ABC | `app/content/generator.py:29` |
| `LLMContentGenerator` (model-router-backed) | `app/content/generator.py:38` |
| `ContentDraftTool` (validate + thread-split) | `app/tools/builtin/content.py:62` |
| `ContentValidateTool` (deterministic checks) | `app/tools/builtin/content.py:113` |
| Content agent graph + compile | `app/agents/graphs/content.py` |
| Draft ORM model | `app/db/models/draft.py` |
| `POST /content/drafts`, `GET`, `PATCH` | `app/api/routes/content.py` |
| Draft schemas + tool I/O schemas | `app/schemas/content.py` |
| Real-LLM integration test | `tests/integration/test_content_generator_real_llm.py` |
| Graph + tools unit tests | `tests/integration/test_content_graph.py`, `tests/unit/test_content_tools.py`, `tests/unit/test_llm_content_generator.py` |

## What Phase 5 must deliver

Per PROJECT.md §12 and TODO.md Phase 5:

1. **LLM-backed tone + safety check** — layer semantic validation on top of deterministic validators.
2. **Thread support for X** — API exposes multi-post drafts with ordering.
3. **Draft editing flow** — research-aware draft creation, not just raw content.
4. **Content skill wiring** — replace `NotImplementedError` in `skills/content-generation/graph.py`.
5. **Orchestrator integration** — content agent participates in the plan→execute loop.

---

## Work items (in order)

- [x] 1. `ToneSafetyChecker` — done (`app/content/tone_safety.py`)
- [x] 2. `validate_content_async` extension — done (`app/content/validators.py`)
- [x] 3. `ContentValidateTool`/`ContentDraftTool` wiring — done (`app/tools/builtin/content.py`)
- [x] 4. Schema updates — done (`app/schemas/content.py`)
- [x] 5. LLM generation in `POST /content/drafts` — done (`app/api/routes/content.py`)
- [x] 6. Skill wiring — done (`skills/content_generation/graph.py`)
- [x] 7. Orchestrator integration — already mapped (`_AGENT_KEY` includes `"content"`)
- [x] 8. Thread support — done (`ContentDraftTool` splits >280 chars)
- [x] 9. Tone + safety tests — done (`tests/unit/test_tone_safety.py`, `tests/unit/test_content_validators.py`)
- [x] 10. TODO.md Phase 5 checklist — done

### 1. Add `ToneSafetyChecker` (LLM-backed semantic check)

**File**: `app/content/tone_safety.py` (new)

- New class `ToneSafetyChecker` with method `async check(content: str, tone: TonePreference) -> list[ContentValidationIssue]`.
- Uses `ModelRouter` with `RoutingCriteria(structured_output=True, requires_reasoning=False, risk_level=RiskLevel.MEDIUM, task_complexity=TaskComplexity.SIMPLE)` — this hits the FAST/TOOL_CALLING class, not REASONING; tone/safety is a cheap semantic check, not deep research.
- System prompt: check for (a) tone deviation from requested tone, (b) factual claims unsupported by the research block, (c) safety issues (harassment, dangerous instructions, self-harm, hate speech). Return JSON list of `{check: "tone"|"safety", message: str}`.
- Uses `StructuredTool`-style `with_structured_output` or `bind_tools` — returns `list[ContentValidationIssue]`. Keep it thin: one LLM call, parse JSON, return issues list (empty = pass).
- Unit test with `AsyncMock` model — verify prompt contains tone + content, verify JSON parsing, verify empty issues on clean content.

**Why separate from validators.py**: validators.py is deterministic (AGENTS.md rule 273 — never use an LLM where deterministic checks suffice). Tone and semantic safety need LLM judgment (rule 272).

### 2. Extend `validate_content()` to accept optional `ToneSafetyChecker`

**File**: `app/content/validators.py`

- `validate_content(platform, content, *, existing_hashes=None, tone=None, tone_checker=None) -> ContentValidationResult`
- When `tone_checker` is provided, call `await tone_checker.check(content, tone)` and append returned issues.
- Backward-compatible: existing callers (API route, `ContentValidateTool`) work unchanged — `tone_checker` defaults to `None`.
- Add `TonePreference` import (already in `app/schemas/content.py`).
- Update tests: add one test verifying tone checker integration, one verifying backward-compat (no checker → no tone issues).

### 3. Extend `ContentValidateTool` to accept optional tone + checker

**File**: `app/tools/builtin/content.py`

- Add `tone: TonePreference | None = None` to `ContentValidateToolInput` (schema in `app/schemas/content.py`).
- Late-bind the `ToneSafetyChecker` (same pattern as `FactCheckTool.wire_engine` — too early in the dep graph to construct at import time).
- When `tone` is provided and checker is wired, call `validate_content(..., tone=tone, tone_checker=self._tone_checker)`.
- `ContentDraftTool` also gains the optional `tone` field (already exists on `ContentDraftToolInput`) — thread posts get the same validation per-post.

**Files changed**: `app/schemas/content.py` (add tone to validate input), `app/tools/builtin/content.py` (wire checker), `app/tools/factory.py` (inject checker at engine-build time, like `FactCheckTool.wire_engine`).

### 4. Add `DraftTonePreferenceRequest` schema + update `DraftCreateRequest`

**File**: `app/schemas/content.py`

- Add `tone: TonePreference | None = None` to `DraftCreateRequest` — optional, defaults to `None`.
- Add optional `research: list[ClaimInput] | None = None` where `ClaimInput` is a new lightweight schema `{claim: str, confidence: float}` — research context the LLM drafts from (avoids inventing facts per AGENTS.md rule 120).
- Both fields are optional; existing API callers without them work unchanged.

### 5. Wire LLM generation into `POST /content/drafts`

**File**: `app/api/routes/content.py`

- New optional dependency `ToneSafetyChecker` + `LLMContentGenerator` (lazily constructed via deps.py, only when tone/research is provided).
- When `payload.research` is present: route through `LLMContentGenerator.generate_draft()` → `validate_content()` → `ToneSafetyChecker.check()` → persist.
- When `payload.tone` is provided without research: still run tone checker on the raw content.
- Keep existing path: raw content without research/tone still validates deterministically.
- Error handling: LLM failure → `ValidationError` with retryable flag; tone/safety failure → `ValidationError` non-retryable.
- Integration test: `tests/integration/test_content_api.py` gains one test for research-aware draft creation (mocked LLM).

### 6. Implement `skills/content-generation/graph.py`

**File**: `skills/content-generation/graph.py`

- Replace `NotImplementedError` with actual compiled subgraph — same pattern as `skills/web-research/graph.py`.
- `_TOOL_NAMES = ["content_draft", "content_validate"]`.
- `build_skill(router, engine, registry, *, context=None)` → calls `create_react_agent` with `CONTENT_CRITERIA` model + collected tools.
- Import `CONTENT_CRITERIA` from `app/agents/graphs/_helpers.py`.
- Unit test: `tests/unit/test_content_skill.py` — verify graph compiles with mocked model, verify tools are collected.

### 7. Wire content agent into orchestrator plan→execute loop

**File**: `app/agents/orchestrator.py`

- `_AGENT_KEY` already maps `"content": "content"` (line 66). No change needed.
- Planner agent must know about the content agent step type. Inspect `app/agents/planner.py` to verify `"content"` is an allowed agent value in the plan step schema — if not, add it.
- Verify: when a plan step has `agent="content"`, the orchestrator invokes the content graph with the step description as the HumanMessage, receives the last AI message as the draft result.
- Add integration test: orchestrator runs a two-step plan (research → content), mocked subgraphs, verify the content graph is invoked with the research output.

### 8. Thread support — expose multi-post drafts via API

**File**: `app/schemas/content.py`, `app/api/routes/content.py`

- Add `DraftThreadResponse` schema: `{draft_id, platform, thread_posts: list[ThreadPost], character_count, warnings}`.
- When `ContentDraftToolOutput.thread_posts` is non-empty, return the thread response shape.
- Add `GET /content/drafts/{draft_id}/posts` — returns the ordered thread posts for a draft (parsed from `formatted_content` which is `\n\n`-joined).
- Test: create a draft with >280 chars of research → verify thread posts returned, verify ordering and numbering.

### 9. Tone + safety tests

**File**: `tests/unit/test_tone_safety.py` (new)

- Test `ToneSafetyChecker` with mocked model: (a) clean content → empty issues, (b) tone deviation → issue returned, (c) safety violation → issue returned, (d) malformed JSON from model → handled gracefully (empty issues + logged warning), (e) LLM exception → empty issues + logged error (fail-open: deterministic checks already ran).

### 10. Update TODO.md Phase 5 checklist

Mark all five Phase 5 items complete once implementation is verified.

---

## Dependency graph

```
app/schemas/content.py          ← tone + research fields on DraftCreateRequest
        ↓
app/content/tone_safety.py      ← new LLM-backed ToneSafetyChecker
        ↓
app/content/validators.py       ← optional tone_checker param
        ↓
app/tools/builtin/content.py    ← wire checker in ContentValidateTool, add tone to input schema
app/tools/factory.py            ← inject checker at engine build time
        ↓
app/api/deps.py                 ← lazy ToneSafetyChecker + LLMContentGenerator provider
app/api/routes/content.py       ← research-aware draft creation path
        ↓
skills/content-generation/graph.py  ← replace NotImplementedError
        ↓
app/agents/planner.py           ← verify content agent is allowed in plan steps
app/agents/orchestrator.py      ← verify content graph wired (already mapped)
        ↓
tests/unit/test_tone_safety.py  ← new
tests/unit/test_content_validators.py ← new tone integration tests
tests/integration/test_content_api.py  ← new research-aware draft test
tests/unit/test_content_skill.py ← new
```

## Verification

```bash
# All existing tests still pass
pytest tests/ -x --ignore=tests/integration/test_content_generator_real_llm.py

# Real-LLM smoke test (requires OPENROUTER_API_KEY)
pytest tests/integration/test_content_generator_real_llm.py -v -s

# Verify content skill is importable and compiles
python -c "from skills.content_generation.graph import build_skill; print('OK')"

# Verify orchestrator routes to content agent
python -c "from app.agents.orchestrator import _AGENT_KEY; assert 'content' in _AGENT_KEY"
```

## Definition of Done

- [ ] `ToneSafetyChecker` implemented, tested, wired into validators
- [ ] Content agent graph invokes content tools through `ToolExecutionEngine`
- [ ] `skills/content-generation/graph.py` returns a compiled `CompiledGraph` (not `NotImplementedError`)
- [ ] `POST /content/drafts` accepts optional `research` + `tone` → LLM generates draft → validates → persists
- [ ] Thread drafts >280 chars are split and returned with ordering
- [ ] Orchestrator plan→execute loop can run a `content` step
- [ ] Unit tests: `test_tone_safety.py`, `test_content_skill.py`, new `test_content_validators.py` cases
- [ ] Integration test: research → content plan with mocked subgraphs
- [ ] `TODO.md` Phase 5 checklist fully checked
