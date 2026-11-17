"""What a workshop still has to enter before it can quote, found by running the real engine.

A hand-kept list of which deductions and prices each construction type needs would drift from
the rules the moment a rule changed. These functions ask the rules and the pricing themselves:

- ``probe_constants`` cuts a probe window of every construction type with a system sheet as it
  is. Each time a rule asks for a deduction or bar length the sheet lacks, the name is recorded
  and a stand-in is put in its place, until the rule asks for nothing more.
- ``prices_needed`` prices one probe job (every type, both opening sides, every reachable size
  class, every installation switch, transport) with a price book that hands out stand-in prices
  and records each key and unit it is asked for.
- ``TrackingBook`` is a real price book that remembers which prices a calculation used, for the
  "estimated prices" warning.

The stand-in values exist only inside these probes; they never reach a quote, a cut list or a
price. A real quote still raises ``MissingConstant`` or ``MissingPrice`` for anything missing.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date
from math import isqrt

from quote_engine.engine.errors import MissingConstant
from quote_engine.engine.model import Colour, Material, Opening, PositionSpec, Role, SystemConstants
from quote_engine.engine.optimizer.ffd import ffd
from quote_engine.engine.optimizer.groups import group_pieces
from quote_engine.engine.prices import Price, PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import (
    Installation,
    PricingSettings,
    QuoteJob,
    SizeClass,
    SizeThresholds,
    price_job,
    size_class,
)
from quote_engine.engine.rules.registry import cut_position, merge
from quote_engine.engine.sheet import LENGTH_KEYS
from quote_engine.engine.units import Bp, Cents, Mm, Mm2

MIN_SIDE_MM = 300  # the API's smallest window side
MAX_SIDE_MM = 3500  # and its largest
PROBE_GLASS = "probe glass"
MAX_ROUNDS = 100  # far more deductions than any rule uses; stops a broken rule from looping

# One layout per type. Every probe also runs mirrored, so both sides' hardware is asked for.
PROBE_OPENINGS: Mapping[str, tuple[Opening, ...]] = {
    "single_sash_tilt_turn": (Opening.TILT_TURN_LEFT,),
    "two_field_t_mullion": (Opening.TILT_TURN_LEFT, Opening.TURN_RIGHT),
    "two_sash_false_mullion": (Opening.TURN_LEFT, Opening.TILT_TURN_RIGHT),
    "fixed": (Opening.FIXED,),
    "balcony_door_tilt_turn": (Opening.TILT_TURN_LEFT,),
}
MIRRORED = {
    Opening.TILT_TURN_LEFT: Opening.TILT_TURN_RIGHT,
    Opening.TILT_TURN_RIGHT: Opening.TILT_TURN_LEFT,
    Opening.TURN_LEFT: Opening.TURN_RIGHT,
    Opening.TURN_RIGHT: Opening.TURN_LEFT,
    Opening.FIXED: Opening.FIXED,
}

# Stand-ins for a probe only (see the module docstring). Lengths need any whole value; the
# reinforced default asks for the steel deductions too, so nothing a real sheet needs is missed.
_STAND_IN_LENGTH = {
    "weld_allowance_mm": 3,
    "kerf_mm": 4,
    "bar_end_trim_mm": 10,
    "steel_shortening_mm": 10,
    "min_offcut_mm": 500,
}
_STAND_IN_BAR_MM = 6000


def _whole(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def probe_position(
    ref: str, construction_type: str, side: int, mirrored: bool = False
) -> PositionSpec:
    openings = PROBE_OPENINGS[construction_type]
    if mirrored:
        openings = tuple(MIRRORED[o] for o in openings)
    return PositionSpec(
        ref=ref,
        construction_type=construction_type,
        width_mm=Mm(side),
        height_mm=Mm(side),
        qty=1,
        colour=Colour.WHITE,
        glass_build=PROBE_GLASS,
        openings=openings,
    )


@dataclass(frozen=True)
class SheetProbe:
    """A sheet completed with stand-ins, and the names of every value it was missing."""

    constants: SystemConstants
    missing: tuple[str, ...]


def probe_constants(sheet: Mapping[str, object], construction_types: Iterable[str]) -> SheetProbe:
    """Which values ``sheet`` lacks for ``construction_types``, asked of the cut rules.

    ``sheet`` is a system sheet as stored (it may be an unfinished draft). The names are the
    ones a real calculation would raise ``MissingConstant`` with, such as
    ``deductions.sash_width`` or ``kerf_mm``.
    """
    missing = [
        key
        for key in ("material", "reinforced", *LENGTH_KEYS, "bar_length_mm", "deductions")
        if sheet.get(key) is None
    ]
    material_value = sheet.get("material")
    material = Material(material_value) if material_value in ("pvc", "aluminium") else Material.PVC
    reinforced = sheet.get("reinforced")
    lengths: dict[str, Mm] = {}
    for key, stand_in in _STAND_IN_LENGTH.items():
        value = _whole(sheet.get(key))
        lengths[key] = Mm(stand_in if value is None else value)
    raw_bars = sheet.get("bar_length_mm")
    bars: dict[Role, Mm] = {}
    if isinstance(raw_bars, Mapping):
        valid_roles = {r.value for r in Role}
        for name, raw in raw_bars.items():
            length = _whole(raw)
            if str(name) in valid_roles and length:
                bars[Role(str(name))] = Mm(length)
    raw_deductions = sheet.get("deductions")
    deductions: dict[str, Mm] = {}
    if isinstance(raw_deductions, Mapping):
        for name, raw in raw_deductions.items():
            amount = _whole(raw)
            if amount is not None:
                deductions[str(name)] = Mm(amount)
    constants = SystemConstants(
        system_id=str(sheet.get("system_id") or "draft"),
        material=material,
        reinforced=reinforced if isinstance(reinforced, bool) else True,
        bar_length_mm=bars,
        deductions=deductions,
        weld_allowance_mm=lengths["weld_allowance_mm"],
        kerf_mm=lengths["kerf_mm"],
        bar_end_trim_mm=lengths["bar_end_trim_mm"],
        steel_shortening_mm=lengths["steel_shortening_mm"],
        min_offcut_mm=lengths["min_offcut_mm"],
    )

    roles_cut: set[Role] = set()
    for key in construction_types:
        for _ in range(MAX_ROUNDS):
            try:
                cut = cut_position(probe_position("P", key, 1500), constants)
            except MissingConstant as error:
                name = error.name
                missing.append(name)
                group, _, item = name.partition(".")
                if group == "deductions":
                    deductions[item] = Mm(0)
                elif group == "bar_length_mm":
                    bars[Role(item)] = Mm(_STAND_IN_BAR_MM)
                else:
                    raise
                constants = replace(constants, deductions=deductions, bar_length_mm=bars)
            else:
                roles_cut |= {piece.role for piece in (*cut.pieces, *cut.steel)}
                break
    # Grouping the pieces onto bars needs a bar length for every role that was cut.
    for role in sorted(roles_cut):
        if role not in bars:
            missing.append(f"bar_length_mm.{role}")
            bars[role] = Mm(_STAND_IN_BAR_MM)
    constants = replace(constants, bar_length_mm=bars)
    return SheetProbe(constants, tuple(dict.fromkeys(missing)))


def probe_sides(thresholds: SizeThresholds) -> dict[SizeClass, int]:
    """One square window side per size class that a window of the API's sizes can reach."""
    candidates = [
        MIN_SIDE_MM,
        isqrt(thresholds.small_max_mm2),
        isqrt(thresholds.small_max_mm2) + 1,
        isqrt(thresholds.standard_max_mm2),
        isqrt(thresholds.standard_max_mm2) + 1,
        MAX_SIDE_MM,
    ]
    sides: dict[SizeClass, int] = {}
    for side in sorted(s for s in candidates if MIN_SIDE_MM <= s <= MAX_SIDE_MM):
        sides.setdefault(size_class(Mm2(side * side), thresholds), side)
    return sides


class _ProbeBook(PriceBook):
    """Hands out a stand-in price for any key and records what it was asked for."""

    asked: dict[PriceKey, PriceUnit]

    def __init__(self) -> None:
        super().__init__(date.min, {})
        object.__setattr__(self, "asked", {})

    def price(self, key: PriceKey, unit: PriceUnit) -> Price:
        self.asked[key] = unit
        return Price(key, Cents(100), unit, "probe", date.min)


@dataclass(frozen=True, order=True)
class NeededPrice:
    """A price the engine asks for: its key and the unit it must be quoted in."""

    kind: str
    ref: str
    colour: str | None
    unit: str

    @property
    def key(self) -> PriceKey:
        return PriceKey(self.kind, self.ref, Colour(self.colour) if self.colour else None)


def probe_settings(thresholds: SizeThresholds) -> PricingSettings:
    """Pricing settings for a probe: only the size classes matter for which keys are asked."""
    zero = Bp(0)
    return PricingSettings(zero, False, zero, zero, Mm2(0), zero, thresholds)


def probe_job(
    constants: SystemConstants,
    construction_types: Iterable[str],
    thresholds: SizeThresholds,
    colour: Colour,
) -> QuoteJob | None:
    """One job with a window of every type, both opening sides and every reachable size class.

    Deductions are all zero here: which prices a window needs never depends on their values,
    and zero keeps every probe window cuttable. ``None`` when there are no types to probe.
    """
    flat = replace(constants, deductions=dict.fromkeys(constants.deductions, Mm(0)))
    positions: list[PositionSpec] = []
    for key in construction_types:
        for side in probe_sides(thresholds).values():
            for mirrored in (False, True):
                ref = f"P{len(positions) + 1}"
                positions.append(replace(probe_position(ref, key, side, mirrored), colour=colour))
    if not positions:
        return None
    cut_lists = {pos.ref: cut_position(pos, flat) for pos in positions}
    groups = group_pieces(merge(cut_lists.values()), positions, flat)
    plans = {
        g.name: ffd(g.demands, g.bar_length_mm, flat.kerf_mm, flat.bar_end_trim_mm) for g in groups
    }
    everything = Installation(install=True, ral=True, old_window_removal=True, wall_repair=True)
    return QuoteJob(
        positions=tuple(positions),
        cut_lists=cut_lists,
        groups=groups,
        plans=plans,
        kerf_mm=flat.kerf_mm,
        system_id=flat.system_id,
        material=flat.material,
        installation=dict.fromkeys((p.ref for p in positions), everything),
        transport_km=1,
    )


def prices_needed(
    constants: SystemConstants,
    construction_types: Iterable[str],
    thresholds: SizeThresholds,
    colour: Colour,
) -> tuple[NeededPrice, ...]:
    """Every price a quote of this system in ``colour`` can ask for, sorted.

    The glass build of the probes is ``PROBE_GLASS``: any glass the workshop prices will do,
    so callers treat that key as "at least one glass price".
    """
    job = probe_job(constants, construction_types, thresholds, colour)
    if job is None:
        return ()
    book = _ProbeBook()
    price_job(job, book, probe_settings(thresholds))
    return tuple(
        sorted(
            NeededPrice(k.kind, k.ref, k.colour.value if k.colour else None, unit.value)
            for k, unit in book.asked.items()
        )
    )


class TrackingBook(PriceBook):
    """A real price book that remembers which prices a calculation used."""

    used: dict[PriceKey, Price]

    def __init__(self, book: PriceBook) -> None:
        super().__init__(book.valid_from, book.prices)
        object.__setattr__(self, "used", {})

    def price(self, key: PriceKey, unit: PriceUnit) -> Price:
        found = super().price(key, unit)
        self.used[key] = found
        return found
