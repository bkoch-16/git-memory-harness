from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from git_memory_harness.mcp_server import _dispatch


@pytest.mark.asyncio
async def test_remember_fact_flushes_immediately():
    with (
        patch("git_memory_harness.mcp_server.remember") as mock_remember,
        patch("git_memory_harness.mcp_server.flush") as mock_flush,
    ):
        await _dispatch("remember_fact", {"content": "test content"})
    mock_flush.assert_called_once()


@pytest.mark.asyncio
async def test_remember_fact_uses_user_role():
    with (
        patch("git_memory_harness.mcp_server.remember") as mock_remember,
        patch("git_memory_harness.mcp_server.flush"),
    ):
        await _dispatch("remember_fact", {"content": "some fact"})
    mock_remember.assert_called_once_with("user", "some fact")


@pytest.mark.asyncio
async def test_recall_memories_returns_text_block():
    with patch("git_memory_harness.mcp_server.recall", return_value="some memory"):
        result = await _dispatch("recall_memories", {"query": "what did we decide?"})
    assert result == [{"type": "text", "text": "some memory"}]


@pytest.mark.asyncio
async def test_call_tool_unknown_name():
    result = await _dispatch("nonexistent_tool", {})
    assert len(result) == 1
    assert "Unknown tool" in result[0]["text"]
