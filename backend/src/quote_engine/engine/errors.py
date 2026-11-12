"""Errors raised by the engine.

The engine never falls back to a guessed value. A missing catalogue value or price, or an input
it cannot work with, always surfaces as one of these.
"""


class EngineError(Exception):
    """Base class for every error the engine raises."""


class InvalidInput(EngineError):
    """The caller passed a value the engine cannot work with, such as a size of zero."""


class MissingConstant(EngineError):
    """A catalogue value (deduction, limit, bar length) is not in the system sheet."""

    def __init__(self, system_id: str, name: str) -> None:
        self.system_id = system_id
        self.name = name
        super().__init__(f"system sheet '{system_id}' has no value for '{name}'")


class MissingPrice(EngineError):
    """The price list has no entry for an item the job needs."""

    def __init__(self, item_kind: str, item_ref: str, colour: str | None = None) -> None:
        self.item_kind = item_kind
        self.item_ref = item_ref
        self.colour = colour
        in_colour = f" in colour '{colour}'" if colour else ""
        super().__init__(f"price list has no price for {item_kind} '{item_ref}'{in_colour}")
