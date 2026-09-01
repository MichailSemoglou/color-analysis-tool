"""Perceptual color space mathematics.

Closed-form conversions between sRGB, CIE XYZ, CIELAB, OKLab, and OKLCh,
plus CIEDE2000 color difference and WCAG relative luminance. Everything
here is a pure function with no Pillow dependency, so the module can be
reused by the clustering engine, the harmony engine, and the accessibility
report alike.

References:
    OKLab and OKLCh: Ottosson (2020, December 23), "A perceptual color
        space for image processing" (matrices revised 2021-01-25),
        https://bottosson.github.io/posts/oklab/
    CIELAB: CIE 1976 L*a*b* colour space, D65 illuminant, ISO/CIE
        11664-4:2019, https://www.iso.org/standard/74166.html
    CIEDE2000: Sharma, Wu, and Dalal (2005), "The CIEDE2000
        color-difference formula", Color Research & Application 30(1),
        21-30, https://doi.org/10.1002/col.20070
    Relative luminance: WCAG 2.2 (W3C Recommendation), "relative
        luminance" definition, https://www.w3.org/TR/WCAG22/
"""

import math
from typing import Tuple

RGB = Tuple[int, int, int]
OKLab = Tuple[float, float, float]
OKLCh = Tuple[float, float, float]
LAB = Tuple[float, float, float]
XYZ = Tuple[float, float, float]

# D65 reference white in XYZ (Y normalized to 1)
_D65_XN = 0.95047
_D65_YN = 1.0
_D65_ZN = 1.08883

# Gamut membership tolerance for linear sRGB channels
_GAMUT_TOLERANCE = 1e-4


def _cbrt(x: float) -> float:
    """Cube root that tolerates small negative float artifacts."""
    if x >= 0:
        return math.pow(x, 1.0 / 3.0)
    return -math.pow(-x, 1.0 / 3.0)


def _srgb_channel_to_linear(c: float) -> float:
    """Linearize one sRGB channel in 0-1 (IEC 61966-2-1)."""
    if c <= 0.04045:
        return c / 12.92
    return math.pow((c + 0.055) / 1.055, 2.4)


def _linear_channel_to_srgb(c: float) -> float:
    """Companding inverse of _srgb_channel_to_linear."""
    if c <= 0.0031308:
        return 12.92 * c
    return 1.055 * math.pow(c, 1.0 / 2.4) - 0.055


def _linear_srgb_to_oklab(r: float, g: float, b: float) -> OKLab:
    """OKLab from linear sRGB channels in 0-1 (Ottosson 2020)."""
    l_c = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_c = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_c = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b

    l_ = _cbrt(l_c)
    m_ = _cbrt(m_c)
    s_ = _cbrt(s_c)

    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _oklab_to_linear_srgb(lab: OKLab) -> Tuple[float, float, float]:
    """Linear sRGB channels in 0-1 from OKLab; may fall outside 0-1."""
    lightness, a, b = lab
    l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
    m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
    s_ = lightness - 0.0894841775 * a - 1.2914855480 * b

    l_v = l_**3
    m_v = m_**3
    s_v = s_**3

    return (
        +4.0767416621 * l_v - 3.3077115913 * m_v + 0.2309699292 * s_v,
        -1.2684380046 * l_v + 2.6097574011 * m_v - 0.3413193965 * s_v,
        -0.0041960863 * l_v - 0.7034186147 * m_v + 1.7076147010 * s_v,
    )


def rgb_to_oklab(rgb: RGB) -> OKLab:
    """Convert an sRGB color to OKLab.

    Args:
        rgb: RGB tuple of (red, green, blue) values (0-255)

    Returns:
        OKLab tuple (L in 0-1, a and b unbounded, typically within 0.5)
    """
    r, g, b = (_srgb_channel_to_linear(c / 255) for c in rgb)
    return _linear_srgb_to_oklab(r, g, b)


def oklab_to_rgb(lab: OKLab) -> RGB:
    """Convert OKLab to the nearest in-gamut sRGB color.

    Channels that land outside 0-1 are clamped; use gamut_map_oklch for
    hue-preserving gamut mapping instead of clipping.

    Args:
        lab: OKLab tuple (L in 0-1)

    Returns:
        RGB tuple of (red, green, blue) values (0-255)
    """
    linear = _oklab_to_linear_srgb(lab)
    channels = [round(_linear_channel_to_srgb(min(1.0, max(0.0, c))) * 255) for c in linear]
    return (channels[0], channels[1], channels[2])


def rgb_to_oklch(rgb: RGB) -> OKLCh:
    """Convert an sRGB color to OKLCh (cylindrical OKLab).

    Args:
        rgb: RGB tuple of (red, green, blue) values (0-255)

    Returns:
        OKLCh tuple (L in 0-1, C >= 0, H in degrees 0-360)
    """
    lightness, a, b = rgb_to_oklab(rgb)
    chroma = math.hypot(a, b)
    hue = math.degrees(math.atan2(b, a)) % 360
    return (lightness, chroma, hue)


def oklch_to_oklab(lch: OKLCh) -> OKLab:
    """Convert OKLCh to OKLab.

    Args:
        lch: OKLCh tuple (L, C, H in degrees)

    Returns:
        OKLab tuple
    """
    lightness, chroma, hue = lch
    a = chroma * math.cos(math.radians(hue))
    b = chroma * math.sin(math.radians(hue))
    return (lightness, a, b)


def normalize_oklch(lch: OKLCh) -> OKLCh:
    """Round OKLCh coordinates for display (4 decimal places).

    Hue is meaningless when chroma is zero (it is the atan2 of rounding
    noise), so achromatic colors report hue 0.

    Args:
        lch: OKLCh tuple (L, C, H in degrees)

    Returns:
        Rounded OKLCh tuple
    """
    lightness, chroma, hue = lch
    chroma = round(chroma, 4)
    if chroma == 0.0:
        hue = 0.0
    return (round(lightness, 4), chroma, round(hue, 4))


def _linear_srgb_to_xyz(r: float, g: float, b: float) -> XYZ:
    """CIE XYZ (D65, Y in 0-1) from linear sRGB channels in 0-1."""
    return (
        0.4124564 * r + 0.3575761 * g + 0.1804375 * b,
        0.2126729 * r + 0.7151522 * g + 0.0721750 * b,
        0.0193339 * r + 0.1191920 * g + 0.9503041 * b,
    )


def _xyz_to_lab(x: float, y: float, z: float) -> LAB:
    """CIELAB (D65, CIE 1976) from XYZ with Y normalized to 1."""

    def f(t: float) -> float:
        delta = 6.0 / 29.0
        if t > delta**3:
            return _cbrt(t)
        return t / (3 * delta**2) + 4.0 / 29.0

    fx, fy, fz = f(x / _D65_XN), f(y / _D65_YN), f(z / _D65_ZN)
    return (
        116 * fy - 16,
        500 * (fx - fy),
        200 * (fy - fz),
    )


def rgb_to_xyz(rgb: RGB) -> XYZ:
    """Convert an sRGB color to CIE XYZ (D65, Y normalized to 1).

    Args:
        rgb: RGB tuple of (red, green, blue) values (0-255)

    Returns:
        XYZ tuple with Y in 0-1
    """
    r, g, b = (_srgb_channel_to_linear(c / 255) for c in rgb)
    return _linear_srgb_to_xyz(r, g, b)


def rgb_to_lab(rgb: RGB) -> LAB:
    """Convert an sRGB color to CIELAB (D65, CIE 1976).

    Args:
        rgb: RGB tuple of (red, green, blue) values (0-255)

    Returns:
        LAB tuple (L in 0-100)
    """
    x, y, z = rgb_to_xyz(rgb)
    return _xyz_to_lab(x, y, z)


def oklab_to_lab(lab: OKLab) -> LAB:
    """Convert OKLab to CIELAB through linear sRGB and XYZ.

    Unlike oklab_to_rgb followed by rgb_to_lab, this path neither clamps
    nor rounds, so it is suitable for comparing cluster centroids that
    may sit outside the sRGB gamut.

    Args:
        lab: OKLab tuple (L in 0-1)

    Returns:
        LAB tuple (L in 0-100)
    """
    r, g, b = _oklab_to_linear_srgb(lab)
    x, y, z = _linear_srgb_to_xyz(r, g, b)
    return _xyz_to_lab(x, y, z)


def delta_e_ciede2000(lab1: LAB, lab2: LAB) -> float:
    """CIEDE2000 color difference between two CIELAB colors.

    Implementation of Sharma, Wu, and Dalal (2005) with the standard
    parametric factors kL = kC = kH = 1.

    Args:
        lab1: First LAB color (L in 0-100)
        lab2: Second LAB color (L in 0-100)

    Returns:
        CIEDE2000 Delta E; roughly 1.0 corresponds to one
        just-noticeable difference for uniform patches
    """
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0

    g = 0.5 * (1.0 - math.sqrt(c_bar**7 / (c_bar**7 + 25.0**7)))
    a1p = (1.0 + g) * a1
    a2p = (1.0 + g) * a2
    c1p = math.hypot(a1p, b1)
    c2p = math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360

    d_lp = l2 - l1
    d_cp = c2p - c1p

    if c1p * c2p == 0:
        d_hp = 0.0
    elif abs(h2p - h1p) <= 180:
        d_hp = h2p - h1p
    elif h2p - h1p > 180:
        d_hp = h2p - h1p - 360
    else:
        d_hp = h2p - h1p + 360
    d_hp_upper = 2.0 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_hp / 2.0))

    lp_bar = (l1 + l2) / 2.0
    cp_bar = (c1p + c2p) / 2.0

    if c1p * c2p == 0:
        hp_bar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hp_bar = (h1p + h2p) / 2.0
    elif h1p + h2p < 360:
        hp_bar = (h1p + h2p + 360) / 2.0
    else:
        hp_bar = (h1p + h2p - 360) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(hp_bar - 30))
        + 0.24 * math.cos(math.radians(2 * hp_bar))
        + 0.32 * math.cos(math.radians(3 * hp_bar + 6))
        - 0.20 * math.cos(math.radians(4 * hp_bar - 63))
    )
    d_theta = 30.0 * math.exp(-(((hp_bar - 275.0) / 25.0) ** 2))
    r_c = 2.0 * math.sqrt(cp_bar**7 / (cp_bar**7 + 25.0**7))
    s_l = 1.0 + (0.015 * (lp_bar - 50.0) ** 2) / math.sqrt(20.0 + (lp_bar - 50.0) ** 2)
    s_c = 1.0 + 0.045 * cp_bar
    s_h = 1.0 + 0.015 * cp_bar * t
    r_t = -math.sin(math.radians(2.0 * d_theta)) * r_c

    return math.sqrt(
        (d_lp / s_l) ** 2
        + (d_cp / s_c) ** 2
        + (d_hp_upper / s_h) ** 2
        + r_t * (d_cp / s_c) * (d_hp_upper / s_h)
    )


def relative_luminance(rgb: RGB) -> float:
    """WCAG 2.2 relative luminance of an sRGB color.

    Uses the coefficients and the 0.03928 threshold from the WCAG 2.2
    "relative luminance" definition, which differ slightly from the
    IEC sRGB companding constants.

    Args:
        rgb: RGB tuple of (red, green, blue) values (0-255)

    Returns:
        Relative luminance in 0-1
    """

    def linearize(c: int) -> float:
        c_srgb = c / 255
        if c_srgb <= 0.03928:
            return c_srgb / 12.92
        return math.pow((c_srgb + 0.055) / 1.055, 2.4)

    r, g, b = (linearize(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def gamut_map_oklch(lch: OKLCh) -> RGB:
    """Map an OKLCh color into the sRGB gamut, preserving hue and lightness.

    Reduces chroma by binary search until the color fits the sRGB gamut,
    per the CSS Color 4 gamut-mapping approach: clipping alone shifts hue,
    while chroma reduction keeps the perceived hue constant. Lightness is
    clamped into 0-1 first.

    Args:
        lch: OKLCh tuple (L, C, H in degrees)

    Returns:
        In-gamut RGB tuple of (red, green, blue) values (0-255)
    """
    lightness, chroma, hue = lch
    lightness = min(1.0, max(0.0, lightness))

    def fits(c: float) -> bool:
        linear = _oklab_to_linear_srgb(oklch_to_oklab((lightness, c, hue)))
        return all(-_GAMUT_TOLERANCE <= v <= 1.0 + _GAMUT_TOLERANCE for v in linear)

    if fits(chroma):
        return oklab_to_rgb(oklch_to_oklab((lightness, chroma, hue)))

    low, high = 0.0, chroma
    for _ in range(32):
        mid = (low + high) / 2.0
        if fits(mid):
            low = mid
        else:
            high = mid
    return oklab_to_rgb(oklch_to_oklab((lightness, low, hue)))
