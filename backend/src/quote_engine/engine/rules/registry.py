"""The construction types the engine knows, and the one entry point that cuts a job.

``cut_job`` checks each position against its type (known key, number of fields, fixed or
opening) before calling that type's rule, then merges the results into one ``CutList``.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from types import ModuleType

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.model import CutList, Opening, PositionSpec, SystemConstants
from quote_engine.engine.rules import (
    balcony_door_tilt_turn,
    fixed,
    single_sash_tilt_turn,
    two_field_t_mullion,
    two_sash_false_mullion,
)
from quote_engine.engine.units import Mm

CutRule = Callable[[PositionSpec, SystemConstants], CutList]


@dataclass(frozen=True)
class ConstructionType:
    """One construction type: its key, how many fields it has, and its cut rule."""

    key: str
    fields: int
    fixed: bool
    rule: CutRule


def _from_module(module: ModuleType, *, fixed: bool = False) -> ConstructionType:
    return ConstructionType(module.KEY, module.FIELDS, fixed, module.cut)


TYPES: Mapping[str, ConstructionType] = {
    t.key: t
    for t in (
        _from_module(single_sash_tilt_turn),
        _from_module(two_field_t_mullion),
        _from_module(two_sash_false_mullion),
        _from_module(fixed, fixed=True),
        _from_module(balcony_door_tilt_turn),
    )
}


def construction_type(key: str) -> ConstructionType:
    """Return the construction type for ``key``, or raise ``InvalidInput``."""
    try:
        return TYPES[key]
    except KeyError:
        known = ", ".join(sorted(TYPES))
        raise InvalidInput(f"unknown construction type '{key}' (known: {known})") from None


def check_position(pos: PositionSpec) -> ConstructionType:
    """Check a position against its construction type and return that type."""
    kind = construction_type(pos.construction_type)
    if len(pos.openings) != kind.fields:
        raise InvalidInput(
            f"{pos.ref}: {kind.key} has {kind.fields} field(s), got {len(pos.openings)} opening(s)"
        )
    fixed_fields = [opening is Opening.FIXED for opening in pos.openings]
    if kind.fixed and not all(fixed_fields):
        raise InvalidInput(f"{pos.ref}: every field of a fixed window must be fixed")
    if not kind.fixed and any(fixed_fields):
        raise InvalidInput(f"{pos.ref}: every field of a {kind.key} must open")
    return kind


def cut_position(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Cut one position with its construction type's rule."""
    return check_position(pos).rule(pos, c)


def merge(cut_lists: Iterable[CutList]) -> CutList:
    """One cut list holding every piece, pane and hardware set of the given lists, in order."""
    lists = tuple(cut_lists)
    return CutList(
        pieces=tuple(piece for cl in lists for piece in cl.pieces),
        steel=tuple(piece for cl in lists for piece in cl.steel),
        glass=tuple(pane for cl in lists for pane in cl.glass),
        hardware_sets=tuple(need for cl in lists for need in cl.hardware_sets),
        gasket_mm=Mm(sum(cl.gasket_mm for cl in lists)),
    )


def cut_job(positions: Iterable[PositionSpec], c: SystemConstants) -> CutList:
    """Cut every position of a job and merge the results. Position refs must be unique."""
    seen: set[str] = set()
    results = []
    for pos in positions:
        if pos.ref in seen:
            raise InvalidInput(f"position ref '{pos.ref}' is used twice")
        seen.add(pos.ref)
        results.append(cut_position(pos, c))
    return merge(results)
