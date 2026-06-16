import json
import sys
from pathlib import Path


def _find_opencode_config() -> Path | None:
    p1 = Path("~/.opencode.json").expanduser()
    if p1.exists():
        return p1
    p2 = Path("~/.config/opencode").expanduser()
    if p2.exists():
        return p2 / ".opencode.json"
    return None


def install_mcp(config_path: Path) -> None:
    cmd = sys.executable
    args = ["-m", "git_memory_harness.mcp_server"]
    data = json.loads(config_path.read_text()) if config_path.exists() else {}
    servers = data.setdefault("mcpServers", {})
    if "git-memory-harness" in servers:
        return
    servers["git-memory-harness"] = {"type": "stdio", "command": cmd, "args": args, "env": []}
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2))
