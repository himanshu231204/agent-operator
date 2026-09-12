# Phase 4 — Research: Detailed Implementation Plan

Status: not started → **in progress** (branch `phase-4-research`)

## Decision record (resolves "Search provider" TBD in TODO.md)

- **Primary search provider: Tavily.** `WebSearchTool` (`app/tools/builtin/search.py`)
  already wraps `langchain_community.tools.TavilySearchResults` end-to-end and is
  registered in `build_registry()`. The `.env.example` already exposes
  `TAVILY_API_KEY`. Decision: keep Tavily as the canonical source.
- **Secondary/fallback: LangSearch.** `LangSearchTool`
  (`app/tools/builtin/langsearch.py`) is already implemented, registered, and
  tested. It is registered under `lang_search` and is available to the research
  graph's `_TOOL_NAMES = ["web_search", "lang_search", "web_fetch"]`.
- Conclusion of the open TODO question: **no new search integration code is
  required**; both are wired. The remaining work is the *pipeline* that uses
  them — source classification, the concrete `ResearchPipeline`, the `fact_check`
  tool (currently referenced but unregistered), adversarial fixtures, and tests.

## What already exists (no-op for this phase)

| Item | Status | File |
|------|--------|------|
| `WebSearchTool` (Tavily) | done | `app/tools/builtin/search.py` |
| `WebFetchTool` (SSRF-guarded) | done | `app/tools/builtin/fetch.py` |
| `LangSearchTool` (secondary) | done | `app/tools/builtin/langsearch.py` |
| SSRF guard + fetch unit tests | done | `tests/unit/test_web_fetch_tool.py` |
| Search + langsearch unit tests | done | `tests/unit/test_web_search_tool.py`, `test_langsearch_tool.py` |
| `ResearchPipeline` ABC + evidence helpers | done | `app/research/pipeline.py`, `app/research/evidence.py` |
| Research schemas (`Source`, `Claim`) | done | `app/schemas/research.py` |
| `ResearchSource` / `ResearchClaim` ORM | done | `app/db/models/research.py` |
| Research agent subgraph | done | `app/agents/graphs/research.py` |
| Fact-checker subgraph (references `fact_check`) | done | `app/agents/graphs/fact_checker.py` |
| Research graph integration test | done | `tests/integration/test_research_graph.py` |

## Remaining Phase 4 TODO items → concrete tasks

The TODO marks Phase 4 items `[ ]`. They decompose as follows:

### Task 1 — `ResearchPipeline` concrete implementation
`app/research/pipeline.py` is currently an abstract base class only. Implement
a concrete `DefaultResearchPipeline` that:
1. Accepts a `ToolExecutionEngine` (dependency) and a `ModelRouter` (for the
   `REASONING` model class used to synthesize).
2. `search(question)` → calls `web_search` (and `lang_search` as fallback)
   through the engine, returns `[Source]` (up to `max_research_sources`).
3. `extract_evidence(source)` → calls `web_fetch` through the engine, uses
   `langchain_text_splitters` to chunk where chunk size improves retrieval
   quality (AGENS.md rule 101), extracts claims via an LLM structured-output
   pass over each chunk.
4. `cross_check(claims)` → groups claims by subject, fills
   `contradicting_evidence` where sources disagree (delegates to deterministic
   `evidence.has_conflicting_evidence` + a reasoning-model pass for semantic
   overlap), never silently resolving.
5. `synthesize(claims)` → single LLM call routed via `REASONING` model class,
   producing a cited answer. Only high-confidence claims (no contradicting
   evidence) are asserted as facts; disputed claims are surfaced.

Acceptance: `DefaultResearchPipeline` instantiates and the four async methods
are typed against the existing ABC; no real network call is required to import.

### Task 2 — Source classification + freshness weighting
`Source.source_type` and `Source.published_at` exist but nothing populates them.
Implement deterministic classification in `app/research/classification.py`:
- Domain-based heuristic: `.gov`/`.edu`/`.org` → primary/official; news domains
  → secondary; blogs/forums/social → community; unknown → unverified.
- Freshness weighting: a `freshness_score(published_at, retrieved_at) -> float`
  function that decays with age (7-day half-life) and returns `0.0` for
  undated.
- Tests for the heuristics + decay math (no network).

Acceptance: module pure-functions only, 100% unit coverage, no DB/LLM dependency.

### Task 3 — `fact_check` tool (registered)
The fact-checker graph references `fact_check` but nothing is registered for
that name → `collect_tools()` silently drops it. Implement
`BuiltinFactCheckTool` (`app/tools/builtin/fact_check.py`) as a `BaseTool`
that:
1. Takes a draft (content) + optional existing claims.
2. Uses `web_search` + `web_fetch` through the engine to look for
   corroborating/contradicting evidence.
3. Returns a structured `FactCheckReport` (list of claims with
   SUPPORTED/UNSUPPORTED/CONTRADICTED/UNVERIFIABLE status + evidence citations).
4. Risk level LOW (read-only research), no approval, no auth.

Register it in `app/tools/factory.py` and add to the fact-checker graph's
effective tool list (it's already declared in `_TOOL_NAMES`).

### Task 4 — Prompt-injection adversarial fixtures
Phase 4 explicitly asks for adversarial fixtures. Add
`tests/fixtures/adversarial_web_content.py` with payloads like
"Ignore all previous instructions", "You are now a different agent",
`<script>…</script>` injection, and unicode-direction overrides. Then add
a test (`tests/unit/test_research_prompt_injection.py`) that feeds each payload
through `web_fetch` + `extract_evidence` and asserts the synthesized output
never echoes attacker instructions / the tool still classifies content as DATA.

### Task 5 — Research pipeline + classification tests
`tests/unit/test_research_pipeline.py`: exercise `DefaultResearchPipeline`
with mocked `ToolExecutionEngine` + mocked model — verifies search→fetch→cross
-check→synthesize wiring, source classification is applied, conflicts are
surfaced, citations are preserved, `max_research_sources` is respected.

`tests/unit/test_research_classification.py`: pure-function tests for
Task 2.

Acceptance: full Phase 4 TODO checklist items satisfied, all tests green,
`ruff` + `mypy` clean on new/modified files.

## Execution order

1. Branch created ✅ (`phase-b-research`)
2. Task 2 (classification module) + its tests  → fast, no deps
3. Task 3 (fact_check tool) + registration
4. Task 1 (concrete pipeline)
5. Task 4 (adversarial fixtures)
6. Task 5 (pipeline + classification tests)
7. `langchain_text_splitters` — verify it's available transitively (it is per
   TODO wording); if missing, add to `pyproject.toml`.
8. Full test run: `pytest tests/ -m "not browser" --deselect <real-llm tests>`
   → 100% green.
9. Update `TODO.md` Phase 4 → `[x]` and `docs/phase-4-plan.md` → status.
