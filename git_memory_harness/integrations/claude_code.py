import json
import sys
from pathlib import Path


def install_hook() -> None:
    cmd = f"{sys.executable} -m git_memory_harness.cli hook"
    settings_path = Path("~/.claude/settings.json").expanduser()
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    hooks = data.setdefault("hooks", {})
    existing = hooks.setdefault("UserPromptSubmit", [])
    for entry in existing:
        for h in entry.get("hooks", []):
            if h.get("command") == cmd:
                return
    existing.append({"hooks": [{"type": "command", "command": cmd}]})
    settings_path.write_text(json.dumps(data, indent=2))
