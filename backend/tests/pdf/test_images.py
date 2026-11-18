"""Logo images are recognised from their first bytes; oversized pictures are refused unopened."""

import zlib

import pytest

from quote_engine.pdf import images


def png(width: int, height: int) -> bytes:
    """A PNG signature and IHDR chunk; enough for the checks, which never decode pixels."""
    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00"
    return images.PNG_SIGNATURE + len(ihdr).to_bytes(4, "big") + b"IHDR" + ihdr + b"\0" * 4


def real_png(width: int, height: int) -> bytes:
    """A complete grey PNG that image libraries can decode, for tests that render it."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data).to_bytes(4, "big")
        return len(data).to_bytes(4, "big") + kind + data + crc

    rows = b"".join(b"\x00" + b"\x80\x80\x80" * width for _ in range(height))
    header = width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes([8, 2, 0, 0, 0])
    return (
        images.PNG_SIGNATURE
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def jpeg(width: int, height: int, *, table_first: bool = False) -> bytes:
    app0 = b"\xff\xe0" + (16).to_bytes(2, "big") + b"JFIF\0" + b"\0" * 9
    dht = b"\xff\xc4" + (5).to_bytes(2, "big") + b"\0\0\0"
    sof = (
        b"\xff\xc0"
        + (17).to_bytes(2, "big")
        + b"\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03"
        + b"\0" * 9
    )
    return b"\xff\xd8" + app0 + (dht if table_first else b"") + sof + b"\xff\xd9"


def test_png_size() -> None:
    assert images.sniff(png(320, 120)) == images.ImageInfo("image/png", 320, 120)
    assert images.problem(png(320, 120)) is None
    assert images.sniff(real_png(30, 10)) == images.ImageInfo("image/png", 30, 10)


@pytest.mark.parametrize("table_first", [False, True], ids=["plain", "table-before-frame"])
def test_jpeg_size(table_first: bool) -> None:
    data = jpeg(640, 200, table_first=table_first)
    assert images.sniff(data) == images.ImageInfo("image/jpeg", 640, 200)
    assert images.problem(data) is None


@pytest.mark.parametrize(
    ("data", "reason"),
    [
        pytest.param(b"", "empty", id="empty"),
        pytest.param(b"GIF89a" + b"\0" * 20, "PNG or JPEG", id="gif"),
        pytest.param(b"<svg xmlns='http://www.w3.org/2000/svg'/>", "PNG or JPEG", id="svg"),
        pytest.param(images.PNG_SIGNATURE + b"\0" * 4, "PNG or JPEG", id="truncated-png"),
        pytest.param(b"\xff\xd8\xff\xda\0\x02", "PNG or JPEG", id="jpeg-without-frame"),
        pytest.param(png(20_000, 20_000), "pixels", id="decompression-bomb"),
        pytest.param(png(0, 10), "pixels", id="no-width"),
        pytest.param(png(10, 10) + b"\0" * images.MAX_BYTES, "KB", id="too-long"),
    ],
)
def test_refused(data: bytes, reason: str) -> None:
    problem = images.problem(data)
    assert problem is not None
    assert reason in problem
