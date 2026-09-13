"""CLI for agent operator (Phase 7 + 8).

Provides command-line interface for:
- Approving/rejecting tasks (Phase 7)
- Cancelling tasks (Phase 7)
- Running secrets audit (Phase 7)
- Creating and tracking tasks (Phase 8)
- Viewing task logs (Phase 8)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid

import httpx


class ApprovalCLI:
    """CLI client for the Agent Operator API."""

    def __init__(self, api_base: str) -> None:
        self._api_base = api_base.rstrip("/")

    async def poll_and_prompt(self, task_id: uuid.UUID) -> None:
        """Poll for pending approval and prompt user to decide."""
        async with httpx.AsyncClient() as client:
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

    async def run_task(self, instruction: str, timeout: int | None = None) -> None:
        """Create a task and monitor its progress."""
        async with httpx.AsyncClient() as client:
            # Create task
            payload = {"instruction": instruction}
            if timeout:
                payload["timeout_seconds"] = timeout

            response = await client.post(
                f"{self._api_base}/api/v1/tasks",
                json=payload,
            )
            task = response.json()
            task_id = task["id"]
            print(f"Task created: {task_id}")
            print(f"Initial state: {task['state']}")

            # Poll until terminal state
            while True:
                await asyncio.sleep(2)
                response = await client.get(
                    f"{self._api_base}/api/v1/tasks/{task_id}"
                )
                task = response.json()
                state = task["state"]
                print(f"  State: {state}")

                if state in ("completed", "failed", "cancelled", "timed_out"):
                    break

            print(f"\nFinal state: {state}")
            if task.get("result"):
                print(f"Result: {task['result']}")

    async def get_status(self, task_id: uuid.UUID) -> None:
        """Show current task state and result."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._api_base}/api/v1/tasks/{task_id}"
            )
            task = response.json()
            print(f"\nTask Status")
            print(f"{'=' * 50}")
            print(f"ID: {task['id']}")
            print(f"Instruction: {task['instruction']}")
            print(f"State: {task['state']}")
            print(f"Created: {task['created_at']}")
            print(f"Updated: {task['updated_at']}")
            if task.get("result"):
                print(f"Result: {task['result']}")
            if task.get("error"):
                print(f"Error: {task['error']}")

    async def get_logs(self, task_id: uuid.UUID, limit: int = 20) -> None:
        """Show recent agent runs for a task."""
        async with httpx.AsyncClient() as client:
            # Get agent runs
            response = await client.get(
                f"{self._api_base}/api/v1/tasks/{task_id}/runs"
            )
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                return

            runs = response.json()
            print(f"\nTask Logs (last {limit})")
            print(f"{'=' * 50}")

            for run in runs[:limit]:
                print(f"\n  Agent: {run['agent_name']}")
                print(f"  Status: {run['status']}")
                print(f"  Duration: {run.get('duration_seconds', 'N/A')}s")
                if run.get("output"):
                    print(f"  Output: {run['output']}")


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

    # Run command
    run_parser = subparsers.add_parser("run", help="Create and monitor a task")
    run_parser.add_argument("instruction", help="Task instruction")
    run_parser.add_argument("--timeout", type=int, help="Timeout in seconds")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show task status")
    status_parser.add_argument("--task-id", required=True, help="Task ID")

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show task logs")
    logs_parser.add_argument("--task-id", required=True, help="Task ID")
    logs_parser.add_argument("--limit", type=int, default=20, help="Max log entries")

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
    elif args.command == "run":
        asyncio.run(cli.run_task(args.instruction, args.timeout))
    elif args.command == "status":
        asyncio.run(cli.get_status(uuid.UUID(args.task_id)))
    elif args.command == "logs":
        asyncio.run(cli.get_logs(uuid.UUID(args.task_id), args.limit))


if __name__ == "__main__":
    main()
