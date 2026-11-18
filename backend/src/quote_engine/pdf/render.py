"""Fill the PDF templates and lay them out with WeasyPrint (PLAN.md section 8).

Two rules keep a PDF from becoming a way into the server:
- Every template value is autoescaped, so a client called ``<img src=...>`` prints as text.
- WeasyPrint may load only the bundled fonts and a logo passed in as a ``data:`` URL that is a
  checked PNG or JPEG. Every other URL (http, other files, anything else) is refused, so a PDF
  can neither read the server's files nor call another host.

WeasyPrint needs the Pango text library, which Windows lacks. It is imported only when a PDF is
made, and a missing library raises ``PdfUnavailableError`` instead of stopping the app.
"""

import base64
import binascii
import re
from functools import cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jinja2 import Environment, PackageLoader, StrictUndefined
from markupsafe import Markup

from quote_engine.pdf import images, labels

ASSETS = Path(__file__).parent / "assets"
FONTS = {
    (ASSETS / "fonts" / name).resolve(): "font/woff2"
    for name in ("noto-sans-latin.woff2", "noto-sans-latin-ext.woff2")
}
_DATA_URL = re.compile(r"data:(image/png|image/jpeg);base64,([A-Za-z0-9+/]+={0,2})")
_SVG_START = '<svg xmlns="http://www.w3.org/2000/svg"'


class PdfUnavailableError(RuntimeError):
    """This server cannot lay out PDFs: WeasyPrint's system libraries are missing."""


class RefusedUrlError(ValueError):
    """A page asked for something other than a bundled font or a checked logo."""


def logo_url(data: bytes) -> str | None:
    """A checked logo as a ``data:`` URL for the template, or ``None`` if it is not one."""
    if images.problem(data) is not None:
        return None
    info = images.sniff(data)
    assert info is not None  # noqa: S101 - images.problem() returned None, so it was sniffed
    return f"data:{info.media_type};base64,{base64.b64encode(data).decode('ascii')}"


def resolve(url: str) -> tuple[bytes, str]:
    """The bytes and media type behind ``url`` when the page may load it.

    Raises ``RefusedUrlError`` for anything else. The message never repeats the URL, which may
    hold a whole image.
    """
    if url.startswith("data:"):
        match = _DATA_URL.fullmatch(url)
        if match is not None:
            try:
                body = base64.b64decode(match[2], validate=True)
            except binascii.Error:
                body = b""
            info = images.sniff(body)
            if images.problem(body) is None and info is not None and info.media_type == match[1]:
                return body, info.media_type
        raise RefusedUrlError("refused a data URL that is not a checked logo")
    if url.startswith("file:"):
        try:
            path = Path.from_uri(url).resolve()
        except ValueError:
            path = None
        media_type = FONTS.get(path) if path is not None else None
        if path is not None and media_type is not None:
            return path.read_bytes(), media_type
    raise RefusedUrlError(f"refused a {urlsplit(url).scheme or 'relative'} URL")


def css_string(value: str) -> Markup:
    """``value`` as a quoted CSS string that is safe inside a ``<style>`` element."""
    out = []
    for char in value:
        if char.isalnum() or char in " .,:-":
            out.append(char)
        else:
            out.append(f"\\{ord(char):x} ")
    return Markup('"' + "".join(out) + '"')  # noqa: S704 - every other character is escaped


def drawing(value: str) -> Markup:
    """A window drawing from ``pdf.drawing``, which escapes its own text, inserted as markup."""
    if not value.startswith(_SVG_START):
        raise ValueError("only drawings made by quote_engine.pdf.drawing can be inserted")
    return Markup(value)  # noqa: S704 - built by pdf.drawing, which escapes every text value


@cache
def environment() -> Environment:
    env = Environment(
        loader=PackageLoader("quote_engine.pdf", "templates"),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        auto_reload=False,
    )
    env.filters["css_string"] = css_string
    env.filters["drawing"] = drawing
    return env


def html(template: str, document: Any, title: str) -> str:
    """The page as HTML. ``document`` is a ``ClientQuote`` or a ``WorkshopSheet``."""
    lang = labels.language(document.lang)

    def t(key: str, **values: object) -> str:
        return labels.text(lang, key, **values)

    footer = labels.text(lang, "sample") if document.sample else title
    return (
        environment().get_template(template).render(doc=document, t=t, title=title, footer=footer)
    )


@cache
def _weasyprint() -> Any:
    try:
        import weasyprint
    except OSError as error:
        raise PdfUnavailableError("PDFs cannot be made on this server") from error
    return weasyprint


@cache
def _fetcher() -> type:
    from weasyprint.urls import URLFetcher, URLFetcherResponse

    class BundledOnly(URLFetcher):  # type: ignore[misc]
        """Serves the bundled fonts and checked logos; refuses every other URL."""

        def fetch(self, url: str, headers: object = None) -> Any:
            body, media_type = resolve(url)
            return URLFetcherResponse(url, body, {"Content-Type": media_type})

    return BundledOnly


def pdf(template: str, document: Any, title: str) -> bytes:
    """The page laid out as a PDF."""
    weasyprint = _weasyprint()
    page = weasyprint.HTML(
        string=html(template, document, title),
        base_url=ASSETS.as_uri() + "/",
        url_fetcher=_fetcher()(),
    )
    data: bytes = page.write_pdf()
    return data
