"""Tests for the perceptual color space mathematics."""

import math

import pytest

from color_analysis_tool import color_spaces as cs


class TestRgbToOklab:
    """Reference values from Ottosson (2020), https://bottosson.github.io/posts/oklab/"""

    def test_red(self):
        lightness, a, b = cs.rgb_to_oklab((255, 0, 0))
        assert lightness == pytest.approx(0.6279553606, abs=1e-6)
        assert a == pytest.approx(0.2248630611, abs=1e-6)
        assert b == pytest.approx(0.1258462985, abs=1e-6)

    def test_green(self):
        lightness, a, b = cs.rgb_to_oklab((0, 255, 0))
        assert lightness == pytest.approx(0.8664396116, abs=1e-6)
        assert a == pytest.approx(-0.2338875742, abs=1e-6)
        assert b == pytest.approx(0.1794984799, abs=1e-6)

    def test_blue(self):
        lightness, a, b = cs.rgb_to_oklab((0, 0, 255))
        assert lightness == pytest.approx(0.4520137184, abs=1e-6)
        assert a == pytest.approx(-0.0324487948, abs=1e-3)
        assert b == pytest.approx(-0.3115281477, abs=1e-6)

    def test_white(self):
        lightness, a, b = cs.rgb_to_oklab((255, 255, 255))
        assert lightness == pytest.approx(1.0, abs=1e-6)
        assert a == pytest.approx(0.0, abs=1e-6)
        assert b == pytest.approx(0.0, abs=1e-6)

    def test_black(self):
        assert cs.rgb_to_oklab((0, 0, 0)) == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)

    def test_gray_is_achromatic(self):
        _, a, b = cs.rgb_to_oklab((128, 128, 128))
        assert a == pytest.approx(0.0, abs=1e-6)
        assert b == pytest.approx(0.0, abs=1e-6)


class TestOklabRoundtrip:
    @pytest.mark.parametrize(
        "rgb",
        [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 255),
            (0, 0, 0),
            (128, 128, 128),
            (18, 52, 86),
            (250, 128, 7),
            (1, 2, 3),
        ],
    )
    def test_roundtrip_within_one_channel_step(self, rgb):
        result = cs.oklab_to_rgb(cs.rgb_to_oklab(rgb))
        for got, want in zip(result, rgb):
            assert abs(got - want) <= 1


class TestRgbToOklch:
    def test_red(self):
        lightness, chroma, hue = cs.rgb_to_oklch((255, 0, 0))
        assert lightness == pytest.approx(0.6279553606, abs=1e-6)
        assert chroma == pytest.approx(0.2576833077, abs=1e-6)
        assert hue == pytest.approx(29.2338858, abs=1e-4)

    def test_achromatic_has_zero_chroma(self):
        _, chroma, _ = cs.rgb_to_oklch((200, 200, 200))
        assert chroma == pytest.approx(0.0, abs=1e-6)

    def test_hue_wraps_into_0_360(self):
        for rgb in [(255, 0, 255), (0, 255, 255), (255, 255, 0), (10, 200, 100)]:
            _, _, hue = cs.rgb_to_oklch(rgb)
            assert 0.0 <= hue < 360.0

    def test_oklch_to_oklab_roundtrip(self):
        lch = cs.rgb_to_oklch((18, 52, 86))
        lab = cs.oklch_to_oklab(lch)
        assert lab == pytest.approx(cs.rgb_to_oklab((18, 52, 86)), abs=1e-12)


class TestOklabToOklch:
    def test_matches_rgb_to_oklch(self):
        rgb = (18, 52, 86)
        via_oklab = cs.oklab_to_oklch(cs.rgb_to_oklab(rgb))
        assert via_oklab == pytest.approx(cs.rgb_to_oklch(rgb), abs=1e-12)

    def test_out_of_gamut_input_not_clamped(self):
        # oklch(0.65, 0.5, 140) is far outside sRGB; the conversion must
        # stay exact instead of clipping into the gamut
        lab = cs.oklch_to_oklab((0.65, 0.5, 140.0))
        assert cs.oklab_to_oklch(lab) == pytest.approx((0.65, 0.5, 140.0), abs=1e-9)

    def test_achromatic_reports_zero_hue(self):
        _, chroma, hue = cs.oklab_to_oklch((0.5, 0.0, 0.0))
        assert chroma == 0.0
        assert hue == 0.0


class TestNormalizeOklch:
    def test_rounds_to_four_decimals(self):
        assert cs.normalize_oklch((0.123456789, 0.234567891, 123.4567891)) == (
            0.1235,
            0.2346,
            123.4568,
        )

    def test_achromatic_hue_becomes_zero(self):
        lch = cs.rgb_to_oklch((255, 255, 255))
        assert cs.normalize_oklch(lch) == (1.0, 0.0, 0.0)

    def test_chromatic_hue_kept(self):
        lch = cs.rgb_to_oklch((255, 0, 0))
        assert cs.normalize_oklch(lch)[2] == pytest.approx(29.2339, abs=1e-4)


class TestRgbToXyz:
    def test_white_is_d65_white(self):
        x, y, z = cs.rgb_to_xyz((255, 255, 255))
        assert x == pytest.approx(0.9505, abs=1e-3)
        assert y == pytest.approx(1.0, abs=1e-6)
        assert z == pytest.approx(1.0888, abs=1e-3)

    def test_red(self):
        x, y, z = cs.rgb_to_xyz((255, 0, 0))
        assert x == pytest.approx(0.4124564, abs=1e-6)
        assert y == pytest.approx(0.2126729, abs=1e-6)
        assert z == pytest.approx(0.0193339, abs=1e-6)

    def test_black(self):
        assert cs.rgb_to_xyz((0, 0, 0)) == (0.0, 0.0, 0.0)


class TestRgbToLab:
    def test_white(self):
        lightness, a, b = cs.rgb_to_lab((255, 255, 255))
        assert lightness == pytest.approx(100.0, abs=1e-4)
        assert a == pytest.approx(0.0, abs=1e-4)
        assert b == pytest.approx(0.0, abs=1e-4)

    def test_black(self):
        assert cs.rgb_to_lab((0, 0, 0)) == pytest.approx((0.0, 0.0, 0.0), abs=1e-9)

    def test_red(self):
        # CIELAB of sRGB red, standard reference values
        lightness, a, b = cs.rgb_to_lab((255, 0, 0))
        assert lightness == pytest.approx(53.2408, abs=1e-3)
        assert a == pytest.approx(80.0925, abs=1e-3)
        assert b == pytest.approx(67.2032, abs=1e-3)


class TestOklabToLab:
    @pytest.mark.parametrize(
        "rgb",
        [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 255),
            (0, 0, 0),
            (128, 128, 128),
            (18, 52, 86),
        ],
    )
    def test_matches_rgb_to_lab_for_in_gamut_colors(self, rgb):
        via_oklab = cs.oklab_to_lab(cs.rgb_to_oklab(rgb))
        assert via_oklab == pytest.approx(cs.rgb_to_lab(rgb), abs=1e-3)


class TestDeltaECiede2000:
    """Reference pairs from Sharma, Wu, and Dalal (2005), Table 1."""

    @pytest.mark.parametrize(
        "lab1,lab2,expected",
        [
            ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
            ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
            ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
            ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
            ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
            ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
            ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
        ],
    )
    def test_sharma_pairs(self, lab1, lab2, expected):
        assert cs.delta_e_ciede2000(lab1, lab2) == pytest.approx(expected, abs=1e-4)

    def test_identical_colors_have_zero_distance(self):
        assert cs.delta_e_ciede2000((50.0, 20.0, -30.0), (50.0, 20.0, -30.0)) == 0.0

    def test_symmetry(self):
        lab1, lab2 = (60.0, 10.0, 5.0), (40.0, -20.0, 30.0)
        assert cs.delta_e_ciede2000(lab1, lab2) == pytest.approx(
            cs.delta_e_ciede2000(lab2, lab1), abs=1e-9
        )


class TestRelativeLuminance:
    def test_white(self):
        assert cs.relative_luminance((255, 255, 255)) == pytest.approx(1.0, abs=1e-12)

    def test_black(self):
        assert cs.relative_luminance((0, 0, 0)) == 0.0

    def test_mid_gray(self):
        # WCAG linearization of 128/255
        expected = ((128 / 255 + 0.055) / 1.055) ** 2.4
        assert cs.relative_luminance((128, 128, 128)) == pytest.approx(expected, abs=1e-12)


class TestGamutMapOklch:
    def test_in_gamut_color_unchanged(self):
        lch = cs.rgb_to_oklch((18, 52, 86))
        assert cs.gamut_map_oklch(lch) == (18, 52, 86)

    def test_out_of_gamut_color_lands_in_gamut(self):
        # Chroma far beyond anything sRGB can display
        result = cs.gamut_map_oklch((0.6, 0.5, 29.0))
        assert all(0 <= c <= 255 for c in result)

    def test_hue_and_lightness_preserved(self):
        lightness, _, hue = (0.65, 0.5, 140.0)
        result = cs.gamut_map_oklch((lightness, 0.5, hue))
        new_lightness, new_chroma, new_hue = cs.rgb_to_oklch(result)
        assert new_lightness == pytest.approx(lightness, abs=0.02)
        assert math.isclose(new_hue, hue, abs_tol=2.0)
        assert new_chroma < 0.5  # chroma was reduced to fit

    def test_chroma_reduction_is_minimal(self):
        # The mapped chroma should be close to the maximum displayable
        result = cs.gamut_map_oklch((0.65, 0.5, 140.0))
        _, new_chroma, _ = cs.rgb_to_oklch(result)
        assert new_chroma > 0.05

    def test_achromatic_color_unchanged(self):
        assert cs.gamut_map_oklch(cs.rgb_to_oklch((128, 128, 128))) == (128, 128, 128)

    def test_lightness_clamped(self):
        assert cs.gamut_map_oklch((1.5, 0.0, 0.0)) == (255, 255, 255)
        assert cs.gamut_map_oklch((-0.5, 0.0, 0.0)) == (0, 0, 0)


class TestNumericalEdges:
    def test_cbrt_negative_input(self):
        # Matrix float noise can hand _cbrt a small negative; the sign-
        # preserving branch must handle it
        assert cs._cbrt(-8.0) == pytest.approx(-2.0)
        assert cs._cbrt(8.0) == pytest.approx(2.0)

    def test_ciede2000_achromatic_pair(self):
        # Both colors achromatic: exercises the zero-chroma branches
        assert cs.delta_e_ciede2000((50.0, 0.0, 0.0), (60.0, 0.0, 0.0)) == pytest.approx(
            9.4706, abs=1e-3
        )

    def test_ciede2000_hue_wraparound(self):
        # Hues straddling 0/360 degrees exercise the wrap branches; the
        # mean hue must resolve near 0, not near 180, which a wrap bug
        # would produce
        lab1 = (50.0, 39.39, -6.95)  # hue ~350 degrees
        lab2 = (50.0, 39.39, 6.95)  # hue ~10 degrees
        forward = cs.delta_e_ciede2000(lab1, lab2)
        assert forward == pytest.approx(7.7262, abs=1e-3)
        assert math.isfinite(forward)
        assert cs.delta_e_ciede2000(lab2, lab1) == pytest.approx(forward, abs=1e-9)
