"""Unit tests for CLI approval."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cli import ApprovalCLI


class TestApprovalCLI:
    @pytest.fixture
    def cli(self):
        return ApprovalCLI(api_base="http://localhost:8000")

    @pytest.mark.asyncio
    async def test_poll_and_prompt_approves(self, cli):
        """Test approving a pending action."""
        task_id = uuid.uuid4()
        mock_approval = {
            "task_id": str(task_id),
            "action": "social_publish_x",
            "target": "x",
            "risk_level": "high",
            "reason": "Publish to X",
        }
        mock_decision = {"status": "approved"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # Mock GET approval response
            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = mock_approval
            mock_client.get.return_value = mock_get_response

            # Mock POST decision response
            mock_post_response = MagicMock()
            mock_post_response.json.return_value = mock_decision
            mock_client.post.return_value = mock_post_response

            with patch("builtins.input", return_value="y"):
                await cli.poll_and_prompt(task_id)

            # Verify GET was called
            mock_client.get.assert_called_once_with(
                f"http://localhost:8000/api/v1/tasks/{task_id}/approval"
            )

            # Verify POST was called with approval
            mock_client.post.assert_called_once_with(
                f"http://localhost:8000/api/v1/tasks/{task_id}/approval",
                json={"approved": True, "decided_by": "cli-user"},
            )

    @pytest.mark.asyncio
    async def test_poll_and_prompt_rejects(self, cli):
        """Test rejecting a pending action."""
        task_id = uuid.uuid4()
        mock_approval = {
            "task_id": str(task_id),
            "action": "social_publish_x",
            "target": "x",
            "risk_level": "high",
            "reason": "Publish to X",
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_get_response = MagicMock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = mock_approval
            mock_client.get.return_value = mock_get_response

            mock_post_response = MagicMock()
            mock_post_response.json.return_value = {"status": "rejected"}
            mock_client.post.return_value = mock_post_response

            with patch("builtins.input", return_value="n"):
                await cli.poll_and_prompt(task_id)

            mock_client.post.assert_called_once_with(
                f"http://localhost:8000/api/v1/tasks/{task_id}/approval",
                json={"approved": False, "decided_by": "cli-user"},
            )

    @pytest.mark.asyncio
    async def test_poll_and_prompt_no_pending(self, cli):
        """Test when no pending approval exists."""
        task_id = uuid.uuid4()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_get_response = MagicMock()
            mock_get_response.status_code = 404
            mock_client.get.return_value = mock_get_response

            await cli.poll_and_prompt(task_id)

            # Should not POST anything
            mock_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_task(self, cli):
        """Test cancelling a task."""
        task_id = uuid.uuid4()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = {"state": "cancelled"}
            mock_client.post.return_value = mock_response

            await cli.cancel_task(task_id)

            mock_client.post.assert_called_once_with(
                f"http://localhost:8000/api/v1/tasks/{task_id}/cancel"
            )

    @pytest.mark.asyncio
    async def test_audit_secrets(self, cli):
        """Test secrets audit."""
        mock_result = {
            "scanned": 100,
            "findings": [
                {
                    "tool_call_id": str(uuid.uuid4()),
                    "field": "input",
                    "pattern": "api_key",
                    "redacted_preview": "sk-...abcd",
                }
            ],
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_response = MagicMock()
            mock_response.json.return_value = mock_result
            mock_client.get.return_value = mock_response

            await cli.audit_secrets()

            mock_client.get.assert_called_once_with(
                "http://localhost:8000/api/v1/audit/secrets"
            )
