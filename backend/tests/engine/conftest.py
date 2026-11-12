"""Fixtures shared by the engine tests.

SAMPLE - NOT REAL. Every value here is invented for the tests. Real constants come only from a
profile system's sheet (PLAN.md section 2).
"""

import pytest

from quote_engine.engine.model import Role, SystemConstants
from quote_engine.engine.units import Mm


@pytest.fixture
def sample_constants() -> SystemConstants:
    """An invented system sheet with obviously fake values."""
    return SystemConstants(
        system_id="sample-not-real",
        bar_length_mm={Role.FRAME: Mm(9999), Role.SASH: Mm(9999), Role.STEEL: Mm(7777)},
        weld_allowance_mm=Mm(1),
        kerf_mm=Mm(2),
        bar_end_trim_mm=Mm(3),
        steel_shortening_mm=Mm(4),
        deductions={"sample_sash_deduction": Mm(11)},
        min_offcut_mm=Mm(555),
    )
