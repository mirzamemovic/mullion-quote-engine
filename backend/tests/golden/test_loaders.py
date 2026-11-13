"""The golden-test loaders read the formats in ``README.md`` (checked on temporary sample files)."""

from datetime import date
from pathlib import Path

from quote_engine.engine.model import Colour, Opening, Role
from quote_engine.engine.prices import PriceKey, PriceUnit
from quote_engine.engine.pricing import ExtraKind, Installation
from tests.engine.conftest import SAMPLE_SHEET
from tests.golden.loaders import job_files, load_job, load_private_prices, load_system

JOB = """\
id: job-sample
note: "SAMPLE - NOT REAL"
system: sample-not-real
price_list_date: 2026-01-01
positions:
  - ref: P1
    type: single_sash_tilt_turn
    width_mm: 800
    height_mm: 1400
    qty: 2
    colour: white
    glass: "4-16-4"
    openings: [tilt_turn_right]
installation:
  P1: {ral: true}
extras:
  - {kind: sill, ref: S1, qty: 2, length_mm: 900, colour: white}
transport_km: 40
discount_bp: 500
expected:
  cuts:
    - {ref: P1, role: frame, label: frame top, length_mm: 806, qty: 2}
  bars_used: {frame/white: 2}
  billed_total_cents: 54000
tolerance: {cut_mm: 1, total_bp: 300}
"""

PRICES = """\
valid_from: 2026-01-01
settings: {margin_bp: 2500, vat_registered: false, vat_bp: 1800, advance_bp: 5000,
  glass_min_area_mm2: 300000, gasket_extra_bp: 500, small_max_mm2: 500000,
  standard_max_mm2: 2000000}
prices:
  - {kind: profile, ref: frame, colour: white, amount_cents: 1111, unit: bar,
     supplier: Sample Supplier, quoted_on: 2025-12-30}
"""


def test_no_job_files_in_a_missing_or_empty_folder(tmp_path: Path) -> None:
    assert job_files(tmp_path / "missing") == []
    assert job_files(tmp_path) == []


def test_job_file_is_read(tmp_path: Path) -> None:
    (tmp_path / "job-sample.yaml").write_text(JOB, encoding="utf-8")

    (path,) = job_files(tmp_path)
    job = load_job(path)

    assert (job.id, job.system, job.price_list_date) == (
        "job-sample",
        "sample-not-real",
        date(2026, 1, 1),
    )
    (p1,) = job.positions
    assert (p1.width_mm, p1.qty, p1.colour, p1.openings) == (
        800,
        2,
        Colour.WHITE,
        (Opening.TILT_TURN_RIGHT,),
    )
    assert job.installation == {"P1": Installation(ral=True)}
    assert [(e.kind, e.length_mm, e.colour) for e in job.extras] == [
        (ExtraKind.SILL, 900, Colour.WHITE)
    ]
    assert (job.transport_km, job.discount.bp) == (40, 500)
    assert [(c.role, c.label, c.length_mm) for c in job.cuts] == [
        (Role.FRAME.value, "frame top", 806)
    ]
    assert job.bars_used == {"frame/white": 2}
    assert (job.billed_total_cents, job.cut_tolerance_mm, job.total_tolerance_bp) == (
        54_000,
        1,
        300,
    )


def test_system_sheet_is_read_when_present(tmp_path: Path) -> None:
    assert load_system("sample-not-real", tmp_path) is None
    (tmp_path / "sample-not-real.yaml").write_text(
        SAMPLE_SHEET.read_text(encoding="utf-8"), encoding="utf-8"
    )

    constants = load_system("sample-not-real", tmp_path)

    assert constants is not None
    assert constants.system_id == "sample-not-real"


def test_private_prices_are_read_when_present(tmp_path: Path) -> None:
    assert load_private_prices(date(2026, 1, 1), tmp_path) is None
    (tmp_path / "prices-2026-01-01.yaml").write_text(PRICES, encoding="utf-8")

    private = load_private_prices(date(2026, 1, 1), tmp_path)

    assert private is not None
    assert private.settings.margin_bp == 2500
    assert private.settings.vat_registered is False
    price = private.book.price(PriceKey("profile", "frame", Colour.WHITE), PriceUnit.BAR)
    assert (price.amount_cents, price.supplier, price.quoted_on) == (
        1111,
        "Sample Supplier",
        date(2025, 12, 30),
    )


def test_private_folder_is_ignored_by_git() -> None:
    gitignore = Path(__file__).parents[3] / ".gitignore"

    assert "backend/tests/golden/private/" in gitignore.read_text(encoding="utf-8").splitlines()
