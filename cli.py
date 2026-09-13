"""CLI for approval workflows (Phase 7 — Safety).

Provides command-line interface for approving/rejecting tasks,
cancelling tasks, and running secrets audit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid

import httpx


class ApprovalCLI:
    """CLI client for the Agent Operator approval API."""

    def __init__(self, api_base: str) -> None:
        self._api_base = api_base.rstrip("/")

    async def poll_and_prompt(self, task_id: uuid.UUID) -> None:
        """Poll for pending approval and prompt user to decide."""
        async with httpx.AsyncClient() as client:
            # Get pending approval
            response = await client.get(
                f"{self._api_base}/api/v1/tasks/{task_id}/approval"
            )
            if response.status_code == 404:
                print(f"No pending approval for task {task_id}")
                return

            approval = response.json()
            print(f"\nApproval Request")
            print(f"{'=' * 50}")
            print(f"Task ID: {approval['task_id']}")
            print(f"Action: {approval['action']}")
            print(f"Target: {approval['target']}")
            print(f"Risk Level: {approval['risk_level']}")
            print(f"Reason: {approval.get('reason', 'N/A')}")
            print(f"{'=' * 50}\n")

            decision = input("Approve? [y/n]: ").strip().lower()
            approved = decision == "y"

            # Submit decision
            response = await client.post(
                f"{self._api_base}/api/v1/tasks/{task_id}/approval",
                json={"approved": approved, "decided_by": "cli-user"},
            )
            result = response.json()
            print(f"\nDecision recorded: {result['status']}")

    async def cancel_task(self, task_id: uuid.UUID) -> None:
        """Cancel a running task."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._api_base}/api/v1/tasks/{task_id}/cancel"
            )
            result = response.json()
            print(f"Task {task_id} cancelled. State: {result['state']}")

    async def audit_secrets(self) -> None:
        """Run secrets audit and display findings."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._api_base}/api/v1/audit/secrets"
            )
            result = response.json()
            print(f"\nSecrets Audit")
            print(f"{'=' * 50}")
            print(f"Scanned: {result['scanned']} tool calls")
            print(f"Findings: {len(result['findings'])}")

            for finding in result["findings"]:
                print(f"\n  Tool Call: {finding['tool_call_id']}")
                print(f"  Field: {finding['field']}")
                print(f"  Pattern: {finding['pattern']}")
                print(f"  Preview: {finding['redacted_preview']}")

            print(f"\n{'=' * 50}")


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="Agent Operator CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Approve a pending action")
    approve_parser.add_argument("--task-id", required=True, help="Task ID")

    # Cancel command
    cancel_parser = subparsers.add_parser("cancel", help="Cancel a running task")
    cancel_parser.add_argument("--task-id", required=True, help="Task ID")

    # Audit command
    subparsers.add_parser("audit", help="Run secrets audit")

    # Common arguments
    parser.add_argument(
        "--api-base",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = ApprovalCLI(api_base=args.api_base)

    if args.command == "approve":
        asyncio.run(cli.poll_and_prompt(uuid.UUID(args.task_id)))
    elif args.command == "cancel":
        asyncio.run(cli.cancel_task(uuid.UUID(args.task_id)))
    elif args.command == "audit":
        asyncio.run(cli.audit_secrets())


if __name__ == "__main__":
    main()
