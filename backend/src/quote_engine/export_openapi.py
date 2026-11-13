"""Write the API's OpenAPI schema to ``frontend/openapi.json`` (PLAN.md section 6).

    uv run python -m quote_engine.export_openapi          # write the file
    uv run python -m quote_engine.export_openapi --check  # exit 1 when the file is out of date

The frontend generates its types from this file (``npm run gen:api``), so CI fails when it is
stale.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from quote_engine.main import create_app

DEFAULT_TARGET = Path(__file__).resolve().parents[3] / "frontend" / "openapi.json"


def schema_text() -> str:
    """The schema as stable, sorted JSON with a final newline."""
    schema: dict[str, Any] = create_app().openapi()
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m quote_engine.export_openapi")
    parser.add_argument("--check", action="store_true", help="only check that the file is current")
    parser.add_argument("--output", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args(argv)
    text = schema_text()
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
    if args.check:
        if current != text:
            print(f"{args.output} is out of date: run python -m quote_engine.export_openapi")
            return 1
        return 0
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
