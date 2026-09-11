"""Filesystem tools for the local system agent.

All paths are resolved to absolute and checked against blocked patterns
before any I/O. HIGH-risk tools (delete) require explicit approval.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.errors import ToolError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions

# ---------------------------------------------------------------------------
# Path guard
# ---------------------------------------------------------------------------

_BLOCKED_PATH_FRAGMENTS: tuple[str, ...] = (
    ".git/config",
    ".git\\config",
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "C:\\Windows\\System32",
    "/proc/",
    "/sys/",
)


def _guard_path(path: Path) -> None:
    name = path.name
    if name == ".env" or name.startswith(".env."):
        raise ToolError(
            f"Access to credential files is not allowed: {name!r}",
            context={"path": str(path)},
        )
    path_str = str(path)
    for fragment in _BLOCKED_PATH_FRAGMENTS:
        if fragment in path_str:
            raise ToolError(
                f"Access to {fragment!r} is not permitted",
                context={"path": path_str},
            )


# ---------------------------------------------------------------------------
# FileReadTool
# ---------------------------------------------------------------------------

class FileReadInput(BaseModel):
    path: str
    encoding: str = "utf-8"


class FileReadOutput(BaseModel):
    content: str
    size_bytes: int
    path: str


class FileReadTool(BaseTool[FileReadInput, FileReadOutput]):
    name = "file_read"
    description = "Read the full contents of a local file."
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: FileReadInput) -> FileReadOutput:
        path = Path(tool_input.path).resolve()
        _guard_path(path)
        if not path.exists():
            raise ToolError(f"File not found: {path}", context={"path": str(path)})
        try:
            content = path.read_text(encoding=tool_input.encoding)
        except PermissionError as exc:
            raise ToolError(f"Permission denied: {path}") from exc
        return FileReadOutput(content=content, size_bytes=path.stat().st_size, path=str(path))


# ---------------------------------------------------------------------------
# FileWriteTool
# ---------------------------------------------------------------------------

class FileWriteInput(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"
    create_parents: bool = True


class FileWriteOutput(BaseModel):
    path: str
    bytes_written: int
    created: bool


class FileWriteTool(BaseTool[FileWriteInput, FileWriteOutput]):
    name = "file_write"
    description = (
        "Write content to a file. Creates the file and parent directories if they do not exist."
    )
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    async def execute(self, tool_input: FileWriteInput) -> FileWriteOutput:
        path = Path(tool_input.path).resolve()
        _guard_path(path)
        created = not path.exists()
        if tool_input.create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(tool_input.content, encoding=tool_input.encoding)
        return FileWriteOutput(
            path=str(path),
            bytes_written=len(tool_input.content.encode(tool_input.encoding)),
            created=created,
        )


# ---------------------------------------------------------------------------
# FileEditTool
# ---------------------------------------------------------------------------

class FileEditInput(BaseModel):
    path: str
    old_string: str
    new_string: str
    encoding: str = "utf-8"


class FileEditOutput(BaseModel):
    path: str
    replacements: int


class FileEditTool(BaseTool[FileEditInput, FileEditOutput]):
    name = "file_edit"
    description = "Replace the first occurrence of old_string with new_string in a file."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    async def execute(self, tool_input: FileEditInput) -> FileEditOutput:
        path = Path(tool_input.path).resolve()
        _guard_path(path)
        if not path.exists():
            raise ToolError(f"File not found: {path}", context={"path": str(path)})
        content = path.read_text(encoding=tool_input.encoding)
        if tool_input.old_string not in content:
            raise ToolError(
                "old_string not found in file",
                context={"path": str(path), "old_string_preview": tool_input.old_string[:80]},
            )
        new_content = content.replace(tool_input.old_string, tool_input.new_string, 1)
        path.write_text(new_content, encoding=tool_input.encoding)
        return FileEditOutput(path=str(path), replacements=1)


# ---------------------------------------------------------------------------
# FileDeleteTool
# ---------------------------------------------------------------------------

class FileDeleteInput(BaseModel):
    path: str


class FileDeleteOutput(BaseModel):
    path: str
    deleted: bool


class FileDeleteTool(BaseTool[FileDeleteInput, FileDeleteOutput]):
    name = "file_delete"
    description = "Permanently delete a file from the local filesystem."
    permissions = ToolPermissions(risk_level=RiskLevel.HIGH, requires_approval=True)

    async def execute(self, tool_input: FileDeleteInput) -> FileDeleteOutput:
        path = Path(tool_input.path).resolve()
        _guard_path(path)
        if not path.exists():
            raise ToolError(f"File not found: {path}", context={"path": str(path)})
        path.unlink()
        return FileDeleteOutput(path=str(path), deleted=True)


# ---------------------------------------------------------------------------
# FolderCreateTool
# ---------------------------------------------------------------------------

class FolderCreateInput(BaseModel):
    path: str
    exist_ok: bool = True


class FolderCreateOutput(BaseModel):
    path: str
    created: bool


class FolderCreateTool(BaseTool[FolderCreateInput, FolderCreateOutput]):
    name = "folder_create"
    description = "Create a directory (and all parent directories)."
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: FolderCreateInput) -> FolderCreateOutput:
        path = Path(tool_input.path).resolve()
        _guard_path(path)
        created = not path.exists()
        path.mkdir(parents=True, exist_ok=tool_input.exist_ok)
        return FolderCreateOutput(path=str(path), created=created)


# ---------------------------------------------------------------------------
# FolderListTool
# ---------------------------------------------------------------------------

class FolderListInput(BaseModel):
    path: str
    include_hidden: bool = False


class FolderListOutput(BaseModel):
    path: str
    entries: list[dict[str, Any]]


class FolderListTool(BaseTool[FolderListInput, FolderListOutput]):
    name = "folder_list"
    description = "List the contents of a directory, returning name, type, size, and mtime."
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: FolderListInput) -> FolderListOutput:
        path = Path(tool_input.path).resolve()
        _guard_path(path)
        if not path.is_dir():
            raise ToolError(f"Not a directory: {path}", context={"path": str(path)})
        entries: list[dict[str, Any]] = []
        for entry in sorted(path.iterdir()):
            if not tool_input.include_hidden and entry.name.startswith("."):
                continue
            stat = entry.stat()
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size_bytes": stat.st_size if entry.is_file() else 0,
                "modified": stat.st_mtime,
            })
        return FolderListOutput(path=str(path), entries=entries)


# ---------------------------------------------------------------------------
# FolderDeleteTool
# ---------------------------------------------------------------------------

class FolderDeleteInput(BaseModel):
    path: str
    recursive: bool = False


class FolderDeleteOutput(BaseModel):
    path: str
    deleted: bool


class FolderDeleteTool(BaseTool[FolderDeleteInput, FolderDeleteOutput]):
    name = "folder_delete"
    description = "Delete a directory. Set recursive=True to delete non-empty directories."
    permissions = ToolPermissions(risk_level=RiskLevel.HIGH, requires_approval=True)

    async def execute(self, tool_input: FolderDeleteInput) -> FolderDeleteOutput:
        path = Path(tool_input.path).resolve()
        _guard_path(path)
        if not path.exists():
            raise ToolError(f"Directory not found: {path}", context={"path": str(path)})
        if tool_input.recursive:
            shutil.rmtree(path)
        else:
            path.rmdir()
        return FolderDeleteOutput(path=str(path), deleted=True)
