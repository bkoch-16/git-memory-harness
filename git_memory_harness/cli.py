import json
import sys

import click
import keyring

from git_memory_harness import client as _client_mod
from git_memory_harness.memory import flush, ingest_transcript, recall
from git_memory_harness.repo import get_repo_id, get_run_id, get_user_id


@click.group()
def main() -> None:
    pass


@main.command()
def setup() -> None:
    """Store mem0 API key and install integrations."""
    existing = keyring.get_password("git-memory-harness", "mem0_api_key")
    if existing:
        overwrite = click.confirm("API key already stored. Overwrite?", default=False)
        if not overwrite:
            click.echo("Keeping existing key.")
        else:
            key = click.prompt("mem0 API key", hide_input=True)
            keyring.set_password("git-memory-harness", "mem0_api_key", key)
    else:
        key = click.prompt("mem0 API key", hide_input=True)
        keyring.set_password("git-memory-harness", "mem0_api_key", key)

    try:
        _client_mod.get_client().get_all(filters={"user_id": get_user_id()}, limit=1)
    except Exception as e:
        click.echo(f"Failed to verify API key: {e}", err=True)
        sys.exit(1)

    installed = []

    from pathlib import Path
    if Path("~/.claude").expanduser().exists():
        from git_memory_harness.integrations.claude_code import install_hook
        install_hook()
        installed.append("Claude Code hook (~/.claude/settings.json)")

    from git_memory_harness.integrations.opencode import _find_opencode_config, install_mcp
    config_path = _find_opencode_config()
    if config_path:
        install_mcp(config_path)
        installed.append(f"OpenCode MCP ({config_path})")

    click.echo("Setup complete.")
    for item in installed:
        click.echo(f"  + {item}")
    if not installed:
        click.echo("  (no integrations detected)")


@main.command()
def status() -> None:
    """Show current namespace and buffer state."""
    from git_memory_harness.memory import _buffer_file, _load_buffer
    try:
        run_id = get_run_id()
        user_id = get_user_id()
        repo_id = get_repo_id()
    except Exception as e:
        click.echo(f"Error reading git state: {e}", err=True)
        sys.exit(1)

    click.echo(f"run_id:  {run_id}")
    click.echo(f"user_id: {user_id}")
    click.echo(f"repo_id: {repo_id}")

    try:
        buf = _load_buffer()
        click.echo(f"turns:   {len(buf.get('turns', []))}")
        click.echo(f"pending: {len(buf.get('pending_turns', []))}")
        click.echo(f"offset:  {buf.get('transcript_line_offset', 0)}")
    except Exception:
        click.echo("buffer:  (not initialized)")


@main.command()
def hook() -> None:
    """Claude Code UserPromptSubmit hook entrypoint."""
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(f"[git-memory-harness] ERROR parsing hook payload: {e}", file=sys.stderr)
        print(json.dumps({"continue": True}))
        return

    try:
        if "prompt" in payload and "transcript_path" in payload:
            ingest_transcript(payload["transcript_path"])
            memories = recall(payload["prompt"])
            if memories:
                out = {
                    "continue": True,
                    "hookSpecificOutput": {"additionalSystemPrompt": memories},
                }
            else:
                out = {"continue": True}
        else:
            out = {}
    except Exception as e:
        print(f"[git-memory-harness] ERROR in hook: {e}", file=sys.stderr)
        out = {"continue": True}

    print(json.dumps(out))
