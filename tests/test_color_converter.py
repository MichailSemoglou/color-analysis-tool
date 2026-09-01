"""Tests for ColorConverter."""

import pytest

from color_analysis_tool.analyzer import ColorConverter


class TestRgbToHex:
    def test_white(self):
        assert ColorConverter.rgb_to_hex((255, 255, 255)) == "#ffffff"

    def test_black(self):
        assert ColorConverter.rgb_to_hex((0, 0, 0)) == "#000000"

    def test_red(self):
        assert ColorConverter.rgb_to_hex((255, 0, 0)) == "#ff0000"

    def test_arbitrary(self):
        assert ColorConverter.rgb_to_hex((18, 52, 86)) == "#123456"


class TestHexToRgb:
    def test_with_hash(self):
        assert ColorConverter.hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_without_hash(self):
        assert ColorConverter.hex_to_rgb("000000") == (0, 0, 0)

    def test_red(self):
        assert ColorConverter.hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_arbitrary(self):
        assert ColorConverter.hex_to_rgb("#123456") == (18, 52, 86)

    def test_returns_three_tuple(self):
        result = ColorConverter.hex_to_rgb("#aabbcc")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_roundtrip(self):
        original = (100, 150, 200)
        assert ColorConverter.hex_to_rgb(ColorConverter.rgb_to_hex(original)) == original

    def test_shorthand_with_hash(self):
        assert ColorConverter.hex_to_rgb("#fff") == (255, 255, 255)

    def test_shorthand_without_hash(self):
        assert ColorConverter.hex_to_rgb("f53") == (255, 85, 51)

    def test_shorthand_mixed_case(self):
        assert ColorConverter.hex_to_rgb("#Ff5") == (255, 255, 85)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid hex color"):
            ColorConverter.hex_to_rgb("")

    def test_invalid_length_raises(self):
        with pytest.raises(ValueError, match="Invalid hex color"):
            ColorConverter.hex_to_rgb("#ff")

    def test_five_digits_raise(self):
        with pytest.raises(ValueError, match="Invalid hex color"):
            ColorConverter.hex_to_rgb("12345")

    def test_invalid_characters_raise(self):
        with pytest.raises(ValueError, match="Invalid hex color"):
            ColorConverter.hex_to_rgb("#gggggg")


class TestRgbToCmykDeviceNaive:
    """The pre-v2 formula, retained explicitly as method='device_naive'."""

    def test_black(self):
        assert ColorConverter.rgb_to_cmyk(0, 0, 0, method="device_naive") == (0, 0, 0, 100)

    def test_white(self):
        assert ColorConverter.rgb_to_cmyk(255, 255, 255, method="device_naive") == (0, 0, 0, 0)

    def test_pure_red(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(255, 0, 0, method="device_naive")
        assert k == 0
        assert c == 0
        assert m == 100
        assert y == 100

    def test_pure_green(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(0, 255, 0, method="device_naive")
        assert k == 0
        assert c == 100
        assert m == 0
        assert y == 100

    def test_pure_blue(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(0, 0, 255, method="device_naive")
        assert k == 0
        assert c == 100
        assert m == 100
        assert y == 0

    def test_values_in_range(self):
        for r, g, b in [(128, 64, 32), (10, 200, 100), (255, 128, 0)]:
            result = ColorConverter.rgb_to_cmyk(r, g, b, method="device_naive")
            assert all(0 <= v <= 100 for v in result)


class TestRgbToCmykIcc:
    """ICC conversion through the bundled FOGRA39 profile (default method)."""

    def test_white_has_no_ink(self):
        assert ColorConverter.rgb_to_cmyk(255, 255, 255) == (0, 0, 0, 0)

    def test_black_is_rich_black(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(0, 0, 0)
        assert k >= 80

    def test_pure_red(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(255, 0, 0)
        assert c == 0
        assert m >= 80
        assert y >= 80

    def test_deterministic(self):
        first = ColorConverter.rgb_to_cmyk(18, 52, 86)
        second = ColorConverter.rgb_to_cmyk(18, 52, 86)
        assert first == second

    def test_values_in_range(self):
        for r, g, b in [(128, 64, 32), (10, 200, 100), (255, 128, 0), (0, 0, 0)]:
            result = ColorConverter.rgb_to_cmyk(r, g, b)
            assert all(0 <= v <= 100 for v in result)

    def test_custom_profile_path_matches_default(self):
        default = ColorConverter.rgb_to_cmyk(18, 52, 86)
        explicit = ColorConverter.rgb_to_cmyk(
            18, 52, 86, profile="color_analysis_tool/profiles/ISOcoated_v2_eci.icc"
        )
        assert default == explicit

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="method"):
            ColorConverter.rgb_to_cmyk(0, 0, 0, method="magic")

    def test_bundled_profile_is_shipped(self):
        from importlib import resources

        profile = (
            resources.files("color_analysis_tool")
            .joinpath("profiles")
            .joinpath("ISOcoated_v2_eci.icc")
        )
        assert profile.is_file()


class TestRgbToCmykBatch:
    """One-pass palette conversion must match per-color conversion exactly."""

    SAMPLE = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (0, 0, 0),
        (255, 255, 255),
        (128, 128, 128),
        (18, 52, 86),
    ]

    def test_matches_single_conversion(self):
        batch = ColorConverter.rgb_to_cmyk_batch(self.SAMPLE)
        singles = [ColorConverter.rgb_to_cmyk(*c) for c in self.SAMPLE]
        assert batch == singles

    def test_order_preserved(self):
        batch = ColorConverter.rgb_to_cmyk_batch(self.SAMPLE)
        assert batch[0] == ColorConverter.rgb_to_cmyk(255, 0, 0)
        assert batch[-1] == ColorConverter.rgb_to_cmyk(18, 52, 86)

    def test_device_naive_matches_single(self):
        batch = ColorConverter.rgb_to_cmyk_batch(self.SAMPLE, method="device_naive")
        singles = [
            ColorConverter.rgb_to_cmyk(*c, method="device_naive") for c in self.SAMPLE
        ]
        assert batch == singles

    def test_empty_list(self):
        assert ColorConverter.rgb_to_cmyk_batch([]) == []

    def test_validation(self):
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_cmyk_batch([(255, 0, 0), (300, 0, 0)])

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="method"):
            ColorConverter.rgb_to_cmyk_batch(self.SAMPLE, method="magic")

    def test_bad_profile_path_raises(self):
        with pytest.raises(OSError, match="cannot open profile"):
            ColorConverter.rgb_to_cmyk_batch(self.SAMPLE, profile="/nonexistent/profile.icc")

    def test_custom_profile_path_matches_default(self):
        batch = ColorConverter.rgb_to_cmyk_batch(
            self.SAMPLE, profile="color_analysis_tool/profiles/ISOcoated_v2_eci.icc"
        )
        assert batch == ColorConverter.rgb_to_cmyk_batch(self.SAMPLE)


class TestPerceptualConverters:
    def test_rgb_to_oklab(self):
        lightness, a, b = ColorConverter.rgb_to_oklab((255, 0, 0))
        assert lightness == pytest.approx(0.628, abs=1e-3)
        assert a == pytest.approx(0.225, abs=1e-3)
        assert b == pytest.approx(0.126, abs=1e-3)

    def test_rgb_to_oklch(self):
        lightness, chroma, hue = ColorConverter.rgb_to_oklch((255, 0, 0))
        assert lightness == pytest.approx(0.628, abs=1e-3)
        assert chroma == pytest.approx(0.258, abs=1e-3)
        assert hue == pytest.approx(29.23, abs=0.01)

    def test_rgb_to_xyz(self):
        _, y, _ = ColorConverter.rgb_to_xyz((255, 255, 255))
        assert y == pytest.approx(1.0, abs=1e-6)

    def test_rgb_to_lab(self):
        lightness, _, _ = ColorConverter.rgb_to_lab((255, 255, 255))
        assert lightness == pytest.approx(100.0, abs=1e-4)

    def test_validation(self):
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_oklab((256, 0, 0))
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_oklch((0, 0, 256))
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_xyz((0, 256, 0))
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_lab((0, 0, -1))


class TestChannelValidation:
    def test_rgb_to_hex_rejects_out_of_range(self):
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_hex((256, 0, 0))

    def test_rgb_to_hex_rejects_negative(self):
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_hex((-1, 0, 0))

    def test_rgb_to_hex_rejects_wrong_length(self):
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_hex((18, 52))

    def test_rgb_to_cmyk_rejects_out_of_range(self):
        with pytest.raises(ValueError, match="0-255"):
            ColorConverter.rgb_to_cmyk(300, 0, 0)

    def test_valid_input_still_accepted(self):
        assert ColorConverter.rgb_to_hex((0, 128, 255)) == "#0080ff"
        assert ColorConverter.rgb_to_cmyk(0, 128, 255, method="device_naive") == (100, 50, 0, 0)
