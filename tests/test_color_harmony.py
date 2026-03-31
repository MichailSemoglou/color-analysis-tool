"""Tests for ColorHarmony."""

from color_analysis_tool.analyzer import ColorHarmony


def test_find_harmonies_returns_all_types():
    result = ColorHarmony.find_harmonies((255, 0, 0))
    assert set(result.keys()) == {"complementary", "analogous", "triadic", "tetradic"}


def test_complementary_length():
    result = ColorHarmony.find_harmonies((255, 0, 0))
    assert len(result["complementary"]) == 1


def test_analogous_length():
    result = ColorHarmony.find_harmonies((255, 0, 0))
    assert len(result["analogous"]) == 3


def test_triadic_length():
    result = ColorHarmony.find_harmonies((255, 0, 0))
    assert len(result["triadic"]) == 3


def test_tetradic_length():
    result = ColorHarmony.find_harmonies((255, 0, 0))
    assert len(result["tetradic"]) == 4


def test_all_colors_are_rgb_tuples():
    result = ColorHarmony.find_harmonies((100, 150, 200))
    for colors in result.values():
        for color in colors:
            assert isinstance(color, tuple)
            assert len(color) == 3
            assert all(0 <= v <= 255 for v in color)


def test_complementary_of_red_is_cyan():
    # Red (0°) → complementary is cyan (180°)
    result = ColorHarmony.find_harmonies((255, 0, 0))
    comp = result["complementary"][0]
    # Cyan: R~0, G~255, B~255
    assert comp[1] > 200
    assert comp[2] > 200
    assert comp[0] < 10


def test_white_harmonies_are_all_white():
    # White has 0 saturation; all harmony colours should also be white
    result = ColorHarmony.find_harmonies((255, 255, 255))
    for colors in result.values():
        for color in colors:
            assert color == (255, 255, 255)


def test_black_harmonies_are_all_black():
    result = ColorHarmony.find_harmonies((0, 0, 0))
    for colors in result.values():
        for color in colors:
            assert color == (0, 0, 0)
