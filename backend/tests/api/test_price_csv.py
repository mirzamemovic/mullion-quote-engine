"""CSV price lists: exact amounts, Excel's habits, every problem listed (SAMPLE data only)."""

import uuid
from datetime import date

import pytest

from quote_engine.services import price_csv
from quote_engine.services.price_csv import CsvError, CsvRow

TODAY = date(2026, 11, 17)
SUPPLIERS = {"Sample Glass Ltd": uuid.uuid4(), "Sample Profiles": uuid.uuid4()}
HEADER = "kind,ref,colour,unit,amount,supplier,quoted_on,estimate"


def parse(text: str) -> list[CsvRow]:
    return price_csv.parse(text, SUPPLIERS, TODAY)


def problems(text: str) -> list[tuple[int, str]]:
    with pytest.raises(CsvError) as raised:
        parse(text)
    return [(p.row, p.column) for p in raised.value.problems]


@pytest.mark.parametrize(
    ("text", "cents"),
    [("21.60", 2160), ("21,60", 2160), ("21", 2100), ("0,5", 50), ("1234.05", 123405)],
)
def test_amounts_become_exact_cents(text: str, cents: int) -> None:
    assert price_csv.amount_cents(text) == cents


@pytest.mark.parametrize("text", ["", "-5", "1.234,50", "21.605", "abc", "1e3", "12 €"])
def test_unclear_amounts_are_refused(text: str) -> None:
    with pytest.raises(ValueError, match=r"21\.60"):
        price_csv.amount_cents(text)


def test_a_semicolon_file_from_excel_with_a_bom_reads_the_same() -> None:
    comma = f"{HEADER}\nglass,4-16-4,,m2,18.00,Sample Glass Ltd,2026-11-01,no\n"
    semicolon = comma.replace(",", ";").replace("18.00", "18,00")
    from_excel = ("﻿" + semicolon).encode("utf-8")

    assert parse(comma) == parse(price_csv.decode(from_excel))
    row = parse(comma)[0]
    assert (row.kind, row.ref, row.colour, row.unit) == ("glass", "4-16-4", None, "m2")
    assert (row.amount_cents, row.quoted_on, row.estimate) == (1800, date(2026, 11, 1), False)
    assert row.supplier == "Sample Glass Ltd"


def test_a_windows_1250_file_keeps_its_letters() -> None:
    text = f"{HEADER}\nsill,PVC 200 mm čćšžđ,white,m,16.00,Sample Profiles,,yes\n"

    row = parse(price_csv.decode(text.encode("cp1250")))[0]
    assert row.ref == "PVC 200 mm čćšžđ"
    assert row.estimate is True
    assert row.quoted_on == TODAY  # an empty date means today


def test_columns_may_come_in_any_order_and_any_case() -> None:
    text = "Supplier,Amount,Unit,Ref,Kind\nSample Glass Ltd,18,m2,4-16-4,glass\n"

    assert parse(text)[0].amount_cents == 1800


def test_every_problem_is_listed_with_its_row_and_column() -> None:
    text = "\n".join(
        [
            HEADER,
            "glass,4-16-4,,m2,18.00,Sample Glass Ltd,,",
            "glas,x,,m2,1,Sample Glass Ltd,,",  # unknown kind
            "profile,s/frame,purple,bar,1,Sample Profiles,,",  # unknown colour
            "glass,4-16-4,,m2,19.00,Sample Glass Ltd,,",  # the same price twice
            "hardware,pvc/tilt_turn_left,,piece,32,Sample Profiles,,",  # wrong unit
            "transport,lorry,,job,20,Sample Profiles,,",  # transport is flat or km
            "consumables,pvc,,piece,2.50,Nobody,,",  # unknown supplier
            "labour,pvc/fixed/small,,piece,15,Sample Profiles,32.13.2026,maybe",
        ]
    )

    assert problems(text) == [
        (3, "kind"),
        (4, "colour"),
        (5, "ref"),
        (6, "unit"),
        (7, "ref"),
        (8, "supplier"),
        (9, "quoted_on"),
        (9, "estimate"),
    ]


def test_missing_columns_and_empty_files_are_named() -> None:
    assert problems("kind,ref,unit\n") == [(1, "amount"), (1, "supplier")]
    assert problems("") == [(1, "")]


def test_blank_rows_are_skipped() -> None:
    text = f"{HEADER}\n\n,,,,,,,\nglass,4-16-4,,m2,18,Sample Glass Ltd,,\n"

    assert len(parse(text)) == 1


def test_files_over_the_size_limit_are_refused() -> None:
    with pytest.raises(CsvError):
        price_csv.decode(b"x" * (price_csv.MAX_BYTES + 1))


def test_an_export_reads_back_unchanged_and_never_runs_as_a_formula() -> None:
    rows = [
        CsvRow("glass", '=HYPERLINK("x")', None, "m2", 1800, "Sample Glass Ltd", TODAY, True),
        CsvRow("profile", "s/frame", "white", "bar", 2160, "Sample Profiles", TODAY),
    ]
    text = price_csv.to_csv(rows)

    assert "'=HYPERLINK" in text
    assert parse(text) == rows


def test_a_template_row_has_an_empty_amount() -> None:
    template = price_csv.to_csv(
        [CsvRow("glass", "4-16-4", None, "m2", None, "", TODAY)]
    ).splitlines()

    assert template[0] == HEADER
    assert template[1].split(",")[4] == ""


@pytest.mark.parametrize(
    ("kind", "ref", "unit"),
    [
        ("profile", "x/frame", "bar"),
        ("gasket", "x", "m"),
        ("glass", "4-16-4", "m2"),
        ("transport", "flat", "job"),
        ("transport", "km", "km"),
        ("transport", "bus", None),
        ("nonsense", "x", None),
    ],
)
def test_each_kind_has_its_unit(kind: str, ref: str, unit: str | None) -> None:
    assert price_csv.expected_unit(kind, ref) == unit
