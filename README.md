# git-memory-harness

A Python package that gives AI coding agents (Claude Code, OpenCode) persistent, branch-scoped memory backed by mem0. Each git branch gets its own strictly isolated mem0 run — memories from one branch never surface on another. Turns are buffered on disk with a two-phase commit for crash safety.

## How it works

- **Branch-scoped sessions** — namespace is `repo-id/branch`, so memory is isolated per branch and never bleeds across contexts
- **Disk buffer with crash safety** — turns accumulate locally and flush to mem0 in batches of 5 via atomic write (`.tmp` + `os.replace`) and two-phase commit
- **Claude Code** — fully automatic via `UserPromptSubmit` hook: ingests transcript incrementally and injects relevant memories as an additional system prompt on every turn; no model involvement required
- **OpenCode** — opt-in via MCP: the `recall_memories` and `remember_fact` tools are registered as an MCP server and OpenCode decides when to invoke them; `remember_fact` flushes immediately for durability

## Installation

```sh
pip install -e .
```

Run once to store your mem0 API key and wire up Claude Code hooks (or set `MEM0_API_KEY` in your environment to skip the keychain):

```sh
git-memory-harness setup
```

Other commands:

```sh
git-memory-harness status   # show namespace and buffer state
git-memory-harness hook     # Claude Code hook entrypoint (called automatically)
```

### OpenCode setup

Add the MCP server to `~/.config/opencode/config.json`:

```json
{
  "mcp": {
    "git-memory-harness": {
      "type": "local",
      "command": ["/path/to/venv/bin/python3", "-m", "git_memory_harness.mcp_server"]
    }
  }
}
```

Once registered, OpenCode will have `recall_memories` and `remember_fact` available as tools. Whether and when it calls them is up to the model — you can prompt it explicitly (e.g. "recall your memories for this project") or rely on it invoking them autonomously.

## File structure

```
git-memory-harness/
├── pyproject.toml
├── git_memory_harness/
│   ├── __init__.py
│   ├── client.py
│   ├── repo.py
│   ├── memory.py
│   ├── mcp_server.py
│   ├── cli.py
│   └── integrations/
│       ├── __init__.py
│       ├── claude_code.py
│       └── opencode.py
└── tests/
    ├── test_repo.py
    ├── test_memory.py
    ├── test_client.py
    └── test_mcp_server.py
```
