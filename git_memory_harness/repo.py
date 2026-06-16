import hashlib
import json
import re
import subprocess
from pathlib import Path


def _slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9-]", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def _remote_slug() -> str:
    """Return slugified final path component of origin URL, or toplevel dirname as fallback."""
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        name = re.split(r"[:/]", url.rstrip("/"))[-1]
        name = re.sub(r"\.git$", "", name)
        return _slugify(name) or "repo"
    except subprocess.CalledProcessError:
        toplevel = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return _slugify(Path(toplevel).name) or "repo"


def get_branch() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    ).decode().strip()


def _sanitize_branch(b: str) -> str:
    return b.replace("/", "%2F")


def get_repo_id() -> str:
    try:
        root_hash = subprocess.check_output(
            ["git", "rev-list", "--max-parents=0", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()[:12]
        slug = _remote_slug()
        return f"{slug}-{root_hash}"
    except subprocess.CalledProcessError:
        try:
            toplevel = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
        except subprocess.CalledProcessError:
            toplevel = str(Path.cwd())
        hash12 = hashlib.sha256(toplevel.encode()).hexdigest()[:12]
        slug = _slugify(Path(toplevel).name) or "repo"
        return f"{slug}-{hash12}"


def get_user_id() -> str:
    email = subprocess.check_output(["git", "config", "user.email"]).decode().strip()
    if email:
        return _slugify(email)
    name = subprocess.check_output(["git", "config", "user.name"]).decode().strip()
    return _slugify(name) or "user"


def get_run_id() -> str:
    return f"{get_repo_id()}/{_sanitize_branch(get_branch())}"


def get_git_dir() -> Path:
    return Path(
        subprocess.check_output(["git", "rev-parse", "--git-dir"]).decode().strip()
    )


def get_config() -> dict:
    path = get_git_dir() / "git-memory-harness.json"
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def write_config(data: dict) -> None:
    path = get_git_dir() / "git-memory-harness.json"
    path.write_text(json.dumps(data, indent=2))
