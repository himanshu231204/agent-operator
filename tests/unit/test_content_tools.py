"""Unit tests for content tools (Phase 5).

No mocking needed: both tools call validate_content() which is pure Python.
"""
from __future__ import annotations

from app.schemas.content import ContentDraftToolInput, ContentValidateToolInput

# ---------------------------------------------------------------------------
# ContentValidateTool
# ---------------------------------------------------------------------------

async def test_validate_tool_valid_x_content():
    from app.tools.builtin.content import ContentValidateTool
    tool = ContentValidateTool()
    result = await tool.execute(ContentValidateToolInput(platform="x", content="Hello world"))
    assert result.valid is True
    assert result.issues == []

async def test_validate_tool_x_over_limit():
    from app.tools.builtin.content import ContentValidateTool
    tool = ContentValidateTool()
    result = await tool.execute(ContentValidateToolInput(platform="x", content="a" * 281))
    assert result.valid is False
    assert any(i.check == "length" for i in result.issues)

async def test_validate_tool_linkedin_long_content_ok():
    from app.tools.builtin.content import ContentValidateTool
    tool = ContentValidateTool()
    result = await tool.execute(ContentValidateToolInput(platform="linkedin", content="a" * 500))
    assert result.valid is True

async def test_validate_tool_malformed_link():
    from app.tools.builtin.content import ContentValidateTool
    tool = ContentValidateTool()
    result = await tool.execute(ContentValidateToolInput(platform="linkedin", content="See https://bad url here"))
    assert result.valid is False
    assert any(i.check == "links" for i in result.issues)

def test_validate_tool_metadata():
    from app.policies.risk import RiskLevel
    from app.tools.builtin.content import ContentValidateTool
    tool = ContentValidateTool()
    assert tool.name == "content_validate"
    assert tool.permissions.risk_level == RiskLevel.LOW
    assert tool.permissions.requires_approval is False
    assert tool.timeout_seconds == 5.0


# ---------------------------------------------------------------------------
# ContentDraftTool — happy paths
# ---------------------------------------------------------------------------

async def test_draft_tool_valid_short_x_content():
    from app.tools.builtin.content import ContentDraftTool
    tool = ContentDraftTool()
    result = await tool.execute(ContentDraftToolInput(platform="x", content="Short post.", tone="casual"))
    assert result.valid is True
    assert result.thread_posts == []
    assert result.formatted_content == "Short post."

async def test_draft_tool_valid_linkedin_content():
    from app.tools.builtin.content import ContentDraftTool
    tool = ContentDraftTool()
    result = await tool.execute(ContentDraftToolInput(platform="linkedin", content="A valid LinkedIn post.", tone="professional"))
    assert result.valid is True
    assert result.thread_posts == []
    assert result.formatted_content == "A valid LinkedIn post."

# ---------------------------------------------------------------------------
# ContentDraftTool — X thread splitting
# ---------------------------------------------------------------------------

async def test_draft_tool_long_x_content_splits_into_thread():
    """Multi-sentence content >280 chars splits into numbered thread posts."""
    from app.tools.builtin.content import ContentDraftTool
    # 13 sentences × 25 chars = 325 chars total
    content = "This is a test sentence. " * 13
    content = content.strip()
    tool = ContentDraftTool()
    result = await tool.execute(ContentDraftToolInput(platform="x", content=content, tone="educational"))
    assert result.valid is True
    assert len(result.thread_posts) >= 2
    for post in result.thread_posts:
        assert post.index == result.thread_posts.index(post) + 1
        assert post.total == len(result.thread_posts)
        assert len(post.content) <= 280
        assert f" {post.index}/{post.total}" in post.content

async def test_draft_tool_thread_formatted_content_is_newline_joined():
    from app.tools.builtin.content import ContentDraftTool
    content = ("This is a medium length sentence here. " * 9).strip()
    tool = ContentDraftTool()
    result = await tool.execute(ContentDraftToolInput(platform="x", content=content, tone="professional"))
    assert result.valid is True
    assert len(result.thread_posts) >= 2
    expected = "\n\n".join(p.content for p in result.thread_posts)
    assert result.formatted_content == expected

async def test_draft_tool_unsplittable_x_content_returns_invalid():
    """Content >280 chars with no sentence boundaries cannot thread-split — returns length error."""
    from app.tools.builtin.content import ContentDraftTool
    tool = ContentDraftTool()
    result = await tool.execute(ContentDraftToolInput(platform="x", content="a" * 290, tone="casual"))
    assert result.valid is False
    assert any(i.check == "length" for i in result.issues)
    assert result.thread_posts == []

def test_draft_tool_metadata():
    from app.policies.risk import RiskLevel
    from app.tools.builtin.content import ContentDraftTool
    tool = ContentDraftTool()
    assert tool.name == "content_draft"
    assert tool.permissions.risk_level == RiskLevel.MEDIUM
    assert tool.permissions.requires_approval is False
