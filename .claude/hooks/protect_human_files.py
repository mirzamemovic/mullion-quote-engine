"""PreToolUse hook: block Claude from writing the files Mirza writes himself.

Covers the Edit/Write tools and Bash or PowerShell commands that would write, move
or delete those paths. The shell check is best-effort (pattern based); CLAUDE.md also
forbids workarounds. Exit code 2 blocks the tool call and shows stderr to Claude.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path, PurePosixPath

# Repo-relative, forward slashes. A trailing slash protects a whole folder.
# ffd.py was protected until 2026-11-13, when Mirza chose to have it written for him.
PROTECTED = ("backend/tests/golden/jobs/",)

REASON = (
    "Blocked by .claude/hooks/protect_human_files.py: {path} is written by Mirza only "
    "(see CLAUDE.md and docs/PLAN.md section 13). Do not work around this. "
    "If you need a change there, describe it and let Mirza make it."
)

SHELL_TOOLS = ("Bash", "PowerShell")

# Windows file names ignore case: FFD.py and ffd.py are the same file there.
WINDOWS = os.name == "nt"

# Shell patterns that write, move, delete or overwrite files. Checked for both shells:
# rm, mv, cp and tee are PowerShell aliases too, and git/python/node behave the same.
WRITE_COMMANDS_PATTERN = (
    r"(^|[\s;&|({`])("
    r"rm|mv|cp|tee|truncate|dd|install|touch|ln|chmod|unlink|rsync"
    r"|sed\s+(-[a-zA-Z]*i|--in-place)"
    r"|perl\s+-[a-zA-Z]*i"
    r"|git\s+(checkout|restore|rm|mv|apply|stash\s+pop)"
    r"|python3?\s+-c|uv\s+run\s+python\s+-c|node\s+-e"
    r")\b"
)
WRITE_COMMANDS = re.compile(WRITE_COMMANDS_PATTERN)
# PowerShell ignores case in command names, and so does every shell on Windows.
WRITE_COMMANDS_ANY_CASE = re.compile(WRITE_COMMANDS_PATTERN, re.IGNORECASE)

# The file a `>` or `>>` writes to: quoted (may contain spaces) or bare. Covers `2>` and `&>`.
# `2>&1` names no file and does not match.
REDIRECT_TARGET = re.compile(r">{1,2}\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s;&|'\"]+))")

# Separators and brackets that end up glued to a path, as in `git checkout .; npm ci`.
GLUED_PUNCTUATION = ";&|(){}"

# PowerShell only: cmdlets and aliases that write, move, delete or overwrite files.
# Each name is matched as a whole command word, ignoring case (PowerShell ignores case).
# rm, mv, cp, tee and the `>` redirect are already covered above. Short aliases that are also
# ordinary words in other commands (such as `ci` in `npm ci`) are left out on purpose.
POWERSHELL_WRITE_NAMES: tuple[str, ...] = (
    # content
    "Set-Content", "sc", "Add-Content", "ac", "Clear-Content", "clc",
    "Out-File", "Tee-Object", "Export-Csv", "Export-Clixml",
    # items
    "New-Item", "ni", "md", "mkdir",
    "Remove-Item", "ri", "del", "erase", "rd", "rmdir",
    "Move-Item", "mi", "move",
    "Copy-Item", "cpi", "copy",
    "Rename-Item", "rni", "ren",
    "Clear-Item", "cli", "Set-Item", "si",
    # archives and downloads that write files
    "Expand-Archive", "Compress-Archive",
    "Invoke-WebRequest", "iwr", "Invoke-RestMethod", "irm", "Start-BitsTransfer",
)

# PowerShell only: a .NET static call such as [IO.File]::WriteAllText(...) can write anything.
DOTNET_CALL = re.compile(r"\]\s*::")


def powershell_write_pattern(names: tuple[str, ...]) -> re.Pattern[str] | None:
    if not names:
        return None
    alternatives = "|".join(re.escape(name) for name in names)
    return re.compile(rf"(^|[\s;&|({{])({alternatives})(?![\w-])", re.IGNORECASE)


POWERSHELL_WRITE = powershell_write_pattern(POWERSHELL_WRITE_NAMES)


def fold(text: str) -> str:
    return text.casefold() if WINDOWS else text


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
    rel = fold(rel)
    for item in PROTECTED:
        target = fold(item)
        if target.endswith("/"):
            if rel == target.rstrip("/") or rel.startswith(target):
                return item
        elif rel == target:
            return item
    return None


def mentions_protected(text: str) -> str | None:
    normalised = fold(text.replace("\\", "/"))
    for item in PROTECTED:
        needle = fold(item.rstrip("/"))
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
        word = token.strip(GLUED_PUNCTUATION)
        if not word or word.startswith("-") or any(ch in word for ch in "*?$=<>|;&"):
            continue
        rel = to_repo_relative(word, root, cwd)
        if rel is None:
            continue
        rel = fold(rel)
        for item in PROTECTED:
            if rel in ("", ".") or fold(item).startswith(rel.rstrip("/") + "/"):
                return item
    return None


def is_write_command(tool: str, command: str) -> bool:
    ignore_case = tool == "PowerShell" or WINDOWS
    if (WRITE_COMMANDS_ANY_CASE if ignore_case else WRITE_COMMANDS).search(command):
        return True
    if tool != "PowerShell":
        return False
    if DOTNET_CALL.search(command):
        return True
    return POWERSHELL_WRITE is not None and POWERSHELL_WRITE.search(command) is not None


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

    if tool in SHELL_TOOLS:
        command = str(tool_input.get("command", ""))
        if tool == "PowerShell":
            # Backslash separates path parts in PowerShell; its escape character is the backtick.
            command = command.replace("\\", "/")
        for groups in REDIRECT_TARGET.findall(command):
            target = next(filter(None, groups))
            rel = to_repo_relative(target, root, cwd)
            hit = protected_match(rel) if rel else mentions_protected(target)
            if hit:
                block(hit)
        if is_write_command(tool, command):
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
