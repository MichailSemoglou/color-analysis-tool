"""Accessibility contrast metrics: WCAG 2.2 ratios and experimental APCA.

Two metrics are reported side by side:

- WCAG 2.2 contrast ratio, the normative metric for WCAG 2.2 conformance
  (SC 1.4.3/1.4.6): AA requires 4.5:1 for normal text, AAA 7:1.
- APCA (Advanced Perceptual Contrast Algorithm), the candidate contrast
  method under discussion for future WCAG versions. APCA values are
  EXPERIMENTAL: they are not a WCAG conformance criterion, and the
  algorithm itself is not finalized. They are included for research
  comparison only and must not be cited as conformance results.

Both metrics assume sRGB input; wide-gamut or profile-tagged sources
must be converted to sRGB before scoring.
"""

import math
from dataclasses import dataclass
from typing import Optional

from .color_spaces import RGB, relative_luminance

# WCAG 2.2 thresholds for normal text (SC 1.4.3, SC 1.4.6)
WCAG_AA_NORMAL = 4.5
WCAG_AAA_NORMAL = 7.0

# Status label attached to APCA output everywhere it appears
APCA_STATUS = "experimental"

# APCA-W3 0.0.98G-4g constants (sRGB input)
_APCA_BLK_THRS = 0.022
_APCA_BLK_CLMP = 1.414
_APCA_SCALE = 1.14
_APCA_OFFSET = 0.027
_APCA_CLIP = 0.1
_APCA_DELTA_Y_MIN = 0.0005


@dataclass
class ContrastAgainst:
    """Contrast of one color against a single background.

    Attributes:
        background: RGB background color the ratio is computed against
        wcag_ratio: WCAG 2.2 contrast ratio (1.0-21.0)
        wcag_aa: True when the ratio meets WCAG 2.2 AA for normal text
        wcag_aaa: True when the ratio meets WCAG 2.2 AAA for normal text
        apca_lc: APCA Lc value; EXPERIMENTAL, not a WCAG criterion.
            Positive for dark-on-light, negative for light-on-dark
    """

    background: RGB
    wcag_ratio: float
    wcag_aa: bool
    wcag_aaa: bool
    apca_lc: float


@dataclass
class ContrastReport:
    """Contrast of one color against white, black, and the dominant color.

    Attributes:
        on_white: Contrast against white (255, 255, 255)
        on_black: Contrast against black (0, 0, 0)
        vs_dominant: Contrast against the image's dominant color, or None
            when this color is the dominant color
    """

    on_white: ContrastAgainst
    on_black: ContrastAgainst
    vs_dominant: Optional[ContrastAgainst]


def wcag_contrast(rgb1: RGB, rgb2: RGB) -> float:
    """WCAG 2.2 contrast ratio between two sRGB colors.

    Args:
        rgb1: First RGB color (0-255 channels)
        rgb2: Second RGB color (0-255 channels)

    Returns:
        Contrast ratio in 1.0-21.0, symmetric in its arguments
    """
    lum1 = relative_luminance(rgb1)
    lum2 = relative_luminance(rgb2)
    lighter, darker = max(lum1, lum2), min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def _apca_luminance(rgb: RGB) -> float:
    """APCA-W3 estimated luminance: simple 2.4 power, sRGB coefficients."""
    r, g, b = (math.pow(c / 255, 2.4) for c in rgb)
    return 0.2126729 * r + 0.7151522 * g + 0.0721750 * b


def _apca_soft_clamp(y: float) -> float:
    """Soft clamp of near-black luminance per APCA-W3."""
    if y >= _APCA_BLK_THRS:
        return y
    return y + math.pow(_APCA_BLK_THRS - y, _APCA_BLK_CLMP)


def apca_contrast(text_rgb: RGB, background_rgb: RGB) -> float:
    """APCA Lc contrast of text on a background (APCA-W3 0.0.98G-4g).

    EXPERIMENTAL: APCA is a candidate method for future WCAG versions,
    not a WCAG 2.2 conformance criterion. Report for research comparison
    only, always with the APCA_STATUS label.

    Args:
        text_rgb: RGB color of the foreground (text)
        background_rgb: RGB color of the background

    Returns:
        Lc value scaled by 100. Positive for dark text on a light
        background, negative for light text on a dark background; 0.0
        when the pair is below the APCA minimum luminance difference
    """
    text_y = _apca_soft_clamp(_apca_luminance(text_rgb))
    bg_y = _apca_soft_clamp(_apca_luminance(background_rgb))

    if abs(bg_y - text_y) < _APCA_DELTA_Y_MIN:
        return 0.0

    if bg_y > text_y:
        # Dark text on light background, positive polarity
        sapc = (math.pow(bg_y, 0.56) - math.pow(text_y, 0.57)) * _APCA_SCALE
        return 0.0 if sapc < _APCA_CLIP else (sapc - _APCA_OFFSET) * 100.0
    # Light text on dark background, negative polarity
    sapc = (math.pow(bg_y, 0.65) - math.pow(text_y, 0.62)) * _APCA_SCALE
    return 0.0 if sapc > -_APCA_CLIP else (sapc + _APCA_OFFSET) * 100.0


def contrast_against(rgb: RGB, background: RGB) -> ContrastAgainst:
    """WCAG 2.2 and APCA contrast of one color against a background."""
    ratio = wcag_contrast(rgb, background)
    return ContrastAgainst(
        background=background,
        wcag_ratio=round(ratio, 2),
        wcag_aa=ratio >= WCAG_AA_NORMAL,
        wcag_aaa=ratio >= WCAG_AAA_NORMAL,
        apca_lc=round(apca_contrast(rgb, background), 1),
    )


def contrast_report(rgb: RGB, dominant: Optional[RGB] = None) -> ContrastReport:
    """Contrast report against white, black, and the dominant color.

    Args:
        rgb: RGB color to score
        dominant: Dominant color of the image, or None. When equal to
            rgb, vs_dominant is None (a color has no contrast with itself)

    Returns:
        ContrastReport with the three standard comparisons
    """
    white: RGB = (255, 255, 255)
    black: RGB = (0, 0, 0)
    vs_dominant = None
    if dominant is not None and dominant != rgb:
        vs_dominant = contrast_against(rgb, dominant)
    return ContrastReport(
        on_white=contrast_against(rgb, white),
        on_black=contrast_against(rgb, black),
        vs_dominant=vs_dominant,
    )
