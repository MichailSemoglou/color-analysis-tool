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
