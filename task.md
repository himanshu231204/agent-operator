# Research Pipeline — Implementation Plan

## Overview

This document describes the full implementation of the **Phase 4 research pipeline** for agent-operator. It covers every changed file, the design decisions behind each, and how to verify the work end-to-end.

The research pipeline enables the `research` agent subgraph to search the web and fetch pages through the permission-gated `ToolExecutionEngine`. Before this work, both tools raised `NotImplementedError` and the agent graph compiled with zero tools available.

---

## Architecture

```
OrchestratorState
  → research step
      → app/agents/graphs/research.py (build_graph)
          → collect_tools(["web_search", "web_fetch"], engine, registry)
              → WebSearchTool  (wraps TavilySearchResults)
              → WebFetchTool   (SSRF-protected httpx fetch)
          → create_react_agent(model, tools, state_modifier=SYSTEM_PROMPT)
              → ToolExecutionEngine.execute()  ← all calls gate here
                  → DB audit row (ToolCall)
                  → permission check (LOW risk, no approval needed)
                  → actual Tavily / httpx call
```

Context quarantine is preserved: the orchestrator passes only
`{"messages": [HumanMessage(content=step.description)]}` — the research
graph's `MessagesState` is never shared with the orchestrator.

---

## Files Changed

### 1. `app/config.py`
**Change:** Added `tavily_api_key: str | None = None` to `LLMProviderSettings`.

**Why:** The search tool reads this setting at call time so the API key stays out of source code and is validated in one place.

```python
# In LLMProviderSettings:
tavily_api_key: str | None = None
```

---

### 2. `app/tools/builtin/search.py`
**Change:** Replaced the `NotImplementedError` stub with a full `BaseTool` implementation.

**Key design decisions:**
- Wraps `langchain_community.tools.TavilySearchResults` via an async `ainvoke()` call — keeps the Tavily SDK encapsulated inside the tool, not exposed to the graph.
- Raises `ToolError(code="search_unavailable")` if `TAVILY_API_KEY` is missing, so the engine's audit row captures a clean failure rather than an uncaught `KeyError`.
- Input validation: `max_results` is `ge=1, le=20` so the LLM cannot request unbounded result sets.
- Risk level is `LOW` — no approval needed, no authentication needed.

```python
class WebSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)

class WebSearchOutput(BaseModel):
    results: list[SearchResult]

class WebSearchTool(BaseTool[WebSearchInput, WebSearchOutput]):
    name = "web_search"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)
    timeout_seconds = 20.0

    async def execute(self, tool_input: WebSearchInput) -> WebSearchOutput:
        api_key = get_settings().llm.tavily_api_key
        if not api_key:
            raise ToolError("Tavily API key not configured — set TAVILY_API_KEY")
        ...
```

**Environment variable required:**
```
TAVILY_API_KEY=tvly-...
```

---

### 3. `app/tools/builtin/fetch.py`
**Change:** Replaced the `NotImplementedError` stub with an SSRF-protected `httpx` fetcher.

**Key design decisions:**

**SSRF protection (`_guard_url`):**
Resolves the hostname to IPs *before* making any connection, then checks each IP against blocked ranges. This prevents DNS-rebinding attacks (resolve first, then block).

Blocked ranges:
| Range | Reason |
|---|---|
| `127.0.0.0/8` | Loopback |
| `10.0.0.0/8` | Private |
| `172.16.0.0/12` | Private |
| `192.168.0.0/16` | Private |
| `169.254.0.0/16` | Link-local / AWS metadata |
| `fc00::/7` | Unique local IPv6 |
| `::1/128` | IPv6 loopback |

Allowed URL schemes: `http`, `https` only. Raises `ToolError` for `file://`, `ftp://`, `data:`, etc.

**Content extraction:**
HTML is stripped of tags via `re.sub(r"<[^>]+>", " ", ...)` and whitespace collapsed. Output is truncated to 50,000 characters — enough context for the LLM, not enough to overwhelm the context window.

**Prompt injection safety:**
Fetched content is returned as data in `WebFetchOutput.content`. The research agent's system prompt explicitly instructs it to treat web content as untrusted external data that cannot modify its instructions.

```python
class WebFetchInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    timeout_seconds: float = Field(default=15.0, ge=1.0, le=60.0)

class WebFetchOutput(BaseModel):
    content: str
    status_code: int
    content_type: str
    url: str
```

---

### 4. `app/tools/factory.py` *(new file)*
**Change:** Centralised tool instantiation into a single `build_registry()` factory.

**Why:** Previously there was no registry initialisation code anywhere — no graph could actually run tools. This factory is called once per request (via FastAPI deps) and provides a fully populated `ToolRegistry`.

```python
def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in [
        FileReadTool(), FileWriteTool(), FileEditTool(), FileDeleteTool(),
        FolderCreateTool(), FolderListTool(), FolderDeleteTool(),
        ShellRunTool(),
        WebSearchTool(), WebFetchTool(),  # ← Phase 4 additions
    ]:
        registry.register(tool)
    return registry

def build_tool_engine(registry: ToolRegistry, session: AsyncSession) -> ToolExecutionEngine:
    return ToolExecutionEngine(registry=registry, session=session)
```

All 10 tools registered:
- `file_read`, `file_write`, `file_edit`, `file_delete` (filesystem)
- `folder_create`, `folder_list`, `folder_delete` (folder ops)
- `shell_run` (shell execution)
- `web_search` ← new
- `web_fetch` ← new

---

### 5. `app/api/deps.py`
**Change:** Added `get_tool_registry` and `get_tool_engine` FastAPI dependency providers.

```python
def get_tool_registry() -> ToolRegistry:
    return build_registry()

def get_tool_engine(
    session: DbSessionDep,
    registry: Annotated[ToolRegistry, Depends(get_tool_registry)],
) -> ToolExecutionEngine:
    return build_tool_engine(registry, session)

ToolRegistryDep = Annotated[ToolRegistry, Depends(get_tool_registry)]
ToolEngineDep = Annotated[ToolExecutionEngine, Depends(get_tool_engine)]
```

These follow the same pattern as `TaskServiceDep` and `ApprovalServiceDep` — dependency injection stays explicit, no service locator.

---

### 6. `app/agents/graphs/research.py`
**Change:** Fixed `prompt=` → `state_modifier=` for LangGraph 0.2.x API compatibility.

The `build_graph()` function was already structurally correct. With `WebSearchTool` and `WebFetchTool` now registered, `collect_tools(["web_search", "web_fetch"], engine, registry)` returns both tools (previously silently skipped).

Same fix applied to all other agent graphs:
- `app/agents/graphs/browser.py`
- `app/agents/graphs/content.py`
- `app/agents/graphs/fact_checker.py`
- `app/agents/graphs/local_system.py`
- `app/agents/graphs/social.py`
- `app/agents/graphs/verification.py`

---

### 7. `skills/web-research/graph.py`
**Change:** Replaced the `NotImplementedError` stub with a complete `build_skill()` implementation.

```python
def build_skill(
    router: ModelRouter,
    engine: ToolExecutionEngine,
    registry: ToolRegistry,
    *,
    context: ExecutionContext | None = None,
):
    model = resolve_model(router, RESEARCH_CRITERIA)
    tools = collect_tools(["web_search", "web_fetch"], engine, registry, context=context)
    return create_react_agent(model=model, tools=tools, state_modifier=_SYSTEM_PROMPT)
```

Mirrors the `build_graph()` pattern in `research.py` exactly — same model criteria, same tools, same ReAct structure.

---

### 8. `.env.example`
**Change:** Added `TAVILY_API_KEY=` entry under LLM providers section.

```
TAVILY_API_KEY=
```

---

## Tests Added

### `tests/unit/test_web_search_tool.py`
| Test | What it verifies |
|---|---|
| `test_happy_path` | Tavily results map correctly to `SearchResult` objects |
| `test_empty_results` | Empty Tavily response returns `WebSearchOutput(results=[])` |
| `test_missing_api_key_raises` | `ToolError` raised when `TAVILY_API_KEY` not set |
| `test_max_results_validation` | `max_results=0` and `max_results=21` both raise `ValidationError` |
| `test_query_min_length` | Empty query raises `ValidationError` |
| `test_tool_metadata` | Name, description, permissions are correct |

### `tests/unit/test_web_fetch_tool.py`
| Test | What it verifies |
|---|---|
| `test_ssrf_private_ip_blocked` (×8) | All private ranges blocked before any connection |
| `test_disallowed_schemes_blocked` (×3) | `file://`, `ftp://`, `data:` all raise `ToolError` |
| `test_public_url_passes` | `93.184.216.34` (example.com) passes the guard |
| `test_plain_text_returned` | Plain text content returned as-is |
| `test_html_tags_stripped` | `<h1>`, `<p>` tags removed from HTML content |
| `test_content_truncated_at_limit` | 100,000 char input truncated to 50,000 |
| `test_prompt_injection_content_is_data` | Injected instructions returned as inert data |
| `test_timeout_raises_tool_error` | `httpx.TimeoutException` → `ToolError` |
| `test_url_max_length_validation` | 2,050 char URL raises `ValidationError` |
| `test_tool_metadata` | Name, description, permissions are correct |

### `tests/unit/test_tool_factory.py`
| Test | What it verifies |
|---|---|
| `test_build_registry_registers_all_tools` | All 10 tool names present in registry |
| `test_web_search_in_registry` | `"web_search" in registry` → `True` |
| `test_web_fetch_in_registry` | `"web_fetch" in registry` → `True` |
| `test_get_web_search_tool` | `registry.get("web_search")` returns `WebSearchTool` instance |
| `test_get_web_fetch_tool` | `registry.get("web_fetch")` returns `WebFetchTool` instance |

### `tests/integration/test_research_graph.py`
| Test | What it verifies |
|---|---|
| `test_research_graph_compiles` | `build_graph()` returns a non-None compiled graph |
| `test_research_graph_has_web_tools` | `collect_tools` returns both `web_search` and `web_fetch` |
| `test_web_research_skill_compiles` | `skills/web-research/graph.py::build_skill()` compiles |

---

## Verification

```bash
# Run just the new tests
pytest tests/unit/test_web_search_tool.py \
       tests/unit/test_web_fetch_tool.py \
       tests/unit/test_tool_factory.py \
       tests/integration/test_research_graph.py \
       -v

# Full suite (114 tests pass)
pytest tests/ --ignore=tests/integration/test_health.py -q

# Lint (all pass)
ruff check app/tools/builtin/search.py app/tools/builtin/fetch.py \
          app/tools/factory.py app/api/deps.py \
          app/agents/graphs/research.py skills/web-research/graph.py
```

> Note: `tests/integration/test_health.py` has a pre-existing FastAPI 204/response-body
> conflict in `app/api/routes/browser.py` unrelated to this work.

---

## What Remains (Phase 5+)

| Component | Status | Notes |
|---|---|---|
| `app/agents/graphs/browser.py` | stub | Requires Playwright `browser_toolkit` |
| `app/agents/graphs/content.py` | stub | Content generation agent |
| `app/agents/graphs/social.py` | stub | HIGH-risk publishing — needs OAuth |
| `app/agents/graphs/fact_checker.py` | stub | Cross-references research output |
| `skills/browser-control/graph.py` | stub | Phase 3 |
| `skills/fact-checking/graph.py` | stub | Phase 4 |
| `skills/content-generation/graph.py` | stub | Phase 5 |
| `app/workers/` | placeholder | Background task worker (poll + execute) |
| Orchestrator wiring in `deps.py` | partial | Full `get_orchestrator` dep needs all graphs |
