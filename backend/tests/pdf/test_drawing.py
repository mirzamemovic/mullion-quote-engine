"""Window drawings for the PDFs: the app's conventions, whole-number coordinates, escaped text."""

import re

from quote_engine.pdf.drawing import window_svg


def _handle_x(svg: str) -> int:
    match = re.search(r'<rect x="(\d+)"[^>]*fill="#23272b"', svg)
    assert match is not None
    return int(match[1])


def test_handle_sits_opposite_the_hinge() -> None:
    hinge_left = window_svg("single_sash_tilt_turn", 1000, 1000, ["tilt_turn_left"], "white")
    hinge_right = window_svg("single_sash_tilt_turn", 1000, 1000, ["tilt_turn_right"], "white")
    centre = 1000 // 2
    assert _handle_x(hinge_left) > centre
    assert _handle_x(hinge_right) < centre


def test_tilt_is_dashed_and_turn_is_not() -> None:
    assert "stroke-dasharray" in window_svg(
        "single_sash_tilt_turn", 900, 1200, ["tilt_turn_right"], "white"
    )
    assert "stroke-dasharray" not in window_svg(
        "single_sash_tilt_turn", 900, 1200, ["turn_right"], "white"
    )


def test_fixed_glass_has_no_sash_and_no_handle() -> None:
    svg = window_svg("fixed", 900, 900, ["fixed"], "white")
    assert 'fill="#23272b"' not in svg
    assert svg.count("<rect") == 1


def test_fixed_mullion_and_two_fields() -> None:
    svg = window_svg("two_field_t_mullion", 1800, 1200, ["fixed", "turn_left"], "white")
    # Mullion, two panes, one handle.
    assert svg.count("<rect") == 4


def test_foil_on_both_sides_is_shaded() -> None:
    assert "#b9c0c4" in window_svg("fixed", 900, 900, ["fixed"], "foil_both_sides")
    assert "#b9c0c4" not in window_svg("fixed", 900, 900, ["fixed"], "foil_one_side")


def test_whole_number_coordinates_and_the_same_markup_every_time() -> None:
    first = window_svg(
        "two_sash_false_mullion", 1437, 1291, ["turn_left", "tilt_turn_right"], "white"
    )
    assert first == window_svg(
        "two_sash_false_mullion", 1437, 1291, ["turn_left", "tilt_turn_right"], "white"
    )
    assert re.search(r"\d\.\d", first) is None


def test_very_narrow_window_still_draws() -> None:
    svg = window_svg("fixed", 300, 3500, ["fixed"], "white")
    width = int(re.search(r'viewBox="0 0 (\d+) ', svg)[1])  # type: ignore[index]
    assert width >= 200


def test_title_is_escaped() -> None:
    svg = window_svg("fixed", 900, 900, ["fixed"], "white", title='<script>"x"&</script>')
    assert "<script>" not in svg
    assert "<title>&lt;script&gt;&quot;x&quot;&amp;&lt;/script&gt;</title>" in svg
    assert 'role="img"' in svg
    assert 'aria-hidden="true"' in window_svg("fixed", 900, 900, ["fixed"], "white")
