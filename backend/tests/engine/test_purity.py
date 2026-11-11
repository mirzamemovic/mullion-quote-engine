"""The engine stays pure: importing it loads the standard library only (PLAN.md section 2).

import-linter checks the import statements. This test checks what really gets loaded, in a
fresh interpreter, for every module in the engine package.
"""

import json
import subprocess
import sys

ALLOWED_ROOTS = frozenset(sys.stdlib_module_names) | {"quote_engine"}

PROBE = """
import importlib, json, pkgutil, sys

before = set(sys.modules)
{extra_import}
import quote_engine.engine as engine

for info in pkgutil.walk_packages(engine.__path__, engine.__name__ + "."):
    importlib.import_module(info.name)

loaded = set(sys.modules) - before
print(json.dumps(sorted({{name.partition(".")[0] for name in loaded}})))
"""


def roots_loaded_by_engine(extra_import: str = "") -> set[str]:
    """Top-level packages that importing every engine module pulls into a fresh interpreter."""
    result = subprocess.run(
        [sys.executable, "-c", PROBE.format(extra_import=extra_import)],
        capture_output=True,
        text=True,
        check=True,
    )
    roots: list[str] = json.loads(result.stdout)
    return set(roots)


def test_engine_loads_only_the_standard_library() -> None:
    assert roots_loaded_by_engine() - ALLOWED_ROOTS == set()


def test_probe_notices_a_third_party_import() -> None:
    assert "fastapi" in roots_loaded_by_engine("import fastapi") - ALLOWED_ROOTS
