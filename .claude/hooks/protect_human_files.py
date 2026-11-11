"""PreToolUse hook: block Claude from writing the files Mirza writes himself.

Covers the Edit/Write tools and Bash commands that would write, move or delete
those paths. The Bash check is best-effort (pattern based); CLAUDE.md also forbids
workarounds. Exit code 2 blocks the tool call and shows stderr to Claude.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path, PurePosixPath

# Repo-relative, forward slashes. A trailing slash protects a whole folder.
PROTECTED = (
    "backend/src/quote_engine/engine/optimizer/ffd.py",
    "backend/tests/golden/jobs/",
)

REASON = (
    "Blocked by .claude/hooks/protect_human_files.py: {path} is written by Mirza only "
    "(see CLAUDE.md and docs/PLAN.md section 13). Do not work around this. "
    "If you need a change there, describe it and let Mirza make it."
)

# Bash patterns that write, move, delete or overwrite files.
WRITE_COMMANDS = re.compile(
    r"(^|[\s;&|(`])("
    r"rm|mv|cp|tee|truncate|dd|install|touch|ln|chmod|unlink|rsync"
    r"|sed\s+(-[a-zA-Z]*i|--in-place)"
    r"|perl\s+-[a-zA-Z]*i"
    r"|git\s+(checkout|restore|rm|mv|apply|stash\s+pop)"
    r"|python3?\s+-c|uv\s+run\s+python\s+-c|node\s+-e"
    r")\b"
)
REDIRECT_TARGET = re.compile(r"(?<![0-9&])>{1,2}\s*['\"]?([^\s;&|'\"]+)")


def project_dir(payload: dict) -> Path:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    return Path(root).resolve()


def to_repo_relative(raw: str, root: Path, cwd: Path) -> str | None:
    path = Path(raw)
    if not path.is_absolute():
        path = cwd / path
    try:
        rel = path.resolve().relative_to(root)
    except ValueError:
        return None
    return PurePosixPath(*rel.parts).as_posix()


def protected_match(rel: str) -> str | None:
    for item in PROTECTED:
        if item.endswith("/"):
            if rel == item.rstrip("/") or rel.startswith(item):
                return item
        elif rel == item:
            return item
    return None


def mentions_protected(text: str) -> str | None:
    normalised = text.replace("\\", "/")
    for item in PROTECTED:
        needle = item.rstrip("/")
        # also catch paths written relative to backend/ or with only the tail
        tails = {needle, needle.removeprefix("backend/"), "/".join(needle.split("/")[-2:])}
        if any(t in normalised for t in tails):
            return item
    return None


def touches_ancestor(command: str, root: Path, cwd: Path) -> str | None:
    """Catch `rm -rf backend/tests` or `git checkout .`: a folder that contains a protected path."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    for token in tokens:
        if token.startswith("-") or any(ch in token for ch in "*?$=<>|;&"):
            continue
        rel = to_repo_relative(token, root, cwd)
        if rel is None:
            continue
        for item in PROTECTED:
            if rel in ("", ".") or item.startswith(rel.rstrip("/") + "/"):
                return item
    return None


def block(path: str) -> None:
    print(REASON.format(path=path), file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    root = project_dir(payload)
    cwd = Path(payload.get("cwd") or root)

    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        for target in REDIRECT_TARGET.findall(command):
            rel = to_repo_relative(target, root, cwd)
            hit = protected_match(rel) if rel else mentions_protected(target)
            if hit:
                block(hit)
        if WRITE_COMMANDS.search(command):
            hit = mentions_protected(command) or touches_ancestor(command, root, cwd)
            if hit:
                block(hit)
        sys.exit(0)

    raw = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")
    if not raw:
        sys.exit(0)
    rel = to_repo_relative(str(raw), root, cwd)
    if rel:
        hit = protected_match(rel)
        if hit:
            block(hit)
    sys.exit(0)


if __name__ == "__main__":
    main()
