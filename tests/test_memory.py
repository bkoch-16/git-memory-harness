import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import git_memory_harness.memory as memory_mod
from git_memory_harness.memory import (
    _empty_buffer,
    _load_buffer,
    _save_buffer,
    flush,
    ingest_transcript,
    remember,
)


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(memory_mod, "get_git_dir", lambda: tmp_path)
    monkeypatch.setattr(memory_mod, "get_run_id", lambda: "test-repo/main")
    monkeypatch.setattr(memory_mod, "get_user_id", lambda: "test-user")


def _write_buffer(tmp_path, buf):
    path = tmp_path / "git-memory-harness-buffer.json"
    path.write_text(json.dumps(buf))


def test_turns_preserved_on_flush_failure(tmp_path):
    buf = _empty_buffer("test-repo/main")
    for i in range(5):
        buf["turns"].append({"role": "user", "content": f"turn {i}"})
    _write_buffer(tmp_path, buf)

    mock_client = MagicMock()
    mock_client.add.side_effect = RuntimeError("network error")

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        flush()

    loaded = _load_buffer()
    assert len(loaded["turns"]) == 5
    assert loaded["pending_turns"] == []


def test_turns_cleared_on_flush_success(tmp_path):
    buf = _empty_buffer("test-repo/main")
    for i in range(3):
        buf["turns"].append({"role": "user", "content": f"turn {i}"})
    _write_buffer(tmp_path, buf)

    mock_client = MagicMock()
    mock_client.add.return_value = {}

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        flush()

    loaded = _load_buffer()
    assert loaded["turns"] == []
    assert loaded["pending_turns"] == []


def test_flush_recovers_pending_from_crash(tmp_path):
    buf = _empty_buffer("test-repo/main")
    buf["pending_turns"] = [
        {"role": "user", "content": "A"},
        {"role": "user", "content": "B"},
    ]
    buf["turns"] = [{"role": "user", "content": "C"}]
    _write_buffer(tmp_path, buf)

    captured = {}
    mock_client = MagicMock()
    def capture_add(turns, **kwargs):
        captured["turns"] = turns
        return {}
    mock_client.add.side_effect = capture_add

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        flush()

    assert len(captured["turns"]) == 3
    loaded = _load_buffer()
    assert loaded["pending_turns"] == []
    assert loaded["turns"] == []


def test_batch_threshold(tmp_path):
    mock_client = MagicMock()
    mock_client.add.return_value = {}

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        for i in range(4):
            remember("user", f"turn {i}")
        assert mock_client.add.call_count == 0

        remember("user", "turn 4")
        assert mock_client.add.call_count == 1


def test_branch_switch_flushes_old_run(tmp_path, monkeypatch):
    buf = _empty_buffer("test-repo/old-branch")
    buf["turns"] = [{"role": "user", "content": "old work"}]
    _write_buffer(tmp_path, buf)

    monkeypatch.setattr(memory_mod, "get_run_id", lambda: "test-repo/new-branch")

    mock_client = MagicMock()
    mock_client.add.return_value = {}

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        remember("user", "new work")

    mock_client.add.assert_called_once()
    assert mock_client.add.call_args.kwargs.get("run_id") == "test-repo/old-branch"

    loaded = _load_buffer()
    assert loaded["run_id"] == "test-repo/new-branch"


def test_no_deadlock_in_ingest(tmp_path):
    lines = []
    for i in range(3):
        lines.append(json.dumps({"type": "user", "message": {"content": f"user {i}"}}))
        lines.append(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": f"reply {i}"}]}}))

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(lines) + "\n")

    written: list = []
    mock_client = MagicMock()
    def capture_add(turns, **kwargs):
        written.extend(turns)
        return {}
    mock_client.add.side_effect = capture_add

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        ingest_transcript(str(transcript))

    loaded = _load_buffer()
    total = len(loaded["turns"]) + len(loaded["pending_turns"]) + len(written)
    assert total == 6


def test_ingest_incremental_offset(tmp_path):
    lines_6 = [
        json.dumps({"type": "user", "message": {"content": f"u{i}"}})
        for i in range(6)
    ]
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(lines_6) + "\n")

    mock_client = MagicMock()
    mock_client.add.return_value = {}

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        ingest_transcript(str(transcript))

    loaded = _load_buffer()
    assert loaded["transcript_line_offset"] == 6

    lines_8 = lines_6 + [
        json.dumps({"type": "user", "message": {"content": f"u{i}"}})
        for i in range(6, 8)
    ]
    transcript.write_text("\n".join(lines_8) + "\n")

    with patch("git_memory_harness.memory.get_client", return_value=mock_client):
        ingest_transcript(str(transcript))

    loaded = _load_buffer()
    assert loaded["transcript_line_offset"] == 8


def test_ingest_skips_tool_result_messages(tmp_path):
    lines = [
        json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "data"}]}}),
    ]
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(lines) + "\n")

    ingest_transcript(str(transcript))

    loaded = _load_buffer()
    assert loaded["turns"] == []


def test_ingest_skips_thinking_blocks(tmp_path):
    lines = [
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "thinking", "thinking": "..."},
            {"type": "text", "text": "hello"},
        ]}}),
    ]
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(lines) + "\n")

    ingest_transcript(str(transcript))

    loaded = _load_buffer()
    assert len(loaded["turns"]) == 1
    assert loaded["turns"][0]["content"] == "hello"


def test_ingest_resets_offset_on_new_transcript_path(tmp_path):
    # Seed buffer with a high offset from a previous transcript path
    old_buf = _empty_buffer("test-repo/main")
    old_buf["transcript_path"] = "/old/path/transcript.jsonl"
    old_buf["transcript_line_offset"] = 999
    _write_buffer(tmp_path, old_buf)

    lines = [json.dumps({"type": "user", "message": {"content": "new session turn"}})]
    new_transcript = tmp_path / "new_transcript.jsonl"
    new_transcript.write_text("\n".join(lines) + "\n")

    ingest_transcript(str(new_transcript))

    loaded = _load_buffer()
    assert loaded["transcript_path"] == str(new_transcript)
    assert loaded["transcript_line_offset"] == 1
    assert any(t["content"] == "new session turn" for t in loaded["turns"])


def test_ingest_survives_malformed_line(tmp_path):
    lines = [
        "not valid json{{{",
        json.dumps({"type": "user", "message": {"content": "good line"}}),
    ]
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(lines) + "\n")

    ingest_transcript(str(transcript))

    loaded = _load_buffer()
    assert len(loaded["turns"]) == 1
    assert loaded["turns"][0]["content"] == "good line"
