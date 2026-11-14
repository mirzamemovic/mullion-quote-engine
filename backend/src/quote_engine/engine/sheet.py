"""System sheet loading: plain data (as read from YAML or the database) into ``SystemConstants``.

The engine never reads files. Callers parse the sheet and pass the resulting mapping here.
A missing value raises ``MissingConstant``; an unknown key or a value of the wrong kind raises
``InvalidInput``. Nothing is filled in with a default.
"""

from collections.abc import Mapping

from quote_engine.engine.errors import InvalidInput, MissingConstant
from quote_engine.engine.model import Material, Role, SystemConstants
from quote_engine.engine.units import Mm

LENGTH_KEYS = (
    "weld_allowance_mm",
    "kerf_mm",
    "bar_end_trim_mm",
    "steel_shortening_mm",
    "min_offcut_mm",
)
MAPPING_KEYS = ("bar_length_mm", "deductions")
ALL_KEYS = frozenset(("system_id", "material", "reinforced", *LENGTH_KEYS, *MAPPING_KEYS))


def _length(value: object, what: str, system_id: str) -> Mm:
    if value is None:
        raise MissingConstant(system_id, what)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidInput(f"{what} must be a whole number of millimetres, got {value!r}")
    return Mm(value)


def _mapping(value: object, what: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise InvalidInput(f"{what} must be a mapping, got {type(value).__name__}")
    return value


def system_constants_from_mapping(data: Mapping[str, object]) -> SystemConstants:
    """Build one system sheet version from plain data.

    Expected keys: ``system_id``, ``bar_length_mm`` (role name to length), the five constants in
    ``LENGTH_KEYS``, and ``deductions`` (name to length). All lengths are whole millimetres.
    """
    system_id = data.get("system_id")
    if not isinstance(system_id, str) or not system_id.strip():
        raise InvalidInput(f"system_id must be a non-empty text, got {system_id!r}")

    unknown = sorted(str(key) for key in set(data) - ALL_KEYS)
    if unknown:
        raise InvalidInput(f"system sheet '{system_id}' has unknown keys: {', '.join(unknown)}")
    for key in ("material", "reinforced", *LENGTH_KEYS, *MAPPING_KEYS):
        if data.get(key) is None:
            raise MissingConstant(system_id, key)
    try:
        material = Material(str(data["material"]))
    except ValueError:
        raise InvalidInput(
            f"system sheet '{system_id}': material must be 'pvc' or 'aluminium', "
            f"got {data['material']!r}"
        ) from None
    reinforced = data["reinforced"]
    if not isinstance(reinforced, bool):
        raise InvalidInput(f"system sheet '{system_id}': reinforced must be true or false")

    bar_lengths: dict[Role, Mm] = {}
    for role_name, length in _mapping(data["bar_length_mm"], "bar_length_mm").items():
        try:
            role = Role(str(role_name))
        except ValueError:
            raise InvalidInput(
                f"system sheet '{system_id}': unknown role '{role_name}' in bar_length_mm"
            ) from None
        bar_lengths[role] = _length(length, f"bar_length_mm.{role_name}", system_id)

    deductions = {
        str(name): _length(value, f"deductions.{name}", system_id)
        for name, value in _mapping(data["deductions"], "deductions").items()
    }
    lengths = {key: _length(data[key], key, system_id) for key in LENGTH_KEYS}

    return SystemConstants(
        system_id=system_id,
        material=material,
        reinforced=reinforced,
        bar_length_mm=bar_lengths,
        deductions=deductions,
        weld_allowance_mm=lengths["weld_allowance_mm"],
        kerf_mm=lengths["kerf_mm"],
        bar_end_trim_mm=lengths["bar_end_trim_mm"],
        steel_shortening_mm=lengths["steel_shortening_mm"],
        min_offcut_mm=lengths["min_offcut_mm"],
    )
