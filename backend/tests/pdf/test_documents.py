"""The PDF service's own rules: a sliding-minute limit per workshop and safe file names."""

import uuid

import pytest

from quote_engine.services import documents


def test_the_limit_counts_one_minute_per_workshop() -> None:
    limiter = documents._Limiter()
    shop, other = uuid.uuid4(), uuid.uuid4()
    limiter.take(shop, 0.0, 2)
    limiter.take(shop, 10.0, 2)
    with pytest.raises(documents.PdfLimitError, match="at most 2 PDFs a minute"):
        limiter.take(shop, 59.0, 2)
    limiter.take(other, 59.0, 2)
    limiter.take(shop, 60.0, 2)  # the first one is a minute old now


@pytest.mark.parametrize(
    ("kind", "number", "expected"),
    [
        ("quote", "2026-0007", "quote-2026-0007-v3.pdf"),
        ("ponuda", 'A/1 "x"\r\n', "ponuda-A-1-x-v3.pdf"),
        ("radni-nalog", "Čelik 7", "radni-nalog-elik-7-v3.pdf"),
    ],
)
def test_file_names_are_safe_in_a_header(kind: str, number: str, expected: str) -> None:
    assert documents.filename(kind, number, 3) == expected
