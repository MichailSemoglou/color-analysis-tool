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


class TestRgbToCmyk:
    def test_black(self):
        assert ColorConverter.rgb_to_cmyk(0, 0, 0) == (0, 0, 0, 100)

    def test_white(self):
        assert ColorConverter.rgb_to_cmyk(255, 255, 255) == (0, 0, 0, 0)

    def test_pure_red(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(255, 0, 0)
        assert k == 0
        assert c == 0
        assert m == 100
        assert y == 100

    def test_pure_green(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(0, 255, 0)
        assert k == 0
        assert c == 100
        assert m == 0
        assert y == 100

    def test_pure_blue(self):
        c, m, y, k = ColorConverter.rgb_to_cmyk(0, 0, 255)
        assert k == 0
        assert c == 100
        assert m == 100
        assert y == 0

    def test_values_in_range(self):
        for r, g, b in [(128, 64, 32), (10, 200, 100), (255, 128, 0)]:
            result = ColorConverter.rgb_to_cmyk(r, g, b)
            assert all(0 <= v <= 100 for v in result)


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
        assert ColorConverter.rgb_to_cmyk(0, 128, 255) == (100, 50, 0, 0)
