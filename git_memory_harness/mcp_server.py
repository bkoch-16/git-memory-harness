import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from git_memory_harness.memory import flush, recall, remember

app = Server("git-memory-harness")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="recall_memories",
            description="Fetch relevant memories for the current git branch",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        Tool(
            name="remember_fact",
            description="Store an important fact or decision in memory for this branch",
            inputSchema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
        ),
    ]


async def _dispatch(name: str, arguments: dict) -> list[dict]:
    if name == "recall_memories":
        result = await asyncio.to_thread(recall, arguments["query"])
        return [{"type": "text", "text": result}]
    elif name == "remember_fact":
        await asyncio.to_thread(remember, "user", arguments["content"])
        await asyncio.to_thread(flush)
        return [{"type": "text", "text": "Stored."}]
    else:
        return [{"type": "text", "text": f"Unknown tool: {name}"}]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[dict]:
    return await _dispatch(name, arguments)


if __name__ == "__main__":
    asyncio.run(stdio_server(app))
