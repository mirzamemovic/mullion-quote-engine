"""The renderer: autoescaped templates, nothing fetched but bundled fonts and checked logos.

Laying out a real PDF needs WeasyPrint's system libraries (Pango). Those tests skip where the
libraries are missing (Windows) and run in the Docker image and in CI (PLAN.md section 10).
"""

import base64
import io

import pytest
from pypdf import PdfReader

from quote_engine.pdf import render
from tests.pdf.builders import client_document, workshop_document
from tests.pdf.test_images import jpeg, png, real_png

FONT = next(iter(render.FONTS))


def test_bundled_fonts_load() -> None:
    body, media_type = render.resolve(FONT.as_uri())
    assert media_type == "font/woff2"
    assert body[:4] == b"wOF2"


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("http://169.254.169.254/latest/meta-data/", id="cloud-metadata"),
        pytest.param("https://example.com/logo.png", id="https"),
        pytest.param("ftp://example.com/x", id="ftp"),
        pytest.param("file:///etc/passwd", id="server-file"),
        pytest.param((render.ASSETS / "fonts" / "OFL.txt").as_uri(), id="bundled-non-font"),
        pytest.param(FONT.as_uri() + "/../../../render.py", id="walks-out-of-the-folder"),
        pytest.param("fonts/noto-sans-latin.woff2", id="relative"),
        pytest.param("data:text/html;base64,PHNjcmlwdD4=", id="data-html"),
        pytest.param("data:image/svg+xml;base64,PHN2Zz4=", id="data-svg"),
        pytest.param("data:image/png;base64,not*base64", id="bad-base64"),
        pytest.param(
            "data:image/png;base64," + base64.b64encode(jpeg(10, 10)).decode(),
            id="type-does-not-match-bytes",
        ),
        pytest.param(
            "data:image/png;base64," + base64.b64encode(png(9000, 9000)).decode(),
            id="decompression-bomb",
        ),
    ],
)
def test_everything_else_is_refused(url: str) -> None:
    with pytest.raises(render.RefusedUrlError) as refused:
        render.resolve(url)
    assert "base64" not in str(refused.value)


def test_a_checked_logo_loads_as_a_data_url() -> None:
    logo = render.logo_url(png(300, 100))
    assert logo is not None
    assert render.resolve(logo) == (png(300, 100), "image/png")
    assert render.logo_url(b"GIF89a") is None


def test_css_strings_cannot_break_out_of_the_style_element() -> None:
    value = render.css_string('Ana "B" \\ </style><script>{}')
    assert value[0] == value[-1] == '"'
    assert not set(value[1:-1]) & set('"<>{};')
    assert render.css_string("Ponuda 2026-007") == '"Ponuda 2026-007"'


def test_only_drawings_go_in_as_markup() -> None:
    with pytest.raises(ValueError, match="only drawings"):
        render.drawing("<img src=x onerror=alert(1)>")


def test_client_values_are_escaped() -> None:
    doc = client_document()
    hostile = '<img src="http://evil.example/x"> & "quotes"'
    doc = type(doc)(**{**doc.__dict__, "client_name": hostile, "client_place": "</p><h1>x</h1>"})
    page = render.html("quote.html", doc, "Quote 2026-007")

    assert "evil.example" in page
    assert '<img src="http://evil.example' not in page
    assert "&lt;img src=&#34;http://evil.example/x&#34;&gt; &amp; &#34;quotes&#34;" in page
    assert "&lt;/p&gt;&lt;h1&gt;x&lt;/h1&gt;" in page


def test_pages_have_their_parts() -> None:
    quote = render.html("quote.html", client_document("bs"), "Ponuda 2026-007")
    assert '<html lang="bs">' in quote
    assert "<title>Ponuda 2026-007</title>" in quote
    assert quote.count('<svg xmlns="http://www.w3.org/2000/svg"') == 1
    assert "Prihvata klijent" in quote
    assert "Primjer radionice" not in quote

    sheet = render.html("workshop.html", workshop_document(is_demo=True), "Workshop sheet 2026-007")
    assert "Sample workshop with invented data" in sheet
    assert 'class="strip"' in sheet
    assert "€" not in sheet


def _pdf_text(template: str, document: object, title: str) -> str:
    try:
        data = render.pdf(template, document, title)
    except render.PdfUnavailableError:
        pytest.skip("WeasyPrint's system libraries (Pango) are not installed here")
    assert data.startswith(b"%PDF-")
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(data)).pages)


def test_client_pdf_has_the_total_and_local_letters() -> None:
    text = _pdf_text("quote.html", client_document("bs"), "Ponuda 2026-007")
    flat = text.replace(chr(0xA0), " ")
    assert "Ponuda 2026-007" in flat
    assert "1.150,50" in flat
    assert "Važi do" in flat
    assert "Plaćanje" in flat
    assert "Strana 1 od 1" in flat


def test_workshop_pdf_has_the_formulas() -> None:
    text = _pdf_text("workshop.html", workshop_document("bs"), "Radni nalog 2026-007")
    assert "Plan sječenja" in text
    assert "Krojna lista" in text
    assert "=" in text


def test_client_pdf_prints_the_logo() -> None:
    doc = client_document()
    logo = render.logo_url(real_png(240, 80))
    doc = type(doc)(**{**doc.__dict__, "header": type(doc.header)(doc.header.name, (), logo)})
    try:
        data = render.pdf("quote.html", doc, "Quote 2026-007")
    except render.PdfUnavailableError:
        pytest.skip("WeasyPrint's system libraries (Pango) are not installed here")
    assert len(PdfReader(io.BytesIO(data)).pages[0].images) == 1
