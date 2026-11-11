"""Tests for the PreToolUse hook that protects the files Mirza writes himself.

Each case pipes a tool-call payload to the hook, the way Claude Code does, and checks the
exit code: 2 = blocked, 0 = allowed. Run from backend/: uv run pytest ../.claude/hooks
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name("protect_human_files.py")
BLOCKED, ALLOWED = 2, 0

FFD = "backend/src/quote_engine/engine/optimizer/ffd.py"
FFD_WIN = FFD.replace("/", "\\")
JOBS = "backend/tests/golden/jobs"
JOBS_WIN = JOBS.replace("/", "\\")

WAITING = pytest.mark.xfail(
    reason="waiting for Mirza: POWERSHELL_WRITE_NAMES in protect_human_files.py"
)
WINDOWS_ONLY = pytest.mark.skipif(
    os.name != "nt", reason="file names are case-sensitive on this system"
)


def run_hook(root: Path, tool: str, tool_input: dict[str, str]) -> subprocess.CompletedProcess[str]:
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(root)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)},
        cwd=root,
        timeout=30,
        check=False,
    )


@pytest.mark.parametrize(
    ("tool", "key", "path", "expected"),
    [
        pytest.param("Write", "file_path", FFD, BLOCKED, id="write-ffd"),
        pytest.param("Edit", "file_path", FFD, BLOCKED, id="edit-ffd"),
        pytest.param("Write", "file_path", f"{JOBS}/job-004.yaml", BLOCKED, id="write-golden-job"),
        pytest.param("NotebookEdit", "notebook_path", f"{JOBS}/notes.ipynb", BLOCKED, id="notebook-in-jobs"),
        pytest.param(
            "Write", "file_path", FFD.replace("ffd.py", "FFD.PY"), BLOCKED,
            marks=WINDOWS_ONLY, id="write-ffd-other-case",
        ),
        pytest.param(
            "Write", "file_path", "backend/src/quote_engine/engine/units.py", ALLOWED, id="write-ordinary-file",
        ),
        pytest.param(
            "Write", "file_path", "backend/src/quote_engine/engine/optimizer/exact.py", ALLOWED,
            id="write-neighbour-of-ffd",
        ),
    ],
)
def test_file_tools(tmp_path: Path, tool: str, key: str, path: str, expected: int) -> None:
    result = run_hook(tmp_path, tool, {key: str(tmp_path.joinpath(*path.split("/")))})
    assert result.returncode == expected


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        pytest.param(f"echo '# hello' > {FFD}", BLOCKED, id="redirect-into-ffd"),
        pytest.param("rm -rf backend/tests", BLOCKED, id="rm-parent-folder"),
        pytest.param(f"mv draft.py {FFD}", BLOCKED, id="mv-onto-ffd"),
        pytest.param("git checkout .", BLOCKED, id="git-checkout-everything"),
        pytest.param(f"cat {FFD}", ALLOWED, id="read-ffd"),
        pytest.param("uv run pytest tests/engine -q", ALLOWED, id="run-tests"),
    ],
)
def test_bash(tmp_path: Path, command: str, expected: int) -> None:
    assert run_hook(tmp_path, "Bash", {"command": command}).returncode == expected


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        pytest.param(f"echo '# hello' > {FFD_WIN}", BLOCKED, id="redirect-into-ffd"),
        pytest.param("rm backend\\tests -Recurse -Force", BLOCKED, id="rm-alias-parent-folder"),
        pytest.param("git checkout .", BLOCKED, id="git-checkout-everything"),
        pytest.param(f"[IO.File]::WriteAllText('{FFD}', '# hello')", BLOCKED, id="dotnet-write"),
        pytest.param(f"Get-Content {FFD_WIN}", ALLOWED, id="read-ffd"),
        pytest.param("uv run pytest tests/golden -q", ALLOWED, id="run-golden-tests"),
        pytest.param("cd backend; npm ci", ALLOWED, id="npm-ci-is-not-copy-item"),
        pytest.param(f"Set-Content {FFD_WIN} '# hello'", BLOCKED, marks=WAITING, id="set-content"),
        pytest.param(f"set-content {FFD_WIN} '# hello'", BLOCKED, marks=WAITING, id="set-content-lower-case"),
        pytest.param(f"'# hello' | Out-File -FilePath {FFD_WIN}", BLOCKED, marks=WAITING, id="out-file"),
        pytest.param(f"New-Item -ItemType File {FFD_WIN}", BLOCKED, marks=WAITING, id="new-item"),
        pytest.param(f"Copy-Item draft.py {FFD_WIN}", BLOCKED, marks=WAITING, id="copy-item"),
        pytest.param(f"Remove-Item {JOBS_WIN} -Recurse", BLOCKED, marks=WAITING, id="remove-item"),
        pytest.param("Move-Item backend\\tests old-tests", BLOCKED, marks=WAITING, id="move-item-parent-folder"),
    ],
)
def test_powershell(tmp_path: Path, command: str, expected: int) -> None:
    assert run_hook(tmp_path, "PowerShell", {"command": command}).returncode == expected


def test_blocked_message_names_the_protected_path(tmp_path: Path) -> None:
    result = run_hook(tmp_path, "Write", {"file_path": str(tmp_path.joinpath(*FFD.split("/")))})
    assert result.returncode == BLOCKED
    assert FFD in result.stderr
    assert "Mirza" in result.stderr


def test_matcher_in_settings_covers_every_tool_the_hook_handles() -> None:
    settings = json.loads(HOOK.parents[1].joinpath("settings.json").read_text(encoding="utf-8"))
    matcher = settings["hooks"]["PreToolUse"][0]["matcher"].split("|")
    assert {"Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"} <= set(matcher)
