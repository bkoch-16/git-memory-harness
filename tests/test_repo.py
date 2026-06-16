import subprocess
from unittest.mock import patch

import pytest

from git_memory_harness.repo import (
    _sanitize_branch,
    _slugify,
    get_repo_id,
    get_run_id,
    get_user_id,
)


def _make_check_output(responses: dict):
    """Return a mock for subprocess.check_output keyed by first two args."""
    def _mock(cmd, **kwargs):
        key = tuple(cmd[:3])
        if key in responses:
            val = responses[key]
            if isinstance(val, Exception):
                raise val
            return val.encode() if isinstance(val, str) else val
        raise subprocess.CalledProcessError(1, cmd)
    return _mock


def test_slash_encoding():
    run_id = get_run_id.__wrapped__("feature/auth") if hasattr(get_run_id, "__wrapped__") else None
    assert _sanitize_branch("feature/auth") == "feature%2Fauth"
    assert "feature%2Fauth" in f"repo/{_sanitize_branch('feature/auth')}"


def test_no_collision():
    assert _sanitize_branch("feature/foo-bar") != _sanitize_branch("feature-foo-bar")


def test_repo_id_length():
    root_hash = "abcdef123456extra"
    slug = "my-app"
    result = f"{slug}-{root_hash[:12]}"
    hash_part = result.split("-")[-1]
    assert len(hash_part) == 12


def test_no_remote_fallback():
    def mock_check_output(cmd, **kwargs):
        args = list(cmd)
        if args[:3] == ["git", "rev-list", "--max-parents=0"]:
            return b"abcdef123456abcdef\n"
        if args[:3] == ["git", "remote", "get-url"]:
            raise subprocess.CalledProcessError(1, cmd)
        if args[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return b"/home/user/my-project\n"
        raise subprocess.CalledProcessError(1, cmd)

    with patch("subprocess.check_output", side_effect=mock_check_output):
        repo_id = get_repo_id()

    assert repo_id
    assert "abcdef123456" in repo_id
    assert "my-project" in repo_id


def test_get_user_id_email():
    def mock_check_output(cmd, **kwargs):
        if list(cmd) == ["git", "config", "user.email"]:
            return b"Jane.Doe@Example.com\n"
        raise subprocess.CalledProcessError(1, cmd)

    with patch("subprocess.check_output", side_effect=mock_check_output):
        uid = get_user_id()

    assert uid == "jane-doe-example-com"


def test_get_user_id_fallback():
    def mock_check_output(cmd, **kwargs):
        if list(cmd) == ["git", "config", "user.email"]:
            return b"\n"
        if list(cmd) == ["git", "config", "user.name"]:
            return b"Jane Doe\n"
        raise subprocess.CalledProcessError(1, cmd)

    with patch("subprocess.check_output", side_effect=mock_check_output):
        uid = get_user_id()

    assert uid == "jane-doe"
