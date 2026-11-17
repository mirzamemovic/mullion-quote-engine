"""The price book: what the engine may charge, and from whom (PLAN.md sections 4.5 and 5).

Prices come in as plain data from one price-list version. Every price has a unit, a supplier and
the date it was quoted. A missing price raises ``MissingPrice``; nothing is guessed.

Item keys used by pricing (services map real profile codes and supplier items onto these):

=================  =====================================  ======  ==========
kind               ref                                    colour  unit
=================  =====================================  ======  ==========
``profile``        role (``frame``, ``sash``, ...)        yes     ``bar``
``steel``          ``steel``                              no      ``bar``
``gasket``         ``gasket``                             no      ``m``
``hardware``       opening (``tilt_turn_left``, ...)      no      ``set``
``glass``          glass build (``4-16-4``)               no      ``m2``
``consumables``    ``window``                             no      ``piece``
``labour``         ``<construction type>/<size class>``   no      ``piece``
``installation``   size class, ``ral``, ``old_window_removal``, ``wall_repair``  no  ``piece``
``sill``           sill ref                               yes     ``m``
``shutter``        shutter ref                            no      ``m2``
``screen``         screen ref                             no      ``m2``
``transport``      ``flat`` / ``km``                      no      ``job`` / ``km``
=================  =====================================  ======  ==========
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from quote_engine.engine.errors import InvalidInput, MissingPrice
from quote_engine.engine.model import Colour
from quote_engine.engine.units import Cents


class PriceUnit(StrEnum):
    """What one price is for."""

    BAR = "bar"
    METRE = "m"
    SQUARE_METRE = "m2"
    SET = "set"
    PIECE = "piece"
    JOB = "job"
    KM = "km"


@dataclass(frozen=True)
class PriceKey:
    """Which item a price is for. ``colour`` is set only for items priced by colour."""

    kind: str
    ref: str
    colour: Colour | None = None


@dataclass(frozen=True)
class Price:
    """One entry of a price list."""

    key: PriceKey
    amount_cents: Cents
    unit: PriceUnit
    supplier: str
    quoted_on: date
    # A starter price (market estimate) rather than a supplier's quote; quotes using it warn.
    estimate: bool = False

    def __post_init__(self) -> None:
        if type(self.amount_cents) is not int or self.amount_cents < 0:
            raise InvalidInput(f"{self.key}: price must be whole cents, zero or more")
        if not self.supplier.strip():
            raise InvalidInput(f"{self.key}: every price needs its supplier")


@dataclass(frozen=True)
class PriceBook:
    """One price-list version: every price by its key."""

    valid_from: date
    prices: Mapping[PriceKey, Price]

    @classmethod
    def of(cls, valid_from: date, prices: Iterable[Price]) -> "PriceBook":
        """Build a price book; one price per key."""
        by_key: dict[PriceKey, Price] = {}
        for price in prices:
            if price.key in by_key:
                raise InvalidInput(f"price list has two prices for {price.key}")
            by_key[price.key] = price
        return cls(valid_from, by_key)

    def price(self, key: PriceKey, unit: PriceUnit) -> Price:
        """The price for ``key``, which must be quoted per ``unit``. Never guesses."""
        try:
            found = self.prices[key]
        except KeyError:
            raise MissingPrice(key.kind, key.ref, key.colour) from None
        if found.unit is not unit:
            raise InvalidInput(
                f"{key.kind} '{key.ref}' is priced per {found.unit}, expected {unit}"
            )
        return found

    def amount(self, key: PriceKey, unit: PriceUnit) -> Cents:
        """Just the amount of ``price(key, unit)``."""
        return self.price(key, unit).amount_cents
