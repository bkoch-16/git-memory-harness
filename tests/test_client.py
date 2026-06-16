import os
from unittest.mock import MagicMock, patch

import pytest

import git_memory_harness.client as client_mod
from git_memory_harness.client import _reset_client, get_api_key, get_client


@pytest.fixture(autouse=True)
def reset():
    _reset_client()
    yield
    _reset_client()


def test_env_var_takes_precedence(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "env-key")
    with patch("keyring.get_password", return_value="keyring-key"):
        key = get_api_key()
    assert key == "env-key"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MEM0_API_KEY", raising=False)
    with patch("keyring.get_password", return_value=None):
        with pytest.raises(RuntimeError, match="setup"):
            get_api_key()


def test_client_resettable(monkeypatch):
    monkeypatch.setenv("MEM0_API_KEY", "test-key")
    mock_instance = MagicMock()
    with patch("git_memory_harness.client.MemoryClient", return_value=mock_instance):
        client1 = get_client()
        assert client1 is mock_instance

        _reset_client()
        mock_instance2 = MagicMock()
        with patch("git_memory_harness.client.MemoryClient", return_value=mock_instance2):
            client2 = get_client()
            assert client2 is mock_instance2
            assert client2 is not client1
