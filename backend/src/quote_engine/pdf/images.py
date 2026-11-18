"""Recognise a logo image from its first bytes, without decoding it.

A workshop logo is checked twice: when it is uploaded, and again when a PDF is made. Only PNG
and JPEG are accepted, at most ``MAX_BYTES`` long and ``MAX_SIDE`` pixels on each side, so a
small file that claims to be a huge picture (a "decompression bomb") is refused before any
library tries to unpack it.
"""

from dataclasses import dataclass

MAX_BYTES = 300 * 1024
MAX_SIDE = 2000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_START = b"\xff\xd8\xff"
# JPEG markers C0-CF are frame headers that carry the size, except these three.
_NOT_FRAMES = {0xC4, 0xC8, 0xCC}


@dataclass(frozen=True)
class ImageInfo:
    media_type: str
    width: int
    height: int


def _png(data: bytes) -> ImageInfo | None:
    # Signature, then the IHDR chunk: length (4), b"IHDR", width (4), height (4).
    if len(data) < 24 or data[12:16] != b"IHDR":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return ImageInfo("image/png", width, height)


def _jpeg(data: bytes) -> ImageInfo | None:
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return None
        marker = data[i + 1]
        if marker == 0xFF:  # fill byte
            i += 1
            continue
        if marker == 0x01 or 0xD0 <= marker <= 0xD8:  # markers without a length
            i += 2
            continue
        if marker in (0xD9, 0xDA):  # end of image or start of scan before any frame header
            return None
        length = int.from_bytes(data[i + 2 : i + 4], "big")
        if length < 2:
            return None
        if 0xC0 <= marker <= 0xCF and marker not in _NOT_FRAMES:
            if i + 9 > len(data):
                return None
            height = int.from_bytes(data[i + 5 : i + 7], "big")
            width = int.from_bytes(data[i + 7 : i + 9], "big")
            return ImageInfo("image/jpeg", width, height)
        i += 2 + length
    return None


def sniff(data: bytes) -> ImageInfo | None:
    """The type and size of a PNG or JPEG, or ``None`` for anything else."""
    if data.startswith(PNG_SIGNATURE):
        return _png(data)
    if data.startswith(JPEG_START):
        return _jpeg(data)
    return None


def problem(data: bytes) -> str | None:
    """Why ``data`` cannot be a logo, or ``None`` when it can."""
    if not data:
        return "the file is empty"
    if len(data) > MAX_BYTES:
        return f"the logo must be at most {MAX_BYTES // 1024} KB"
    info = sniff(data)
    if info is None:
        return "the logo must be a PNG or JPEG image"
    if not (0 < info.width <= MAX_SIDE and 0 < info.height <= MAX_SIDE):
        return f"the logo must be at most {MAX_SIDE} x {MAX_SIDE} pixels"
    return None
