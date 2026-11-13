"""Group a job's cut pieces for the optimizer: one group per stock bar (PLAN.md 4.4).

A system has one profile per role, so a profile group is role plus colour. Steel reinforcement
has no colour: all steel of a job is one group, whatever the colour of the windows. Each group is
optimized on its own, against that role's bar length from the system sheet.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.model import Colour, CutList, PositionSpec, Role, SystemConstants
from quote_engine.engine.optimizer.plan import Demand
from quote_engine.engine.rules.common import bar_length
from quote_engine.engine.units import Mm

ROLE_ORDER = {role: index for index, role in enumerate(Role)}
COLOUR_ORDER = {colour: index for index, colour in enumerate(Colour)}


@dataclass(frozen=True)
class PieceGroup:
    """The pieces cut from one kind of stock bar. ``colour`` is ``None`` for steel."""

    role: Role
    colour: Colour | None
    bar_length_mm: Mm
    demands: tuple[Demand, ...]

    @property
    def name(self) -> str:
        """For reports: ``"frame/white"``, or ``"steel"``."""
        return str(self.role) if self.colour is None else f"{self.role}/{self.colour}"


def demand_key(position_ref: str, label: str) -> str:
    """The key that ties a demand back to its piece: position ref and piece label."""
    return f"{position_ref} {label}"


def _order(item: tuple[tuple[Role, Colour | None], object]) -> tuple[int, int]:
    (role, colour), _ = item
    return ROLE_ORDER[role], -1 if colour is None else COLOUR_ORDER[colour]


def group_pieces(
    cut_list: CutList, positions: Iterable[PositionSpec], c: SystemConstants
) -> tuple[PieceGroup, ...]:
    """Every profile piece grouped by role and colour, and all steel in one group.

    Two pieces with the same key must have the same length; their quantities are added.
    Raises ``InvalidInput`` for a piece whose position is unknown, and ``MissingConstant`` when
    the system sheet has no bar length for a role.
    """
    colours = {pos.ref: pos.colour for pos in positions}
    grouped: dict[tuple[Role, Colour | None], dict[str, Demand]] = {}
    for piece in (*cut_list.pieces, *cut_list.steel):
        try:
            colour = colours[piece.position_ref]
        except KeyError:
            raise InvalidInput(
                f"piece '{piece.label}' belongs to unknown position {piece.position_ref}"
            ) from None
        key = demand_key(piece.position_ref, piece.label)
        group_colour = None if piece.role is Role.STEEL else colour
        demands = grouped.setdefault((piece.role, group_colour), {})
        earlier = demands.get(key)
        if earlier is None:
            demands[key] = Demand(key, piece.length_mm, piece.qty)
        elif earlier.length_mm == piece.length_mm:
            demands[key] = Demand(key, piece.length_mm, earlier.qty + piece.qty)
        else:
            raise InvalidInput(
                f"{key}: two pieces with this name have different lengths "
                f"({earlier.length_mm} and {piece.length_mm} mm)"
            )

    return tuple(
        PieceGroup(role, colour, bar_length(c, role), tuple(demands.values()))
        for (role, colour), demands in sorted(grouped.items(), key=_order)
    )
