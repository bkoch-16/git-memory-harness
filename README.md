# git-memory-harness

A Python package that gives AI coding agents (Claude Code, OpenCode) persistent, branch-scoped memory backed by Zep Cloud. Each git branch gets its own Zep session. Designed to allow switching between providers. Claude Code gets automatic memory injection via `UserPromptSubmit` hooks; OpenCode gets explicit recall/remember MCP tools. Turns are buffered on disk with a two-phase commit for crash safety.

## How it works

- **Branch-scoped sessions** — namespace is `repo-id/branch`, so memory is isolated per branch and never bleeds across contexts
- **Disk buffer with crash safety** — turns accumulate locally and flush to Zep in batches of 5 via atomic write (`.tmp` + `os.replace`) and two-phase commit
- **Claude Code** — automatic via `UserPromptSubmit` hook: ingests transcript incrementally and injects relevant memories as an additional system prompt on every turn
- **OpenCode** — explicit MCP tools (`recall_memories`, `remember_fact`) via a stdio server; `remember_fact` flushes immediately for durability

## Installation

```sh
pip install -e .
```

Run once to store your Zep API key and wire up integrations:

```sh
git-memory-harness setup
```

Other commands:

```sh
git-memory-harness status   # show namespace and buffer state
git-memory-harness hook     # Claude Code hook entrypoint (called automatically)
```

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
