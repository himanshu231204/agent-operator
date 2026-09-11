from __future__ import annotations

import pytest

from app.errors import ToolError
from app.tools.builtin.shell import ShellRunInput, ShellRunTool


async def test_shell_run_captures_stdout():
    tool = ShellRunTool()
    result = await tool(ShellRunInput(command="echo hello"))
    assert "hello" in result.stdout
    assert result.exit_code == 0
    assert result.success is True


async def test_shell_run_captures_stderr_and_nonzero_exit():
    tool = ShellRunTool()
    result = await tool(ShellRunInput(command="ls /path/that/does/not/exist/xyz123"))
    assert result.exit_code != 0
    assert result.success is False


async def test_shell_run_blocks_sudo():
    tool = ShellRunTool()
    with pytest.raises(ToolError, match="blocked"):
        await tool(ShellRunInput(command="sudo ls"))


async def test_shell_run_blocks_rm_rf_root():
    tool = ShellRunTool()
    with pytest.raises(ToolError, match="blocked"):
        await tool(ShellRunInput(command="rm -rf /"))


async def test_shell_run_with_working_dir(tmp_path):
    (tmp_path / "sentinel.txt").write_text("x")
    tool = ShellRunTool()
    result = await tool(ShellRunInput(command="ls", working_dir=str(tmp_path)))
    assert "sentinel.txt" in result.stdout
    assert result.success is True


async def test_shell_run_timeout_raises():
    tool = ShellRunTool()
    with pytest.raises(ToolError, match="timed out"):
        await tool(ShellRunInput(command="sleep 60", timeout_seconds=0.1))
