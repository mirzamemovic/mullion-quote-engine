"""Pure calculation engine: cut rules, optimizer and pricing.

Standard library only (plus ``ortools`` inside ``optimizer/exact.py``). This package never
imports the API, the database layer or any web, database or validation framework.
The rule is enforced by the import-linter contract in ``pyproject.toml`` and by
``tests/engine/test_purity.py``.
"""
