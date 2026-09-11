from __future__ import annotations

import pytest

from app.errors import ToolError
from app.tools.builtin.filesystem import (
    FileDeleteInput,
    FileDeleteTool,
    FileEditInput,
    FileEditTool,
    FileReadInput,
    FileReadTool,
    FileWriteInput,
    FileWriteTool,
    FolderCreateInput,
    FolderCreateTool,
    FolderDeleteInput,
    FolderDeleteTool,
    FolderListInput,
    FolderListTool,
    _guard_path,
)

# --- _guard_path ---

def test_guard_path_blocks_env_file(tmp_path):
    with pytest.raises(ToolError, match="credential"):
        _guard_path(tmp_path / ".env")

def test_guard_path_blocks_env_local(tmp_path):
    with pytest.raises(ToolError, match="credential"):
        _guard_path(tmp_path / ".env.local")

def test_guard_path_allows_normal_file(tmp_path):
    _guard_path(tmp_path / "main.py")  # must not raise


# --- FileReadTool ---

async def test_file_read_returns_content(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    tool = FileReadTool()
    result = await tool(FileReadInput(path=str(f)))
    assert result.content == "hello world"
    assert result.size_bytes == 11

async def test_file_read_missing_raises(tmp_path):
    tool = FileReadTool()
    with pytest.raises(ToolError, match="not found"):
        await tool(FileReadInput(path=str(tmp_path / "missing.txt")))


# --- FileWriteTool ---

async def test_file_write_creates_new_file(tmp_path):
    path = tmp_path / "out.txt"
    tool = FileWriteTool()
    result = await tool(FileWriteInput(path=str(path), content="hi"))
    assert result.created is True
    assert path.read_text() == "hi"

async def test_file_write_overwrites_existing(tmp_path):
    path = tmp_path / "out.txt"
    path.write_text("old")
    tool = FileWriteTool()
    result = await tool(FileWriteInput(path=str(path), content="new"))
    assert result.created is False
    assert path.read_text() == "new"

async def test_file_write_creates_parent_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "file.txt"
    tool = FileWriteTool()
    await tool(FileWriteInput(path=str(path), content="nested"))
    assert path.read_text() == "nested"


# --- FileEditTool ---

async def test_file_edit_replaces_string(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("foo = 1\nbar = 2\n")
    tool = FileEditTool()
    result = await tool(FileEditInput(path=str(f), old_string="foo = 1", new_string="foo = 99"))
    assert result.replacements == 1
    assert "foo = 99" in f.read_text()

async def test_file_edit_raises_if_old_string_not_found(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("foo = 1")
    tool = FileEditTool()
    with pytest.raises(ToolError, match="not found"):
        await tool(FileEditInput(path=str(f), old_string="MISSING", new_string="x"))


# --- FileDeleteTool ---

async def test_file_delete_removes_file(tmp_path):
    f = tmp_path / "del.txt"
    f.write_text("bye")
    tool = FileDeleteTool()
    result = await tool(FileDeleteInput(path=str(f)))
    assert result.deleted is True
    assert not f.exists()

async def test_file_delete_raises_if_missing(tmp_path):
    tool = FileDeleteTool()
    with pytest.raises(ToolError, match="not found"):
        await tool(FileDeleteInput(path=str(tmp_path / "ghost.txt")))


# --- FolderCreateTool ---

async def test_folder_create_makes_dirs(tmp_path):
    path = tmp_path / "a" / "b" / "c"
    tool = FolderCreateTool()
    result = await tool(FolderCreateInput(path=str(path)))
    assert result.created is True
    assert path.is_dir()


# --- FolderListTool ---

async def test_folder_list_returns_entries(tmp_path):
    (tmp_path / "file.txt").write_text("x")
    (tmp_path / "subdir").mkdir()
    tool = FolderListTool()
    result = await tool(FolderListInput(path=str(tmp_path)))
    names = [e["name"] for e in result.entries]
    assert "file.txt" in names
    assert "subdir" in names

async def test_folder_list_hides_hidden_by_default(tmp_path):
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / "visible.txt").write_text("y")
    tool = FolderListTool()
    result = await tool(FolderListInput(path=str(tmp_path)))
    names = [e["name"] for e in result.entries]
    assert ".hidden" not in names
    assert "visible.txt" in names


# --- FolderDeleteTool ---

async def test_folder_delete_removes_empty_dir(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    tool = FolderDeleteTool()
    result = await tool(FolderDeleteInput(path=str(d)))
    assert result.deleted is True
    assert not d.exists()

async def test_folder_delete_recursive(tmp_path):
    d = tmp_path / "full"
    d.mkdir()
    (d / "file.txt").write_text("x")
    tool = FolderDeleteTool()
    result = await tool(FolderDeleteInput(path=str(d), recursive=True))
    assert result.deleted is True
    assert not d.exists()
