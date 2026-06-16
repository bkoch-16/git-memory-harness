import json
import os
import sys
from pathlib import Path

from filelock import FileLock

from git_memory_harness.client import get_client
from git_memory_harness.repo import get_git_dir, get_run_id, get_user_id

BATCH_SIZE = 5


def _buffer_file() -> Path:
    return get_git_dir() / "git-memory-harness-buffer.json"


def _lock_file() -> Path:
    return get_git_dir() / "git-memory-harness-buffer.json.lock"


def _empty_buffer(run_id: str) -> dict:
    return {
        "run_id": run_id,
        "transcript_path": "",
        "transcript_line_offset": 0,
        "turns": [],
        "pending_turns": [],
    }


def _load_buffer() -> dict:
    try:
        return json.loads(_buffer_file().read_text())
    except (OSError, json.JSONDecodeError):
        return _empty_buffer(get_run_id())


def _save_buffer(buf: dict) -> None:
    path = _buffer_file()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(buf))
    os.replace(tmp, path)


def _append_turn(buf: dict, role: str, content: str) -> None:
    buf["turns"].append({"role": role, "content": content})


def _best_effort_write(run_id: str, turns: list) -> None:
    try:
        get_client().add(
            turns,
            user_id=get_user_id(),
            run_id=run_id,
        )
    except Exception as e:
        print(f"[git-memory-harness] ERROR writing old branch to mem0: {e}", file=sys.stderr)


def _flush_turns(run_id: str, turns: list) -> None:
    success = False
    try:
        get_client().add(
            turns,
            user_id=get_user_id(),
            run_id=run_id,
        )
        success = True
    except Exception as e:
        print(f"[git-memory-harness] ERROR flushing to mem0: {e}", file=sys.stderr)

    with FileLock(_lock_file()):
        buf = _load_buffer()
        if success:
            buf["pending_turns"] = []
        else:
            buf["turns"] = buf.get("pending_turns", []) + buf["turns"]
            buf["pending_turns"] = []
        _save_buffer(buf)


def _format_results(results) -> str:
    if not results:
        return ""
    seen: set[str] = set()
    lines = ["[Relevant memories from this branch:]"]
    for r in results:
        content = r.get("memory")
        if content and content not in seen:
            seen.add(content)
            lines.append(f"- {content}")
    return "\n".join(lines)


def _handle_run_switch(buf: dict, current_run_id: str) -> tuple[dict, str | None, list]:
    if buf["run_id"] == current_run_id:
        return buf, None, []
    old_run_id = buf["run_id"]
    old_turns = list(buf.get("pending_turns", [])) + list(buf["turns"])
    new_buf = _empty_buffer(current_run_id)
    _save_buffer(new_buf)
    return new_buf, old_run_id, old_turns


def recall(query: str) -> str:
    run_id = None
    old_run_id = None
    old_turns: list = []
    with FileLock(_lock_file()):
        buf = _load_buffer()
        buf, old_run_id, old_turns = _handle_run_switch(buf, get_run_id())
        run_id = buf["run_id"]

    if old_turns:
        _best_effort_write(old_run_id, old_turns)

    try:
        raw = get_client().search(
            query,
            filters={"user_id": get_user_id(), "run_id": run_id},
        )
        results = raw.get("results", raw) if isinstance(raw, dict) else raw
        return _format_results(results)
    except Exception as e:
        print(f"[git-memory-harness] ERROR in recall: {e}", file=sys.stderr)
        return ""


def remember(role: str, content: str) -> None:
    turns_to_send = None
    run_id = None
    old_run_id = None
    old_turns: list = []
    with FileLock(_lock_file()):
        buf = _load_buffer()
        buf, old_run_id, old_turns = _handle_run_switch(buf, get_run_id())
        _append_turn(buf, role, content)
        if len(buf["turns"]) >= BATCH_SIZE:
            turns_to_send = list(buf["turns"])
            run_id = buf["run_id"]
            buf["pending_turns"] = turns_to_send
            buf["turns"] = []
        _save_buffer(buf)

    if old_turns:
        _best_effort_write(old_run_id, old_turns)
    if turns_to_send:
        _flush_turns(run_id, turns_to_send)


def flush() -> None:
    with FileLock(_lock_file()):
        buf = _load_buffer()
        all_turns = list(buf.get("pending_turns", [])) + list(buf["turns"])
        if not all_turns:
            return
        run_id = buf["run_id"]
        buf["pending_turns"] = all_turns
        buf["turns"] = []
        _save_buffer(buf)

    _flush_turns(run_id, all_turns)


def ingest_transcript(transcript_path: str) -> None:
    with FileLock(_lock_file()):
        buf = _load_buffer()
        if buf.get("transcript_path") != transcript_path:
            offset = 0
        else:
            offset = buf["transcript_line_offset"]

    try:
        with open(transcript_path) as f:
            lines = f.readlines()
    except OSError as e:
        print(f"[git-memory-harness] ERROR reading transcript: {e}", file=sys.stderr)
        return

    new_turns: list[tuple[str, str]] = []
    for line in lines[offset:]:
        try:
            obj = json.loads(line)
            if obj.get("type") == "user":
                content = obj["message"]["content"]
                if isinstance(content, str):
                    new_turns.append(("user", content))
            elif obj.get("type") == "assistant":
                content = obj["message"]["content"]
                if isinstance(content, list):
                    text = " ".join(
                        b["text"] for b in content if b.get("type") == "text"
                    )
                    if text:
                        new_turns.append(("assistant", text))
        except (KeyError, json.JSONDecodeError):
            continue

    turns_to_send = None
    flush_run_id = None
    old_run_id_ingest = None
    old_turns_ingest: list = []
    with FileLock(_lock_file()):
        buf = _load_buffer()
        buf, old_run_id_ingest, old_turns_ingest = _handle_run_switch(buf, get_run_id())
        buf["transcript_path"] = transcript_path
        buf["transcript_line_offset"] = len(lines)
        for role, content in new_turns:
            _append_turn(buf, role, content)
        if len(buf["turns"]) >= BATCH_SIZE:
            turns_to_send = list(buf["turns"])
            flush_run_id = buf["run_id"]
            buf["pending_turns"] = turns_to_send
            buf["turns"] = []
        _save_buffer(buf)

    if old_turns_ingest:
        _best_effort_write(old_run_id_ingest, old_turns_ingest)
    if turns_to_send:
        _flush_turns(flush_run_id, turns_to_send)
