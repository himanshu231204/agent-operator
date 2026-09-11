"""Shell execution tool for the local system agent.

Runs commands via asyncio subprocess with a configurable timeout.
Blocks a hardcoded set of dangerous patterns before any subprocess is spawned.
"""
from __future__ import annotations

import asyncio

from pydantic import BaseModel

from app.errors import ToolError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions

_BLOCKED_PATTERNS: tuple[str, ...] = (
    "rm -rf /",
    "sudo",
    ":(){ :|:& };:",  # fork bomb
    "dd if=",
    "mkfs",
    "> /dev/",
    "chmod 777 /",
    "chown root",
)


class ShellRunInput(BaseModel):
    command: str
    working_dir: str | None = None
    timeout_seconds: float = 30.0


class ShellRunOutput(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    success: bool


class ShellRunTool(BaseTool[ShellRunInput, ShellRunOutput]):
    name = "shell_run"
    description = (
        "Execute a shell command and return stdout, stderr, exit code, and success flag."
    )
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    async def execute(self, tool_input: ShellRunInput) -> ShellRunOutput:
        cmd = tool_input.command
        for pattern in _BLOCKED_PATTERNS:
            if pattern in cmd:
                raise ToolError(
                    f"Command contains blocked pattern: {pattern!r}",
                    context={"command": cmd, "blocked_pattern": pattern},
                )

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tool_input.working_dir,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=tool_input.timeout_seconds
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            raise ToolError(
                f"Command timed out after {tool_input.timeout_seconds}s",
                context={"command": cmd},
            )

        return ShellRunOutput(
            stdout=stdout_bytes.decode(errors="replace"),
            stderr=stderr_bytes.decode(errors="replace"),
            exit_code=proc.returncode,
            success=proc.returncode == 0,
        )
