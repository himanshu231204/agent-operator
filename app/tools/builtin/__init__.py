"""Wrappers around langchain-community built-in tools and toolkits.

Every wrapper routes execution through ``ToolExecutionEngine`` so
permission checks and audit logging are never bypassed.  Import the
factory functions here to build permission-aware StructuredTool instances.
"""
