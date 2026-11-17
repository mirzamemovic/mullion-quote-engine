"""Price lists as CSV, so a workshop can fill them in Excel or any spreadsheet.

Columns (any order, header row first): ``kind, ref, colour, unit, amount, supplier, quoted_on,
estimate``. ``amount`` is in the workshop's currency with up to two decimals, written ``21.60``
or ``21,60``; it becomes whole minor units (cents) exactly, never through a float.

- Reading accepts UTF-8 (with or without the BOM Excel writes) and Windows-1250, and either
  ``,`` or ``;`` between columns (Excel in Bosnian, Croatian or Serbian uses ``;``).
- Import is all or nothing: every row is checked, every problem is listed with its row number
  and column, and nothing changes unless all rows are good.
- Writing escapes any cell a spreadsheet would run as a formula (``= + - @``), so an exported
  list can be opened safely; reading removes that escape again.
"""

import csv
import io
import re
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime

from quote_engine.engine.model import Colour

COLUMNS = ("kind", "ref", "colour", "unit", "amount", "supplier", "quoted_on", "estimate")
REQUIRED = ("kind", "ref", "unit", "amount", "supplier")
MAX_BYTES = 1_000_000
MAX_ROWS = 2000

# The unit each kind of price is quoted in (the engine refuses any other).
KIND_UNITS: Mapping[str, str] = {
    "profile": "bar",
    "steel": "bar",
    "gasket": "m",
    "hardware": "set",
    "glass": "m2",
    "consumables": "piece",
    "labour": "piece",
    "installation": "piece",
    "sill": "m",
    "shutter": "m2",
    "screen": "m2",
}
TRANSPORT_UNITS: Mapping[str, str] = {"flat": "job", "km": "km"}

_AMOUNT = re.compile(r"^\d{1,9}(?:[.,]\d{1,2})?$")
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
_YES = {"yes", "y", "true", "1", "da", "x"}
_NO = {"no", "n", "false", "0", "ne", ""}


def expected_unit(kind: str, ref: str) -> str | None:
    """The unit a price of this kind must use, or ``None`` for an unknown kind."""
    if kind == "transport":
        return TRANSPORT_UNITS.get(ref)
    return KIND_UNITS.get(kind)


@dataclass(frozen=True)
class CsvRow:
    """One price, as read from or written to a CSV file."""

    kind: str
    ref: str
    colour: str | None
    unit: str
    amount_cents: int | None  # None only in a template row still to be filled in
    supplier: str
    quoted_on: date
    estimate: bool = False


@dataclass(frozen=True)
class CsvProblem:
    row: int  # the line number a spreadsheet shows, header = 1
    column: str
    message: str


class CsvError(Exception):
    """The file cannot be imported; ``problems`` lists every reason found."""

    def __init__(self, problems: list[CsvProblem]) -> None:
        self.problems = problems
        super().__init__(f"{len(problems)} problem(s) in the file")


def decode(data: bytes) -> str:
    """The text of a CSV file: UTF-8 (with or without a BOM), else Windows-1250."""
    if len(data) > MAX_BYTES:
        raise CsvError([CsvProblem(0, "", f"the file is larger than {MAX_BYTES // 1000} kB")])
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1250", errors="replace")


def amount_cents(text: str) -> int:
    """``"21.60"`` or ``"21,60"`` as 2160 cents, exactly. Raises ``ValueError`` otherwise."""
    value = text.strip().replace(" ", "")
    if not _AMOUNT.match(value):
        raise ValueError("write the amount like 21.60 or 21,60, with no thousands separator")
    whole, _, fraction = value.replace(",", ".").partition(".")
    return int(whole) * 100 + int(fraction.ljust(2, "0") or "0")


def cents_text(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _unescape(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith("'") and cell[1:2] in _FORMULA_START:
        return cell[1:]
    return cell


def _escape(cell: str) -> str:
    return f"'{cell}" if cell.startswith(_FORMULA_START) else cell


def _date(text: str, today: date) -> date:
    value = text.strip()
    if not value:
        return today
    for pattern in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%Y."):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    raise ValueError("write the date like 2026-11-17 or 17.11.2026")


def parse(text: str, suppliers: Mapping[str, uuid.UUID], today: date) -> list[CsvRow]:
    """Every row of a CSV price list, or ``CsvError`` listing every problem.

    ``suppliers`` maps supplier names (any case) to their ids; a row must name one of them.
    """
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        raise CsvError([CsvProblem(1, "", "the file is empty")])
    delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = [h.strip().lower() for h in next(reader)]
    absent = [c for c in REQUIRED if c not in header]
    if absent:
        raise CsvError([CsvProblem(1, c, "this column is missing") for c in absent])
    index = {name: header.index(name) for name in COLUMNS if name in header}
    by_name = {name.strip().lower(): name for name in suppliers}

    rows: list[CsvRow] = []
    problems: list[CsvProblem] = []
    seen: dict[tuple[str, str, str | None], int] = {}
    for number, cells in enumerate(reader, start=2):
        if not any(cell.strip() for cell in cells):
            continue
        if number - 1 > MAX_ROWS:
            problems.append(CsvProblem(number, "", f"at most {MAX_ROWS} rows"))
            break

        def cell(name: str, cells: list[str] = cells) -> str:
            i = index.get(name)
            return _unescape(cells[i]) if i is not None and i < len(cells) else ""

        before = len(problems)
        kind, ref, unit = cell("kind").lower(), cell("ref"), cell("unit").lower()
        colour = cell("colour").lower() or None
        want = expected_unit(kind, ref) if kind else None
        if not kind:
            problems.append(CsvProblem(number, "kind", "required"))
        elif want is None and kind != "transport":
            problems.append(CsvProblem(number, "kind", f"unknown kind '{kind}'"))
        if not ref:
            problems.append(CsvProblem(number, "ref", "required"))
        elif kind == "transport" and want is None:
            problems.append(CsvProblem(number, "ref", "transport is 'flat' or 'km'"))
        if want is not None and unit != want:
            problems.append(CsvProblem(number, "unit", f"{kind} is priced per {want}"))
        if colour is not None and colour not in {c.value for c in Colour}:
            problems.append(CsvProblem(number, "colour", f"unknown colour '{colour}'"))
        cents = 0
        try:
            cents = amount_cents(cell("amount"))
        except ValueError as error:
            problems.append(CsvProblem(number, "amount", str(error)))
        supplier = by_name.get(cell("supplier").lower())
        if supplier is None:
            problems.append(
                CsvProblem(number, "supplier", "unknown supplier: add it under Suppliers first")
            )
        quoted_on = today
        try:
            quoted_on = _date(cell("quoted_on"), today)
        except ValueError as error:
            problems.append(CsvProblem(number, "quoted_on", str(error)))
        flag = cell("estimate").lower()
        if flag not in _YES | _NO:
            problems.append(CsvProblem(number, "estimate", "write yes or no"))
        key = (kind, ref, colour)
        if key in seen:
            problems.append(
                CsvProblem(number, "ref", f"the same price is already on row {seen[key]}")
            )
        seen.setdefault(key, number)
        if len(problems) == before and supplier is not None:
            rows.append(CsvRow(kind, ref, colour, unit, cents, supplier, quoted_on, flag in _YES))
    if problems:
        raise CsvError(problems)
    return rows


def to_csv(rows: Iterable[CsvRow]) -> str:
    """A CSV file (comma-separated, UTF-8) that ``parse`` reads back unchanged."""
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow(
            _escape(value)
            for value in (
                row.kind,
                row.ref,
                row.colour or "",
                row.unit,
                "" if row.amount_cents is None else cents_text(row.amount_cents),
                row.supplier,
                row.quoted_on.isoformat(),
                "yes" if row.estimate else "no",
            )
        )
    return out.getvalue()
