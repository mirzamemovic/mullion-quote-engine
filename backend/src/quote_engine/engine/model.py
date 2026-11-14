"""The engine's data model (PLAN.md section 4.1).

Frozen value objects passed between the cut rules, the optimizer and pricing. Each one checks a
few basics when it is built and raises ``InvalidInput`` instead of carrying a bad value along.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.units import Mm

ALLOWED_ANGLES = (45, 90)


class Colour(StrEnum):
    """Profile colour. Prices and installation gaps depend on it."""

    WHITE = "white"
    FOIL_ONE_SIDE = "foil_one_side"
    FOIL_BOTH_SIDES = "foil_both_sides"


class Material(StrEnum):
    """What a profile system is made of. Aluminium corners are crimped, not welded, and need
    no steel; PVC corners are welded and the profiles carry steel reinforcement."""

    PVC = "pvc"
    ALUMINIUM = "aluminium"


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


class ReadOnlyDict[K, V](dict[K, V]):
    """A dict that refuses changes after it is built.

    Unlike ``MappingProxyType`` it can still be copied, pickled and turned into plain data with
    ``dataclasses.asdict``, which snapshots and worker processes need.
    """

    def _refuse(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("this mapping is read-only")

    __setitem__ = _refuse
    __delitem__ = _refuse
    __ior__ = _refuse  # type: ignore[assignment]
    clear = _refuse
    pop = _refuse  # type: ignore[assignment]
    popitem = _refuse  # type: ignore[assignment]
    setdefault = _refuse  # type: ignore[assignment]
    update = _refuse  # pyright: ignore[reportAssignmentType]

    def __reduce__(self) -> tuple[type["ReadOnlyDict[K, V]"], tuple[dict[K, V]]]:
        return (type(self), (dict(self),))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidInput(message)


def _whole(value: object, what: str, *, minimum: int) -> None:
    """Refuse anything that is not a whole number of at least ``minimum`` (``bool`` included)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidInput(f"{what} must be a whole number, got {value!r}")
    _require(value >= minimum, f"{what} must be at least {minimum}, got {value}")


def _text(value: str, what: str) -> None:
    _require(bool(value.strip()), f"{what} must not be empty")


@dataclass(frozen=True)
class SystemConstants:
    """One version of a profile system's sheet.

    Every value comes from the system sheet. No field has a default, so a constant can never be
    filled in by accident. The two mappings are stored read-only.
    """

    system_id: str
    material: Material
    reinforced: bool
    bar_length_mm: Mapping[Role, Mm]
    weld_allowance_mm: Mm
    kerf_mm: Mm
    bar_end_trim_mm: Mm
    steel_shortening_mm: Mm
    deductions: Mapping[str, Mm]
    min_offcut_mm: Mm

    def __post_init__(self) -> None:
        object.__setattr__(self, "bar_length_mm", ReadOnlyDict(self.bar_length_mm))
        object.__setattr__(self, "deductions", ReadOnlyDict(self.deductions))
        _text(self.system_id, "system_id")
        _require(
            isinstance(self.material, Material),
            f"material must be a Material, got {self.material!r}",
        )
        _require(
            type(self.reinforced) is bool,
            f"reinforced must be true or false, got {self.reinforced!r}",
        )
        for role, length in self.bar_length_mm.items():
            _whole(length, f"bar length for {role}", minimum=1)
        for deduction, value in self.deductions.items():
            _whole(value, f"deduction '{deduction}'", minimum=0)
        for name in (
            "weld_allowance_mm",
            "kerf_mm",
            "bar_end_trim_mm",
            "steel_shortening_mm",
            "min_offcut_mm",
        ):
            _whole(getattr(self, name), name, minimum=0)


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
        _text(self.ref, "position ref")
        _text(self.construction_type, f"{self.ref}: construction type")
        _whole(self.width_mm, f"{self.ref}: width", minimum=1)
        _whole(self.height_mm, f"{self.ref}: height", minimum=1)
        _whole(self.qty, f"{self.ref}: quantity", minimum=1)
        _require(bool(self.openings), f"{self.ref}: at least one field (opening) is needed")


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
        _whole(self.length_mm, f"{where}: length", minimum=1)
        for side, angle in (("left", self.angle_left), ("right", self.angle_right)):
            _require(
                type(angle) is int and angle in ALLOWED_ANGLES,
                f"{where}: {side} angle must be 45 or 90, got {angle!r}",
            )
        _whole(self.qty, f"{where}: quantity", minimum=1)
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
        _whole(self.width_mm, f"{where}: width", minimum=1)
        _whole(self.height_mm, f"{where}: height", minimum=1)
        _whole(self.qty, f"{where}: quantity", minimum=1)
        _require(bool(self.formula_w.strip()), f"{where}: the width needs its formula")
        _require(bool(self.formula_h.strip()), f"{where}: the height needs its formula")


@dataclass(frozen=True)
class HardwareNeed:
    """Hardware sets needed for one kind of opening sash in a position."""

    position_ref: str
    opening: Opening
    qty: int

    def __post_init__(self) -> None:
        where = f"{self.position_ref} hardware"
        _require(self.opening is not Opening.FIXED, f"{where}: a fixed field has no hardware set")
        _whole(self.qty, f"{where}: quantity", minimum=1)


@dataclass(frozen=True)
class CutList:
    """Everything one job needs cut or ordered."""

    pieces: tuple[Piece, ...]
    steel: tuple[Piece, ...]
    glass: tuple[GlassPane, ...]
    hardware_sets: tuple[HardwareNeed, ...]
    gasket_mm: Mm

    def __post_init__(self) -> None:
        _whole(self.gasket_mm, "gasket length", minimum=0)
        for piece in self.pieces:
            _require(
                piece.role is not Role.STEEL,
                f"{piece.position_ref} {piece.label}: steel belongs in the steel list",
            )
        for piece in self.steel:
            _require(
                piece.role is Role.STEEL,
                f"{piece.position_ref} {piece.label}: only steel belongs in the steel list",
            )
