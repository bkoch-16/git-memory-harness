import os

import keyring
from mem0 import MemoryClient

_client: MemoryClient | None = None


def _reset_client() -> None:
    global _client
    _client = None


def get_api_key() -> str:
    key = os.environ.get("MEM0_API_KEY")
    if key:
        return key
    key = keyring.get_password("git-memory-harness", "mem0_api_key")
    if key:
        return key
    raise RuntimeError(
        "No mem0 API key. Run 'git-memory-harness setup' or set MEM0_API_KEY."
    )


def get_client() -> MemoryClient:
    global _client
    if _client is None:
        _client = MemoryClient(api_key=get_api_key())
    return _client
