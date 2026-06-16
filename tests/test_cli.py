import json
from unittest.mock import patch

from click.testing import CliRunner

from git_memory_harness.cli import hook


def test_hook_flushes_after_ingest():
    runner = CliRunner()
    payload = json.dumps({"prompt": "hello", "transcript_path": "/tmp/t.jsonl"})
    with (
        patch("git_memory_harness.cli.ingest_transcript") as mock_ingest,
        patch("git_memory_harness.cli.flush") as mock_flush,
        patch("git_memory_harness.cli.recall", return_value=""),
    ):
        result = runner.invoke(hook, input=payload)

    assert result.exit_code == 0
    mock_ingest.assert_called_once_with("/tmp/t.jsonl")
    mock_flush.assert_called_once()


def test_hook_flush_called_before_recall():
    call_order = []
    runner = CliRunner()
    payload = json.dumps({"prompt": "hello", "transcript_path": "/tmp/t.jsonl"})
    with (
        patch("git_memory_harness.cli.ingest_transcript", side_effect=lambda p: call_order.append("ingest")),
        patch("git_memory_harness.cli.flush", side_effect=lambda: call_order.append("flush")),
        patch("git_memory_harness.cli.recall", side_effect=lambda q: call_order.append("recall") or ""),
    ):
        runner.invoke(hook, input=payload)

    assert call_order == ["ingest", "flush", "recall"]


def test_hook_missing_fields_skips_flush():
    runner = CliRunner()
    payload = json.dumps({"other": "data"})
    with (
        patch("git_memory_harness.cli.ingest_transcript") as mock_ingest,
        patch("git_memory_harness.cli.flush") as mock_flush,
        patch("git_memory_harness.cli.recall") as mock_recall,
    ):
        result = runner.invoke(hook, input=payload)

    assert result.exit_code == 0
    mock_ingest.assert_not_called()
    mock_flush.assert_not_called()
    mock_recall.assert_not_called()
