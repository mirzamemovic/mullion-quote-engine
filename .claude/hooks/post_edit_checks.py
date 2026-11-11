"""PostToolUse hook: tidy and check every file Claude edits.

- Python files in backend/: ruff check --fix + ruff format. Remaining lint errors go back to Claude.
- Engine files (src/quote_engine/engine or tests/engine): run the fast engine tests.
- TypeScript files in frontend/: eslint --fix. Remaining errors go back to Claude.

Skips quietly when the project isn't set up yet (no pyproject.toml / node_modules).
Exit code 2 shows stderr to Claude so it fixes the problem.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MAX_OUTPUT = 4000


def run(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def fail(title: str, proc: subprocess.CompletedProcess[str]) -> None:
    output = (proc.stdout + "\n" + proc.stderr).strip()
    print(f"{title} (exit {proc.returncode}):\n{output[-MAX_OUTPUT:]}", file=sys.stderr)
    sys.exit(2)


def check_python(file: Path, backend: Path) -> None:
    uv = shutil.which("uv")
    if uv is None or not (backend / "pyproject.toml").exists():
        return
    run([uv, "run", "--quiet", "ruff", "check", "--fix", str(file)], backend, 60)
    run([uv, "run", "--quiet", "ruff", "format", str(file)], backend, 60)
    proc = run([uv, "run", "--quiet", "ruff", "check", str(file)], backend, 60)
    if proc.returncode != 0:
        fail(f"ruff found problems in {file.name}", proc)

    rel = file.relative_to(backend).as_posix()
    if rel.startswith(("src/quote_engine/engine/", "tests/engine/")) and (backend / "tests/engine").exists():
        proc = run(
            [uv, "run", "--quiet", "pytest", "tests/engine", "-q", "-x", "-m", "not slow",
             "--no-header", "-p", "no:cacheprovider"],
            backend,
            150,
        )
        # exit 5 = no tests collected yet
        if proc.returncode not in (0, 5):
            fail("engine tests failed after this edit", proc)


def check_typescript(file: Path, frontend: Path) -> None:
    npx = shutil.which("npx")
    if npx is None or not (frontend / "node_modules").exists():
        return
    proc = run([npx, "--no-install", "eslint", "--fix", str(file)], frontend, 90)
    if proc.returncode != 0:
        fail(f"eslint found problems in {file.name}", proc)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    raw = (payload.get("tool_input") or {}).get("file_path")
    if not raw:
        sys.exit(0)

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()).resolve()
    file = Path(raw)
    if not file.is_absolute():
        file = Path(payload.get("cwd") or root) / file
    file = file.resolve()
    if not file.exists():
        sys.exit(0)

    backend, frontend = root / "backend", root / "frontend"
    try:
        if file.suffix == ".py" and file.is_relative_to(backend):
            check_python(file, backend)
        elif file.suffix in {".ts", ".tsx"} and file.is_relative_to(frontend):
            check_typescript(file, frontend)
    except subprocess.TimeoutExpired as exc:
        print(f"check timed out: {exc.cmd}", file=sys.stderr)
        sys.exit(1)  # non-blocking
    sys.exit(0)


if __name__ == "__main__":
    main()
