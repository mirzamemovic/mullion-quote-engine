"""PDF words and number formats: the same as the app shows, in English and Bosnian."""

import json
import re
from datetime import date
from pathlib import Path

import pytest

from quote_engine.pdf import labels

FRONTEND = Path(__file__).parents[3] / "frontend" / "src"
NBSP = chr(0xA0)
MINUS = chr(0x2212)
TIMES = chr(0xD7)


@pytest.mark.parametrize(
    ("cents", "lang", "currency", "expected"),
    [
        pytest.param(123_456, "en", "EUR", "€1,234.56", id="english-euros"),
        pytest.param(123_456, "bs", "EUR", f"1.234,56{NBSP}€", id="bosnian-euros"),
        pytest.param(123_456, "en", "BAM", f"1,234.56{NBSP}KM", id="english-marks"),
        pytest.param(5, "en", "EUR", "€0.05", id="cents-only"),
        pytest.param(-1_200, "en", "EUR", f"{MINUS}€12.00", id="negative-has-a-real-minus"),
        pytest.param(100_000_000_00, "bs", "RSD", f"100.000.000,00{NBSP}RSD", id="large"),
    ],
)
def test_money(cents: int, lang: str, currency: str, expected: str) -> None:
    assert labels.money(cents, lang, currency) == expected


@pytest.mark.parametrize(
    ("bp", "lang", "expected"),
    [(2500, "en", "25"), (1850, "bs", "18,5"), (1805, "en", "18.05"), (0, "en", "0")],
)
def test_percent(bp: int, lang: str, expected: str) -> None:
    assert labels.percent(bp, lang) == f"{expected}{NBSP}%"


def test_dates_as_the_trade_writes_them() -> None:
    assert labels.day(date(2026, 11, 28), "en") == "28 Nov 2026"
    assert labels.day(date(2026, 1, 5), "bs") == "5.1.2026."


def test_engine_names_in_the_workshops_words() -> None:
    assert labels.workshop_label("frame/white", "bs") == "štok · bijela"
    assert labels.workshop_label("false mullion steel horizontal", "bs") == (
        "štulp armatura horizontalno"
    )
    assert labels.workshop_label("frame/foil_both_sides", "en") == "frame · foil both sides"
    assert labels.workshop_label("a new part", "bs") == "a new part"
    assert labels.cut_label("Kitchen frame top", "Kitchen", "bs") == "Kitchen · štok gore"
    assert labels.cut_label("odd key", "Kitchen", "en") == "odd key"


def test_sentences_fill_their_values() -> None:
    assert labels.text("en", "bars", count=3, length=6500) == f"3 {TIMES} 6500 mm"
    assert labels.text("bs", "vat", rate="18 %") == "PDV 18 %"
    assert labels.size(1200, 1300) == f"1200{NBSP}{TIMES}{NBSP}1300"


def test_unknown_language_reads_as_english() -> None:
    assert labels.language("sq") == "en"
    assert labels.text("sq", "quote") == "Quote"


def test_both_languages_have_every_sentence() -> None:
    assert labels.TEXT["en"].keys() == labels.TEXT["bs"].keys()
    for table in (labels.TYPES, labels.OPENINGS, labels.COLOURS, labels.EXTRA_KINDS):
        assert table["en"].keys() == table["bs"].keys()


def _frontend_json(lang: str) -> dict[str, dict[str, str]]:
    path = FRONTEND / "i18n" / f"{lang}.json"
    if not path.exists():
        pytest.skip("the frontend is not in this checkout")
    data: dict[str, dict[str, str]] = json.loads(path.read_text(encoding="utf-8"))
    return data


@pytest.mark.parametrize("lang", ["en", "bs"])
def test_names_match_the_app(lang: str) -> None:
    """A window type, opening or colour is called the same on paper as on screen."""
    app = _frontend_json(lang)
    assert labels.TYPES[lang] == app["types"]
    for name, table in (("openings", labels.OPENINGS), ("colours", labels.COLOURS)):
        assert {k: v.lower() for k, v in table[lang].items()} == {
            k: v.lower() for k, v in app[name].items()
        }


def test_piece_words_match_the_app() -> None:
    source = FRONTEND / "lib" / "labels.ts"
    if not source.exists():
        pytest.skip("the frontend is not in this checkout")
    text = source.read_text(encoding="utf-8")
    block = re.search(r"const WORDS_BS[^{]*\{(.*?)\n\};", text, re.DOTALL)
    assert block is not None
    words = dict(re.findall(r'(\w+): "([^"]*)"', block[1]))
    assert words == labels._WORDS["bs"]
