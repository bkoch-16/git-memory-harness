import json
import sys
from pathlib import Path


def install_hooks() -> None:
    exe = sys.executable
    settings_path = Path("~/.claude/settings.json").expanduser()
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    hooks = data.setdefault("hooks", {})

    prompt_cmd = f"{exe} -m git_memory_harness.cli hook"
    existing_prompt = hooks.setdefault("UserPromptSubmit", [])
    if not any(
        h.get("command") == prompt_cmd
        for entry in existing_prompt
        for h in entry.get("hooks", [])
    ):
        existing_prompt.append({"hooks": [{"type": "command", "command": prompt_cmd}]})

    session_cmd = f"{exe} -m git_memory_harness.cli session-start"
    existing_session = hooks.setdefault("SessionStart", [])
    if not any(
        h.get("command") == session_cmd
        for entry in existing_session
        for h in entry.get("hooks", [])
    ):
        existing_session.append({"hooks": [{"type": "command", "command": session_cmd}]})

    settings_path.write_text(json.dumps(data, indent=2))


# Keep old name working for any external callers
install_hook = install_hooks
