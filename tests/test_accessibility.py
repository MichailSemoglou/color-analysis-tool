"""Tests for WCAG 2.2 and APCA contrast metrics."""

import pytest

from color_analysis_tool.accessibility import (
    APCA_STATUS,
    ContrastReport,
    apca_contrast,
    contrast_against,
    contrast_report,
    wcag_contrast,
)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


class TestWcagContrast:
    def test_black_on_white_is_21(self):
        assert wcag_contrast(BLACK, WHITE) == pytest.approx(21.0, abs=1e-9)

    def test_identical_colors_is_1(self):
        assert wcag_contrast((128, 128, 128), (128, 128, 128)) == pytest.approx(1.0)

    def test_symmetry(self):
        assert wcag_contrast((18, 52, 86), WHITE) == pytest.approx(
            wcag_contrast(WHITE, (18, 52, 86)), abs=1e-12
        )

    def test_known_pair(self):
        # #777777 on white is the classic 4.48:1 boundary case
        assert wcag_contrast((119, 119, 119), WHITE) == pytest.approx(4.48, abs=0.01)

    def test_ratio_bounded(self):
        for rgb in [(255, 0, 0), (0, 255, 0), (18, 52, 86)]:
            ratio = wcag_contrast(rgb, WHITE)
            assert 1.0 <= ratio <= 21.0


class TestApcaContrast:
    def test_black_text_on_white(self):
        # APCA-W3 reference polarity: dark on light is positive, ~106
        lc = apca_contrast(BLACK, WHITE)
        assert lc == pytest.approx(106.0, abs=1.0)

    def test_white_text_on_black(self):
        # Light on dark is negative, ~-108
        lc = apca_contrast(WHITE, BLACK)
        assert lc == pytest.approx(-107.9, abs=1.0)

    def test_identical_colors_is_zero(self):
        assert apca_contrast((128, 128, 128), (128, 128, 128)) == 0.0

    def test_near_identical_colors_is_zero(self):
        assert apca_contrast((200, 200, 200), (201, 200, 200)) == 0.0

    def test_polarity_flips_with_swap(self):
        dark_on_light = apca_contrast(BLACK, WHITE)
        light_on_dark = apca_contrast(WHITE, BLACK)
        assert dark_on_light > 0
        assert light_on_dark < 0

    def test_status_label_is_experimental(self):
        assert APCA_STATUS == "experimental"


class TestContrastAgainst:
    def test_fields(self):
        result = contrast_against(BLACK, WHITE)
        assert result.background == WHITE
        assert result.wcag_ratio == pytest.approx(21.0, abs=0.01)
        assert result.wcag_aa is True
        assert result.wcag_aaa is True

    def test_aa_boundary(self):
        # #767676 on white: just above 4.5
        assert contrast_against((118, 118, 118), WHITE).wcag_aa is True
        # #787878 on white: just below 4.5
        assert contrast_against((120, 120, 120), WHITE).wcag_aa is False

    def test_aaa_boundary(self):
        # White on black passes AAA; mid gray does not
        assert contrast_against(WHITE, BLACK).wcag_aaa is True
        assert contrast_against((128, 128, 128), WHITE).wcag_aaa is False


class TestContrastReport:
    def test_structure(self):
        report = contrast_report((18, 52, 86), dominant=(255, 0, 0))
        assert isinstance(report, ContrastReport)
        assert report.on_white.background == WHITE
        assert report.on_black.background == BLACK
        assert report.vs_dominant is not None
        assert report.vs_dominant.background == (255, 0, 0)

    def test_dominant_color_has_no_vs_dominant(self):
        report = contrast_report((255, 0, 0), dominant=(255, 0, 0))
        assert report.vs_dominant is None

    def test_no_dominant(self):
        report = contrast_report((18, 52, 86))
        assert report.vs_dominant is None
