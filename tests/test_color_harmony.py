"""Tests for ColorHarmony."""

import pytest

from color_analysis_tool.analyzer import ColorHarmony
from color_analysis_tool.color_spaces import rgb_to_oklch


def _hue_distance(h1, h2):
    """Smallest angular distance between two hues in degrees."""
    return abs((h1 - h2 + 180) % 360 - 180)


class TestOklchEngine:
    """Default engine: OKLCh hue rotation with gamut mapping."""

    def test_find_harmonies_returns_all_types(self):
        result = ColorHarmony.find_harmonies((255, 0, 0))
        assert set(result.keys()) == {"complementary", "analogous", "triadic", "tetradic"}

    def test_complementary_length(self):
        result = ColorHarmony.find_harmonies((255, 0, 0))
        assert len(result["complementary"]) == 1

    def test_analogous_length(self):
        result = ColorHarmony.find_harmonies((255, 0, 0))
        assert len(result["analogous"]) == 3

    def test_triadic_length(self):
        result = ColorHarmony.find_harmonies((255, 0, 0))
        assert len(result["triadic"]) == 3

    def test_tetradic_length(self):
        result = ColorHarmony.find_harmonies((255, 0, 0))
        assert len(result["tetradic"]) == 4

    def test_all_colors_are_rgb_tuples(self):
        result = ColorHarmony.find_harmonies((100, 150, 200))
        for colors in result.values():
            for color in colors:
                assert isinstance(color, tuple)
                assert len(color) == 3
                assert all(0 <= v <= 255 for v in color)

    def test_complementary_is_180_degrees_away_in_oklch(self):
        _, _, base_hue = rgb_to_oklch((255, 0, 0))
        comp = ColorHarmony.find_harmonies((255, 0, 0))["complementary"][0]
        _, _, comp_hue = rgb_to_oklch(comp)
        assert _hue_distance(comp_hue, (base_hue + 180) % 360) < 3

    def test_analogous_steps_are_30_degrees_in_oklch(self):
        _, _, base_hue = rgb_to_oklch((100, 150, 200))
        result = ColorHarmony.find_harmonies((100, 150, 200))["analogous"]
        hues = [rgb_to_oklch(c)[2] for c in result]
        for got, offset in zip(hues, (-30, 0, 30)):
            assert _hue_distance(got, (base_hue + offset) % 360) < 3

    def test_lightness_is_preserved(self):
        base_lightness = rgb_to_oklch((255, 0, 0))[0]
        result = ColorHarmony.find_harmonies((255, 0, 0))
        for colors in result.values():
            for color in colors:
                assert rgb_to_oklch(color)[0] == pytest.approx(base_lightness, abs=0.03)

    def test_chroma_is_reduced_not_clipped(self):
        # A maximally chromatic base color cannot keep its chroma at a
        # rotated hue; the result must sit inside the sRGB gamut with a
        # lower but nonzero chroma
        base_chroma = rgb_to_oklch((255, 0, 0))[1]
        comp = ColorHarmony.find_harmonies((255, 0, 0))["complementary"][0]
        _, new_chroma, _ = rgb_to_oklch(comp)
        assert 0 < new_chroma < base_chroma

    def test_white_harmonies_are_all_white(self):
        result = ColorHarmony.find_harmonies((255, 255, 255))
        for colors in result.values():
            for color in colors:
                assert color == (255, 255, 255)

    def test_black_harmonies_are_all_black(self):
        result = ColorHarmony.find_harmonies((0, 0, 0))
        for colors in result.values():
            for color in colors:
                assert color == (0, 0, 0)

    def test_gray_harmonies_stay_gray(self):
        result = ColorHarmony.find_harmonies((128, 128, 128))
        for colors in result.values():
            for color in colors:
                assert rgb_to_oklch(color)[1] == pytest.approx(0.0, abs=1e-3)

    def test_deterministic(self):
        assert ColorHarmony.find_harmonies((18, 52, 86)) == ColorHarmony.find_harmonies(
            (18, 52, 86)
        )

    def test_invalid_engine_raises(self):
        with pytest.raises(ValueError, match="engine"):
            ColorHarmony.find_harmonies((255, 0, 0), engine="magic")

    def test_find_harmonies_rejects_out_of_range(self):
        with pytest.raises(ValueError, match="0-255"):
            ColorHarmony.find_harmonies((0, 0, 300))


class TestHsvLegacyEngine:
    """v1 HSV hue rotation, retained for reproducibility."""

    def test_complementary_of_red_is_cyan(self):
        # Red (0 degrees) maps to cyan (180 degrees) on the HSV wheel
        result = ColorHarmony.find_harmonies((255, 0, 0), engine="hsv_legacy")
        comp = result["complementary"][0]
        assert comp[1] > 200
        assert comp[2] > 200
        assert comp[0] < 10

    def test_harmony_channels_are_rounded_not_truncated(self):
        # (0, 0, 15) has hue 240 degrees; its -30 degree analogous color
        # computes to exactly 7.5 on the 0-255 scale, where int() gives 7
        # and round() gives 8
        result = ColorHarmony.find_harmonies((0, 0, 15), engine="hsv_legacy")
        assert result["analogous"][0] == (0, 8, 15)

    def test_matches_v1_values(self):
        result = ColorHarmony.find_harmonies((255, 0, 0), engine="hsv_legacy")
        assert result["complementary"] == [(0, 255, 255)]
        assert result["analogous"] == [(255, 0, 128), (255, 0, 0), (255, 128, 0)]
        assert result["triadic"] == [(0, 255, 0), (255, 0, 0), (0, 0, 255)]

    def test_white_harmonies_are_all_white(self):
        result = ColorHarmony.find_harmonies((255, 255, 255), engine="hsv_legacy")
        for colors in result.values():
            for color in colors:
                assert color == (255, 255, 255)
