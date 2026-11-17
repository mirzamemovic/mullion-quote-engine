"""Deployment files: what can be checked without Docker, a server or GitHub (PLAN.md 11 and 12)."""

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).parents[2]
INFRA = ROOT / "infra"
SCRIPTS = sorted(INFRA.glob("*.sh"))
BASH = shutil.which("bash")


def read_yaml(path: Path) -> dict[Any, Any]:
    data: dict[Any, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


@pytest.mark.skipif(BASH is None, reason="bash is not installed here")
@pytest.mark.parametrize("script", SCRIPTS, ids=[s.name for s in SCRIPTS])
def test_shell_scripts_parse_and_fail_fast(script: Path) -> None:
    assert BASH is not None
    result = subprocess.run([BASH, "-n", str(script)], capture_output=True, text=True, check=False)

    assert result.returncode == 0, result.stderr
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -euo pipefail" in text


def test_scripts_have_lf_line_endings() -> None:
    for script in SCRIPTS:
        assert b"\r\n" not in script.read_bytes(), script.name


def test_production_stack_keeps_secrets_out_of_the_repository() -> None:
    stack = read_yaml(INFRA / "compose.prod.yaml")
    services = stack["services"]

    assert set(services) == {"caddy", "app", "db"}
    assert services["app"]["env_file"] == "/etc/quote-engine/app.env"
    assert "ports" not in services["app"]  # only Caddy is reachable from outside
    assert "ports" not in services["db"]
    password = services["db"]["environment"]["POSTGRES_PASSWORD"]
    assert password.startswith("${POSTGRES_PASSWORD:?")  # no default: must come from the env file


def test_caddy_sets_the_security_headers() -> None:
    caddyfile = (INFRA / "Caddyfile").read_text(encoding="utf-8")

    for header in (
        "Strict-Transport-Security",
        "Content-Security-Policy \"default-src 'self'; frame-ancestors 'none'",
        'X-Content-Type-Options "nosniff"',
        'Referrer-Policy "same-origin"',
    ):
        assert header in caddyfile


def test_image_runs_as_a_non_root_user_and_serves_the_frontend() -> None:
    dockerfile = (INFRA / "Dockerfile").read_text(encoding="utf-8")

    assert "USER app" in dockerfile
    assert "COPY --from=frontend /frontend/dist ./static" in dockerfile
    assert "QUOTE_ENGINE_STATIC_DIR=/app/static" in dockerfile


@pytest.mark.parametrize("name", ["ci.yml", "deploy.yml", "codeql.yml"])
def test_workflows_start_read_only(name: str) -> None:
    workflow = read_yaml(ROOT / ".github" / "workflows" / name)

    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow[True]  # PyYAML reads the key "on" as True


def test_deploy_runs_only_after_ci_passes_on_main() -> None:
    workflow = read_yaml(ROOT / ".github" / "workflows" / "deploy.yml")
    trigger = workflow[True]["workflow_run"]

    assert trigger == {"workflows": ["CI"], "types": ["completed"], "branches": ["main"]}
    condition = workflow["jobs"]["image"]["if"]
    assert "conclusion == 'success'" in condition
    assert "event == 'push'" in condition
    assert "head_repository.full_name == github.repository" in condition


@pytest.mark.parametrize("script", ["deploy.sh", "backup.sh", "restore.sh", "purge-sandboxes.sh"])
def test_scripts_set_the_image_before_using_compose(script: str) -> None:
    # compose.prod.yaml refuses to load without APP_IMAGE, even for `exec`.
    text = (INFRA / script).read_text(encoding="utf-8")

    assert "export APP_IMAGE" in text
    assert text.index("export APP_IMAGE") < text.index(
        "compose ", text.index("export APP_IMAGE") - 1
    )


def test_server_setup_installs_every_timer_it_names() -> None:
    setup = (INFRA / "setup-server.sh").read_text(encoding="utf-8")

    for unit in ("quote-engine-backup", "quote-engine-sandboxes"):
        assert (INFRA / "systemd" / f"{unit}.service").is_file()
        assert (INFRA / "systemd" / f"{unit}.timer").is_file()
        assert f"systemctl enable --now {unit}.timer" in setup


def test_dockerignore_keeps_env_files_out_everywhere() -> None:
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert {"**/.env", "**/.env.*"} <= set(lines)
