"""Integration tests for secrets audit."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.models.agent_run import AgentRun, ToolCall
from app.services.audit_service import audit_tool_calls


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with sessionmaker() as db_session:
        yield db_session

    await engine.dispose()


class TestSecretsAudit:
    @pytest.mark.asyncio
    async def test_no_findings_when_clean(self, session):
        """Test that clean tool calls produce no findings."""
        run = AgentRun(task_id=uuid.uuid4(), agent_name="test", status="success")
        session.add(run)
        await session.flush()

        call = ToolCall(
            agent_run_id=run.id,
            tool_name="web_search",
            risk_level="low",
            status="success",
            input={"query": "hello world"},
            output={"result": "clean data"},
        )
        session.add(call)
        await session.commit()

        result = await audit_tool_calls(session)
        assert result.scanned == 1
        assert len(result.findings) == 0

    @pytest.mark.asyncio
    async def test_detects_api_key(self, session):
        """Test detection of API key pattern."""
        run = AgentRun(task_id=uuid.uuid4(), agent_name="test", status="success")
        session.add(run)
        await session.flush()

        # Use a value that matches the regex: sk- followed by 20+ alphanumeric chars
        api_key = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
        call = ToolCall(
            agent_run_id=run.id,
            tool_name="web_search",
            risk_level="low",
            status="success",
            input={"api_key": api_key},
            output={},
        )
        session.add(call)
        await session.commit()

        result = await audit_tool_calls(session)
        assert len(result.findings) == 1
        assert result.findings[0].pattern == "api_key"
        assert result.findings[0].field == "input"
        # Verify redaction: first 4 chars + "..." + last 4 chars
        # "sk-abcdefghijklmnopqrstuvwxyz1234567890" -> "sk-a" + "..." + "7890"
        assert result.findings[0].redacted_preview == "sk-a...7890"

    @pytest.mark.asyncio
    async def test_detects_github_token(self, session):
        """Test detection of GitHub token pattern."""
        run = AgentRun(task_id=uuid.uuid4(), agent_name="test", status="success")
        session.add(run)
        await session.flush()

        call = ToolCall(
            agent_run_id=run.id,
            tool_name="shell_run",
            risk_level="medium",
            status="success",
            input={"token": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234"},
            output={},
        )
        session.add(call)
        await session.commit()

        result = await audit_tool_calls(session)
        assert len(result.findings) == 1
        assert result.findings[0].pattern == "github_token"

    @pytest.mark.asyncio
    async def test_detects_bearer_token(self, session):
        """Test detection of Bearer token pattern."""
        run = AgentRun(task_id=uuid.uuid4(), agent_name="test", status="success")
        session.add(run)
        await session.flush()

        call = ToolCall(
            agent_run_id=run.id,
            tool_name="web_fetch",
            risk_level="low",
            status="success",
            input={"authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"},
            output={},
        )
        session.add(call)
        await session.commit()

        result = await audit_tool_calls(session)
        assert len(result.findings) == 1
        assert result.findings[0].pattern == "bearer_token"

    @pytest.mark.asyncio
    async def test_detects_in_output(self, session):
        """Test detection in output field."""
        run = AgentRun(task_id=uuid.uuid4(), agent_name="test", status="success")
        session.add(run)
        await session.flush()

        call = ToolCall(
            agent_run_id=run.id,
            tool_name="shell_run",
            risk_level="medium",
            status="success",
            input={"command": "echo hello"},
            output={"result": "sk-secretkey1234567890abcdefghijklmnop"},
        )
        session.add(call)
        await session.commit()

        result = await audit_tool_calls(session)
        assert len(result.findings) == 1
        assert result.findings[0].field == "output"

    @pytest.mark.asyncio
    async def test_redaction_hides_full_value(self, session):
        """Test that full secret value is not exposed."""
        run = AgentRun(task_id=uuid.uuid4(), agent_name="test", status="success")
        session.add(run)
        await session.flush()

        secret = "sk-abcdefghijklmnopqrstuvwxyz1234567890"
        call = ToolCall(
            agent_run_id=run.id,
            tool_name="web_search",
            risk_level="low",
            status="success",
            input={"api_key": secret},
            output={},
        )
        session.add(call)
        await session.commit()

        result = await audit_tool_calls(session)
        preview = result.findings[0].redacted_preview
        # Full secret should not appear in preview
        assert secret not in preview
        # Verify format: first 4 + "..." + last 4
        assert len(preview) == 11  # "sk-a" + "..." + "7890" = 4 + 3 + 4
        assert preview.startswith("sk-a")
        assert "..." in preview
        assert preview.endswith("7890")
