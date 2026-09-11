"""LangGraph subgraph implementations for each specialized agent.

Each module exports a ``build_graph()`` factory that accepts a
``ModelRouter`` and ``ToolExecutionEngine`` and returns a compiled
LangGraph ``CompiledGraph``.  The orchestrator calls each subgraph with
an isolated ``MessagesState`` — never forwarding its own message history.
"""
