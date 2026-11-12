"""The engine's data model (PLAN.md section 4.1).

Frozen value objects passed between the cut rules, the optimizer and pricing. Each one checks a
few basics when it is built and raises ``InvalidInput`` instead of carrying a bad value along.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.units import Mm

ALLOWED_ANGLES = (45, 90)


class Colour(StrEnum):
    """Profile colour. Prices and installation gaps depend on it."""

    WHITE = "white"
    FOIL_ONE_SIDE = "foil_one_side"
    FOIL_BOTH_SIDES = "foil_both_sides"


class Role(StrEnum):
    """What a profile or a cut piece is used for."""

    FRAME = "frame"
    SASH = "sash"
    MULLION = "mullion"
    FALSE_MULLION = "false_mullion"
    BEAD = "bead"
    THRESHOLD = "threshold"
    STEEL = "steel"


class Opening(StrEnum):
    """How one field of a window opens, seen from inside."""

    FIXED = "fixed"
    TILT_TURN_LEFT = "tilt_turn_left"
    TILT_TURN_RIGHT = "tilt_turn_right"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidInput(message)


@dataclass(frozen=True)
class SystemConstants:
    """One version of a profile system's sheet.

    Every value comes from the system sheet. No field has a default, so a constant can never be
    filled in by accident. The two mappings are stored read-only.
    """

    system_id: str
    bar_length_mm: Mapping[Role, Mm]
    weld_allowance_mm: Mm
    kerf_mm: Mm
    bar_end_trim_mm: Mm
    steel_shortening_mm: Mm
    deductions: Mapping[str, Mm]
    min_offcut_mm: Mm

    def __post_init__(self) -> None:
        object.__setattr__(self, "bar_length_mm", MappingProxyType(dict(self.bar_length_mm)))
        object.__setattr__(self, "deductions", MappingProxyType(dict(self.deductions)))
        _require(bool(self.system_id.strip()), "system_id must not be empty")
        for role, length in self.bar_length_mm.items():
            _require(length > 0, f"bar length for {role} must be above zero, got {length}")
        for name in (
            "weld_allowance_mm",
            "kerf_mm",
            "bar_end_trim_mm",
            "steel_shortening_mm",
            "min_offcut_mm",
        ):
            value = getattr(self, name)
            _require(value >= 0, f"{name} must not be negative, got {value}")


@dataclass(frozen=True)
class PositionSpec:
    """One line of a quote: a window of one construction type, size and colour."""

    ref: str
    construction_type: str
    width_mm: Mm
    height_mm: Mm
    qty: int
    colour: Colour
    glass_build: str
    openings: tuple[Opening, ...]

    def __post_init__(self) -> None:
        _require(self.width_mm > 0, f"{self.ref}: width must be above zero, got {self.width_mm}")
        _require(self.height_mm > 0, f"{self.ref}: height must be above zero, got {self.height_mm}")
        _require(self.qty >= 1, f"{self.ref}: quantity must be at least 1, got {self.qty}")


@dataclass(frozen=True)
class Piece:
    """One cut piece of profile or steel, with the formula that explains its length."""

    position_ref: str
    role: Role
    label: str
    length_mm: Mm
    angle_left: int
    angle_right: int
    qty: int
    formula: str

    def __post_init__(self) -> None:
        where = f"{self.position_ref} {self.label}"
        _require(self.length_mm > 0, f"{where}: length must be above zero, got {self.length_mm}")
        for side, angle in (("left", self.angle_left), ("right", self.angle_right)):
            _require(
                angle in ALLOWED_ANGLES, f"{where}: {side} angle must be 45 or 90, got {angle}"
            )
        _require(self.qty >= 1, f"{where}: quantity must be at least 1, got {self.qty}")
        _require(bool(self.formula.strip()), f"{where}: every piece needs its formula")


@dataclass(frozen=True)
class GlassPane:
    """One glass pane to order, with the formulas that explain its width and height."""

    position_ref: str
    width_mm: Mm
    height_mm: Mm
    qty: int
    build: str
    formula_w: str
    formula_h: str

    def __post_init__(self) -> None:
        where = f"{self.position_ref} glass"
        _require(self.width_mm > 0, f"{where}: width must be above zero, got {self.width_mm}")
        _require(self.height_mm > 0, f"{where}: height must be above zero, got {self.height_mm}")
        _require(self.qty >= 1, f"{where}: quantity must be at least 1, got {self.qty}")
        _require(bool(self.formula_w.strip()), f"{where}: the width needs its formula")
        _require(bool(self.formula_h.strip()), f"{where}: the height needs its formula")


@dataclass(frozen=True)
class HardwareNeed:
    """Hardware sets needed for one kind of opening sash in a position."""

    position_ref: str
    opening: Opening
    qty: int

    def __post_init__(self) -> None:
        _require(
            self.qty >= 1,
            f"{self.position_ref} hardware: quantity must be at least 1, got {self.qty}",
        )


@dataclass(frozen=True)
class CutList:
    """Everything one job needs cut or ordered."""

    pieces: tuple[Piece, ...]
    steel: tuple[Piece, ...]
    glass: tuple[GlassPane, ...]
    hardware_sets: tuple[HardwareNeed, ...]
    gasket_mm: Mm

    def __post_init__(self) -> None:
        _require(self.gasket_mm >= 0, f"gasket length must not be negative, got {self.gasket_mm}")
