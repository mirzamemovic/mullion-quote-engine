"""Window drawings for the PDFs, as SVG markup.

The same picture as the app's ``WindowDrawing.tsx``:
- the window is seen from inside;
- frame and sash corners are 45° mitres, and a fixed mullion butts at 90°;
- the opening symbol's point is on the hinge side, dashed lines show tilt, and the handle sits
  on the other side.

Coordinates are whole units in a box 1000 wide on the longer side, so the markup is the same on
every run and line weights look even at any print size. Text in the markup is escaped here,
because the templates insert it as is.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape

FIELDS = {
    "single_sash_tilt_turn": 1,
    "two_field_t_mullion": 2,
    "two_sash_false_mullion": 2,
    "fixed": 1,
    "balcony_door_tilt_turn": 1,
}

INK = "#23272b"
FRAME = "#eef0f0"
FOIL = "#b9c0c4"
GLASS = "#dbe5f7"


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int


def field_count(construction_type: str) -> int:
    return FIELDS.get(construction_type, 1)


def _ring(box: Box, t: int, fill: str) -> str:
    """A ring of profile ``t`` wide inside ``box``, its four corners mitred at 45°."""
    x, y, w, h = box.x, box.y, box.w, box.h
    outer = f"M{x},{y}h{w}v{h}h{-w}z"
    inner = f"M{x + t},{y + t}v{h - 2 * t}h{w - 2 * t}v{-(h - 2 * t)}z"
    mitres = (
        f"M{x},{y}L{x + t},{y + t}"
        f"M{x + w},{y}L{x + w - t},{y + t}"
        f"M{x},{y + h}L{x + t},{y + h - t}"
        f"M{x + w},{y + h}L{x + w - t},{y + h - t}"
    )
    return (
        f'<path d="{outer}{inner}" fill="{fill}" fill-rule="evenodd"/>'
        f'<path d="{mitres}" fill="none"/>'
    )


def _opening_marks(box: Box, opening: str, stroke: int) -> str:
    if opening == "fixed":
        return ""
    x, y, w, h = box.x, box.y, box.w, box.h
    hinge_left = opening.endswith("_left")
    hinge_x = x if hinge_left else x + w
    handle_x = x + w if hinge_left else x
    marks = f'<path d="M{handle_x},{y}L{hinge_x},{y + h // 2}L{handle_x},{y + h}" fill="none"/>'
    if opening.startswith("tilt_turn"):
        dash = f"{stroke * 3} {stroke * 2}"
        marks += (
            f'<path d="M{x},{y}L{x + w // 2},{y + h}L{x + w},{y}" fill="none" '
            f'stroke-dasharray="{dash}"/>'
        )
    handle_w = max(stroke, w * 35 // 1000)
    handle_h = max(stroke * 3, h * 12 // 100)
    handle_left = handle_x - handle_w * 22 // 10 if hinge_left else handle_x + handle_w * 12 // 10
    marks += (
        f'<rect x="{handle_left}" y="{y + h // 2 - handle_h // 2}" width="{handle_w}" '
        f'height="{handle_h}" rx="{handle_w // 2}" fill="{INK}" stroke="none"/>'
    )
    return marks


def window_svg(
    construction_type: str,
    width_mm: int,
    height_mm: int,
    openings: Sequence[str],
    colour: str,
    *,
    title: str = "",
    stroke: int = 10,
) -> str:
    """One window as an ``<svg>`` element. ``stroke`` is in drawing units (1000 = longer side)."""
    longest = max(width_mm, height_mm, 1)
    w = max(width_mm * 1000 // longest, 200)
    h = max(height_mm * 1000 // longest, 200)
    pad = stroke * 2
    t = min(w, h) * 75 // 1000
    fill = FOIL if colour == "foil_both_sides" else FRAME
    frame = Box(pad, pad, w, h)
    inner = Box(pad + t, pad + t, w - 2 * t, h - 2 * t)
    count = field_count(construction_type)
    mullion = t * 9 // 10 if construction_type == "two_field_t_mullion" else 0
    field_w = (inner.w - mullion) // count
    sash = t * 8 // 10

    parts = [_ring(frame, t, fill)]
    if mullion:
        parts.append(
            f'<rect x="{inner.x + field_w}" y="{inner.y}" width="{mullion}" '
            f'height="{inner.h}" fill="{fill}"/>'
        )
    for i in range(count):
        field = Box(inner.x + i * (field_w + mullion), inner.y, field_w, inner.h)
        opening = openings[i] if i < len(openings) else "fixed"
        glass = (
            field
            if opening == "fixed"
            else Box(field.x + sash, field.y + sash, field.w - 2 * sash, field.h - 2 * sash)
        )
        parts.append(
            f'<rect x="{glass.x}" y="{glass.y}" width="{glass.w}" height="{glass.h}" '
            f'fill="{GLASS}"/>'
        )
        if opening != "fixed":
            parts.append(_ring(field, sash, fill))
        parts.append(_opening_marks(glass, opening, stroke))

    label = f"<title>{escape(title)}</title>" if title else ""
    role = ' role="img"' if title else ' aria-hidden="true"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w + 2 * pad} {h + 2 * pad}"'
        f'{role} class="window" stroke="{INK}" stroke-width="{stroke}" '
        f'stroke-linejoin="miter">{label}{"".join(parts)}</svg>'
    )
