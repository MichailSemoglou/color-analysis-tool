"""Core analyzer module for Color Analysis Tool.

This module provides classes for analyzing colors in images, including:
- ColorConverter: Color space conversion utilities
- ColorHarmony: Color harmony calculations
- ImageAnalyzer: Main image analysis functionality
"""

import colorsys
import io
import logging
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources as importlib_resources
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union, cast

from PIL import Image
from tqdm import tqdm

try:
    from PIL import ImageCms

    _HAS_IMAGECMS = True
except ImportError:  # pragma: no cover - Pillow wheels always bundle lcms
    ImageCms = None  # type: ignore[assignment]
    _HAS_IMAGECMS = False

from . import accessibility, clustering, color_spaces, exporters

# Guard against decompression bomb attacks. This intentionally retains
# Pillow's default limit of ~179 MP rather than tightening it: the tool's
# archival and design audience routinely processes high-resolution scans in
# the 100-170 MP range, so a lower limit would reject legitimate input. The
# explicit assignment keeps the limit stable if Pillow's default ever changes.
Image.MAX_IMAGE_PIXELS = 178_956_970  # Pillow default, ~179 MP

logger = logging.getLogger(__name__)

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]
CMYK = Tuple[int, int, int, int]

VALID_SORT_OPTIONS = {"frequency", "hue", "saturation", "brightness"}

# Palette extraction engines: perceptual OKLab clustering (v2 default)
# or the v1 exact-counting pipeline
VALID_EXTRACTORS = {"perceptual", "legacy"}

# CMYK conversion methods: ICC color management (v2 default) or the v1
# device-naive formula
VALID_CMYK_METHODS = {"icc", "device_naive"}

# Number of top colors for which harmonies are computed
HARMONY_LIMIT = 50

# Automatic palette bounds used when max_colors="auto": analyze every unique
# visible color up to the threshold; beyond it, reduce to the palette size
# (clustering under the perceptual extractor, quantization under legacy)
AUTO_PALETTE_THRESHOLD = 256
AUTO_PALETTE_SIZE = 32

# Bundled ICC profile for the default sRGB -> CMYK conversion (FOGRA39,
# ISO Coated v2 by the European Color Initiative); loaded lazily from
# package data, replaceable via the profile argument of rgb_to_cmyk
DEFAULT_CMYK_PROFILE = "ISOcoated_v2_eci.icc"

# Display name recorded in outputs for the default CMYK conversion
DEFAULT_CMYK_PROFILE_NAME = "FOGRA39 (ISO Coated v2)"


def _validate_rgb(rgb: Tuple[int, ...], func_name: str) -> None:
    """Raise ValueError unless rgb holds exactly three channels in 0-255."""
    if (
        len(rgb) != 3
        or not all(
            isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255
            for v in rgb
        )
    ):
        raise ValueError(
            f"{func_name} expects three channel values in 0-255, got {rgb!r}"
        )


def _count_visible_rgb(image: Image.Image) -> "Counter[RGB]":
    """Count pixels by RGB value, dropping fully transparent pixels.

    Alpha only decides whether a pixel is visible, so semi-transparent
    variants of one color merge into a single count instead of appearing
    as duplicates with split weights.
    """
    # cast: Pillow types get_flattened_data loosely; callers pass RGBA
    # images. Counter consumes the iterable directly, so no full pixel
    # list is ever materialized.
    pixels = cast(Iterable[RGBA], image.get_flattened_data())
    counts: Counter[RGB] = Counter()
    for (r, g, b, a), count in Counter(pixels).items():
        if a > 0:
            counts[(r, g, b)] += count
    return counts


def _unique_visible_exceeds(image: Image.Image, threshold: int) -> bool:
    """Return True when an image has more than threshold unique visible colors.

    Bounded probe for the auto-palette decision in the legacy extractor:
    it stops at threshold + 1 unique colors, so its memory cost does not
    scale with the number of colors in the image. The perceptual extractor
    does not use it; clustering needs the full color counts anyway.
    """
    seen = set()
    for r, g, b, a in cast(Iterable[RGBA], image.get_flattened_data()):
        if a > 0:
            seen.add((r, g, b))
            if len(seen) > threshold:
                return True
    return False


def _quantize_preserving_alpha(image: Image.Image, colors: int) -> Image.Image:
    """Quantize an RGBA image to at most colors colors, preserving alpha.

    Used only by the legacy extractor; the perceptual extractor clusters
    the counted colors instead. MEDIANCUT quantizes RGB only, so the alpha
    channel is reattached afterwards. The RGB payload of fully transparent
    pixels is flattened to a single color first: invisible pixels then
    occupy at most one palette slot instead of shifting palette boundaries.
    """
    rgba = image.convert("RGBA")
    rgb_image = rgba.convert("RGB")
    transparent_mask = rgba.getchannel("A").point(lambda a: 255 if a == 0 else 0)
    rgb_image.paste((0, 0, 0), mask=transparent_mask)
    quantized = rgb_image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    result = quantized.convert("RGB")
    result.putalpha(rgba.getchannel("A"))
    return result


@dataclass
class ColorInfo:
    """Data class to store information about a single color.

    Attributes:
        rgb: RGB color values as a tuple of (red, green, blue)
        hex: Hexadecimal color representation
        cmyk: CMYK color values as a tuple of (cyan, magenta, yellow,
            black) percentages; ICC-based (FOGRA39) by default
        weight: Percentage of visible image pixels covered by this color
            (cluster weight for the perceptual extractor, exact pixel
            frequency otherwise)
        oklch: OKLCh coordinates (L in 0-1, C >= 0, H in degrees 0-360),
            rounded to 4 decimal places; achromatic colors report hue 0
        harmonies: Dictionary of color harmony types to lists of RGB colors
        contrast: WCAG 2.2 and APCA contrast report against white, black,
            and the dominant color
    """
    rgb: RGB
    hex: str
    cmyk: CMYK
    weight: float
    oklch: color_spaces.OKLCh
    harmonies: Dict[str, List[RGB]]
    contrast: Optional[accessibility.ContrastReport] = None


@dataclass
class ImageInfo:
    """Data class to store analysis results for an image.

    Attributes:
        filename: Name of the analyzed image file
        dimensions: Image dimensions as (width, height)
        format: Image file format (e.g., 'JPEG', 'PNG')
        colors: List of ColorInfo objects for all colors in the image
        dominant_color: RGB values of the highest-weight color
        cmyk_profile: Display name of the ICC profile behind the CMYK
            values; defaults to the bundled FOGRA39 profile name
    """
    filename: str
    dimensions: Tuple[int, int]
    format: str
    colors: List[ColorInfo]
    dominant_color: Optional[RGB] = None
    cmyk_profile: str = DEFAULT_CMYK_PROFILE_NAME


class ColorConverter:
    """Utility class for color space conversions.

    Example:
        >>> ColorConverter.rgb_to_hex((255, 128, 0))
        '#ff8000'
        >>> ColorConverter.hex_to_rgb("#f80")
        (255, 136, 0)
        >>> ColorConverter.rgb_to_cmyk(255, 0, 0, method="device_naive")
        (0, 100, 100, 0)
    """

    @staticmethod
    def hex_to_rgb(hex_color: str) -> RGB:
        """Convert hexadecimal color to RGB.

        Accepts six-digit hex strings ('#FF5733' or 'FF5733') and the
        three-digit CSS shorthand ('#f53' or 'f53'), which is expanded
        per CSS rules ('f53' is treated as 'ff5533').

        Args:
            hex_color: Hexadecimal color string, with optional leading '#'

        Returns:
            RGB tuple of (red, green, blue) values (0-255)

        Raises:
            ValueError: If the string is not a valid 3- or 6-digit
                hexadecimal color.
        """
        value = hex_color.removeprefix('#')
        if len(value) == 3:
            # Expand CSS shorthand, e.g. 'f53' -> 'ff5533'
            value = ''.join(c * 2 for c in value)
        if len(value) != 6 or any(c not in '0123456789abcdefABCDEF' for c in value):
            raise ValueError(
                f"Invalid hex color {hex_color!r}: expected 3 or 6 hexadecimal digits"
            )
        r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
        return (r, g, b)

    @staticmethod
    def rgb_to_hex(rgb: RGB) -> str:
        """Convert RGB color to hexadecimal.

        Args:
            rgb: RGB tuple of (red, green, blue) values (0-255)

        Returns:
            Hexadecimal color string (e.g., '#ff5733')

        Raises:
            ValueError: If rgb does not hold three channel values in 0-255.
        """
        _validate_rgb(rgb, "rgb_to_hex")
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    @staticmethod
    def rgb_to_cmyk(
        r: int,
        g: int,
        b: int,
        method: str = "icc",
        profile: Optional[Union[str, Path]] = None,
    ) -> CMYK:
        """Convert RGB color to CMYK.

        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)
            method: 'icc' (default) converts through ICC profiles using
                Pillow's LittleCMS binding, from sRGB to the bundled
                FOGRA39 profile (ISO Coated v2) with perceptual intent,
                producing print-meaningful values. 'device_naive' applies
                the classic undercolor-removal formula, which performs no
                gamut mapping and corresponds to no real press condition.
            profile: Optional path to a custom CMYK ICC profile used
                instead of the bundled default when method='icc'.

        Returns:
            CMYK tuple of (cyan, magenta, yellow, black) percentages (0-100)

        Raises:
            ValueError: If a channel value falls outside 0-255, or method
                is not 'icc' or 'device_naive'.
            RuntimeError: If method='icc' but Pillow lacks LittleCMS support.
            OSError: If a custom profile path cannot be opened.
        """
        _validate_rgb((r, g, b), "rgb_to_cmyk")
        return ColorConverter.rgb_to_cmyk_batch(
            [(r, g, b)], method=method, profile=profile
        )[0]

    @staticmethod
    def rgb_to_cmyk_batch(
        colors: Iterable[RGB],
        method: str = "icc",
        profile: Optional[Union[str, Path]] = None,
    ) -> List[CMYK]:
        """Convert multiple RGB colors to CMYK in a single pass.

        Batching applies the ICC profile transform once for the whole list
        instead of once per color, which matters for large palettes (for
        example max_colors=0 on a high-color image).

        Args:
            colors: Iterable of RGB tuples (0-255 channels)
            method: 'icc' (default) or 'device_naive', as in rgb_to_cmyk
            profile: Optional path to a custom CMYK ICC profile used
                instead of the bundled default when method='icc'

        Returns:
            List of CMYK tuples (percentages 0-100), aligned with the
            input order

        Raises:
            ValueError: If any color has a channel value outside 0-255,
                or method is not 'icc' or 'device_naive'.
            RuntimeError: If method='icc' but Pillow lacks LittleCMS support.
            OSError: If a custom profile path cannot be opened.
        """
        rgbs = list(colors)
        for rgb in rgbs:
            _validate_rgb(rgb, "rgb_to_cmyk_batch")
        if method == "device_naive":
            return [
                ColorConverter._rgb_to_cmyk_naive(r, g, b) for r, g, b in rgbs
            ]
        if method != "icc":
            raise ValueError(
                f"method must be 'icc' or 'device_naive', got {method!r}"
            )
        if not _HAS_IMAGECMS:
            raise RuntimeError(
                "ICC conversion requires Pillow with LittleCMS (ImageCms) support"
            )
        if not rgbs:
            return []
        transform = ColorConverter._cmyk_transform(
            str(profile) if profile is not None else None
        )
        strip = Image.new("RGB", (len(rgbs), 1))
        strip.putdata(rgbs)
        converted = transform.apply(strip)
        result: List[CMYK] = []
        for c, m, y, k in cast(
            Iterable[Tuple[int, int, int, int]], converted.get_flattened_data()
        ):
            result.append(
                (
                    round(c / 255 * 100),
                    round(m / 255 * 100),
                    round(y / 255 * 100),
                    round(k / 255 * 100),
                )
            )
        return result

    @staticmethod
    @lru_cache(maxsize=4)
    def _cmyk_transform(profile_path: Optional[str]):
        """Build (and cache) the sRGB -> CMYK profile transform."""
        if profile_path is None:
            data = (
                importlib_resources.files("color_analysis_tool")
                .joinpath("profiles")
                .joinpath(DEFAULT_CMYK_PROFILE)
                .read_bytes()
            )
            cmyk_profile = ImageCms.ImageCmsProfile(io.BytesIO(data))
        else:
            cmyk_profile = ImageCms.ImageCmsProfile(profile_path)
        srgb_profile = ImageCms.createProfile("sRGB")
        return ImageCms.buildTransformFromOpenProfiles(
            srgb_profile, cmyk_profile, "RGB", "CMYK"
        )

    @staticmethod
    def _rgb_to_cmyk_naive(r: int, g: int, b: int) -> CMYK:
        """Device-naive RGB to CMYK formula (no color management)."""
        if r == g == b == 0:
            return (0, 0, 0, 100)

        c = 1 - r / 255
        m = 1 - g / 255
        y = 1 - b / 255
        k = min(c, m, y)

        c = (c - k) / (1 - k)
        m = (m - k) / (1 - k)
        y = (y - k) / (1 - k)

        return (
            round(c * 100),
            round(m * 100),
            round(y * 100),
            round(k * 100),
        )

    @staticmethod
    def rgb_to_oklab(rgb: RGB) -> color_spaces.OKLab:
        """Convert RGB to OKLab (Ottosson 2020).

        Args:
            rgb: RGB tuple of (red, green, blue) values (0-255)

        Returns:
            OKLab tuple (L in 0-1, a and b unbounded)

        Raises:
            ValueError: If rgb does not hold three channel values in 0-255.
        """
        _validate_rgb(rgb, "rgb_to_oklab")
        return color_spaces.rgb_to_oklab(rgb)

    @staticmethod
    def rgb_to_oklch(rgb: RGB) -> color_spaces.OKLCh:
        """Convert RGB to OKLCh (cylindrical OKLab).

        Args:
            rgb: RGB tuple of (red, green, blue) values (0-255)

        Returns:
            OKLCh tuple (L in 0-1, C >= 0, H in degrees 0-360)

        Raises:
            ValueError: If rgb does not hold three channel values in 0-255.
        """
        _validate_rgb(rgb, "rgb_to_oklch")
        return color_spaces.rgb_to_oklch(rgb)

    @staticmethod
    def rgb_to_xyz(rgb: RGB) -> color_spaces.XYZ:
        """Convert RGB to CIE XYZ (D65, Y normalized to 1).

        Args:
            rgb: RGB tuple of (red, green, blue) values (0-255)

        Returns:
            XYZ tuple with Y in 0-1

        Raises:
            ValueError: If rgb does not hold three channel values in 0-255.
        """
        _validate_rgb(rgb, "rgb_to_xyz")
        return color_spaces.rgb_to_xyz(rgb)

    @staticmethod
    def rgb_to_lab(rgb: RGB) -> color_spaces.LAB:
        """Convert RGB to CIELAB (D65, CIE 1976).

        Args:
            rgb: RGB tuple of (red, green, blue) values (0-255)

        Returns:
            LAB tuple (L in 0-100)

        Raises:
            ValueError: If rgb does not hold three channel values in 0-255.
        """
        _validate_rgb(rgb, "rgb_to_lab")
        return color_spaces.rgb_to_lab(rgb)


class ColorHarmony:
    """Class for calculating color harmonies."""

    VALID_ENGINES = {"oklch", "hsv_legacy"}

    @staticmethod
    def find_harmonies(base_color: RGB, engine: str = "oklch") -> Dict[str, List[RGB]]:
        """Calculate color harmonies for a given base color.

        Calculates complementary, analogous, triadic, and tetradic
        color harmonies based on color theory principles.

        Args:
            base_color: RGB tuple of the base color
            engine: Harmony engine. 'oklch' (default) rotates hue in OKLCh
                and maps results into the sRGB gamut by hue-preserving
                chroma reduction, giving perceptually even hue steps.
                'hsv_legacy' reproduces the v1 HSV hue rotation.

        Returns:
            Dictionary mapping harmony type names to lists of RGB colors

        Raises:
            ValueError: If base_color does not hold three channel values
                in 0-255, or engine is not 'oklch' or 'hsv_legacy'.
        """
        _validate_rgb(base_color, "find_harmonies")
        if engine == "hsv_legacy":
            return ColorHarmony._find_harmonies_hsv(base_color)
        if engine != "oklch":
            raise ValueError(
                f"engine must be one of {ColorHarmony.VALID_ENGINES}, got {engine!r}"
            )
        return ColorHarmony._find_harmonies_oklch(base_color)

    @staticmethod
    def _find_harmonies_oklch(base_color: RGB) -> Dict[str, List[RGB]]:
        """OKLCh hue rotation with hue-preserving gamut mapping."""
        lightness, chroma, hue = color_spaces.rgb_to_oklch(base_color)

        hue_sets: Dict[str, List[float]] = {
            'complementary': [(hue + 180) % 360],
            'analogous': [(hue - 30) % 360, hue, (hue + 30) % 360],
            'triadic': [(hue + 120) % 360, hue, (hue + 240) % 360],
            'tetradic': [hue, (hue + 90) % 360, (hue + 180) % 360, (hue + 270) % 360],
        }

        return {
            key: [
                color_spaces.gamut_map_oklch((lightness, chroma, h))
                for h in hues
            ]
            for key, hues in hue_sets.items()
        }

    @staticmethod
    def _find_harmonies_hsv(base_color: RGB) -> Dict[str, List[RGB]]:
        """v1 HSV hue rotation, retained for reproducibility."""
        r, g, b = base_color
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        h = h * 360

        hsv_sets: Dict[str, List[Tuple[float, float, float]]] = {
            'complementary': [((h + 180) % 360, s, v)],
            'analogous': [
                ((h - 30) % 360, s, v),
                (h, s, v),
                ((h + 30) % 360, s, v),
            ],
            'triadic': [
                ((h + 120) % 360, s, v),
                (h, s, v),
                ((h + 240) % 360, s, v),
            ],
            'tetradic': [
                (h, s, v),
                ((h + 90) % 360, s, v),
                ((h + 180) % 360, s, v),
                ((h + 270) % 360, s, v),
            ],
        }

        return {
            key: [
                tuple(round(x * 255) for x in colorsys.hsv_to_rgb(hh / 360, ss, vv))  # type: ignore[misc]
                for hh, ss, vv in colors
            ]
            for key, colors in hsv_sets.items()
        }


class ImageAnalyzer:
    """Main class for image analysis functionality.

    This class provides methods to analyze colors in images, including
    extracting color information, calculating harmonies, and saving
    analysis results.

    Attributes:
        SUPPORTED_FORMATS: Set of supported image file extensions

    Example:
        analyzer = ImageAnalyzer()
        image_info = analyzer.analyze_image('photo.jpg', sort_by='hue')
        analyzer.save_analysis('output/', image_info)
    """

    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.webp', '.psd'}

    def analyze_image(
        self,
        file_path: Union[str, Path],
        sort_by: str = "frequency",
        max_colors: Union[int, str] = "auto",
        extractor: str = "perceptual",
        harmony_engine: str = "oklch",
        cmyk_profile: Optional[Union[str, Path]] = None,
        cmyk_method: str = "icc",
    ) -> Optional[ImageInfo]:
        """Analyze colors in an image file.

        Args:
            file_path: Path to the image file
            sort_by: Sorting criterion for colors. One of:
                'frequency' (default; sorts by weight), 'hue',
                'saturation', 'brightness'
            max_colors: Palette size control. 'auto' (default) analyzes every
                unique visible color when there are at most 256, and otherwise
                reduces to a bounded 32-color palette. An integer N (1-256)
                always reduces to at most N colors; 0 disables palette
                reduction entirely (unbounded output).
            extractor: Palette extraction engine. 'perceptual' (default)
                clusters colors with deterministic k-means++ in OKLab and
                merges near-duplicates at CIEDE2000 2.2; reported weights
                are cluster coverage of the visible pixels. 'legacy'
                reproduces the v1 pipeline (exact frequency counting with
                median-cut quantization for palette reduction).
            harmony_engine: Harmony engine passed to ColorHarmony:
                'oklch' (default) or 'hsv_legacy'.
            cmyk_profile: Optional path to a custom CMYK ICC profile used
                for the CMYK values; defaults to the bundled FOGRA39
                profile (ISO Coated v2).
            cmyk_method: CMYK conversion method passed to ColorConverter:
                'icc' (default) or 'device_naive' (the v1 formula).

        Returns:
            ImageInfo object containing analysis results, or None if analysis
            fails. Weights are percentages of the visible (non-transparent)
            pixels. A fully transparent image yields an ImageInfo with an
            empty colors list and dominant_color=None.

        Raises:
            ValueError: If sort_by is not a recognised sort option, if
                max_colors is neither 'auto' nor an integer in 0-256, if
                extractor is not 'perceptual' or 'legacy', if
                harmony_engine is not 'oklch' or 'hsv_legacy', or if
                cmyk_method is not 'icc' or 'device_naive'.
            OSError: If a custom cmyk_profile path cannot be opened.
        """
        if sort_by not in VALID_SORT_OPTIONS:
            raise ValueError(
                f"sort_by must be one of {VALID_SORT_OPTIONS}, got {sort_by!r}"
            )
        if isinstance(max_colors, str):
            if max_colors != "auto":
                raise ValueError(
                    f"max_colors must be 'auto' or an integer 0-256, got {max_colors!r}"
                )
        elif (
            isinstance(max_colors, bool)
            or not isinstance(max_colors, int)
            or not 0 <= max_colors <= 256
        ):
            raise ValueError(
                f"max_colors must be between 0 and 256, got {max_colors!r}"
            )
        if extractor not in VALID_EXTRACTORS:
            raise ValueError(
                f"extractor must be one of {VALID_EXTRACTORS}, got {extractor!r}"
            )
        if harmony_engine not in ColorHarmony.VALID_ENGINES:
            raise ValueError(
                f"harmony_engine must be one of {ColorHarmony.VALID_ENGINES}, "
                f"got {harmony_engine!r}"
            )
        if cmyk_method not in VALID_CMYK_METHODS:
            raise ValueError(
                f"cmyk_method must be one of {VALID_CMYK_METHODS}, "
                f"got {cmyk_method!r}"
            )

        file_path = Path(file_path)
        try:
            with Image.open(file_path) as img:
                original_format = img.format or "UNKNOWN"
                dimensions = img.size
                image = img.convert("RGBA")

        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            logger.error(f"Error opening {file_path}: {exc}")
            return None

        if extractor == "legacy":
            # v1 pipeline: exact counting, median-cut palette reduction.
            # The bounded probe avoids building a full Counter over a
            # high-color image before the threshold decision
            if isinstance(max_colors, str):  # "auto", validated above
                if _unique_visible_exceeds(image, AUTO_PALETTE_THRESHOLD):
                    logger.info(
                        f"{file_path}: more than {AUTO_PALETTE_THRESHOLD} unique "
                        f"visible colors, quantizing to {AUTO_PALETTE_SIZE} (auto palette)"
                    )
                    image = _quantize_preserving_alpha(image, AUTO_PALETTE_SIZE)
            elif max_colors > 0:
                image = _quantize_preserving_alpha(image, max_colors)
            rgb_counts = _count_visible_rgb(image)
            visible_pixels = sum(rgb_counts.values())
            entries: List[Tuple[RGB, float]] = [
                (rgb, round(100 * count / visible_pixels, 2) if visible_pixels else 0.0)
                for rgb, count in rgb_counts.items()
            ]
        else:
            # Perceptual pipeline: k-means++ in OKLab with coverage weights
            rgb_counts = _count_visible_rgb(image)
            visible_pixels = sum(rgb_counts.values())
            if isinstance(max_colors, str):
                k: Optional[int] = (
                    None
                    if len(rgb_counts) <= AUTO_PALETTE_THRESHOLD
                    else AUTO_PALETTE_SIZE
                )
            elif max_colors == 0:
                k = None
            else:
                k = max_colors
            if k is None or len(rgb_counts) <= k:
                entries = [
                    (rgb, round(100 * count / visible_pixels, 2) if visible_pixels else 0.0)
                    for rgb, count in rgb_counts.items()
                ]
            else:
                clusters = clustering.extract_palette(rgb_counts, k)
                entries = [(c.rgb, c.weight) for c in clusters]

        # Weights are relative to the visible-pixel count, so palettes
        # from images with transparency still sum to 100%. A fully
        # transparent image yields an empty palette and no dominant color.
        if visible_pixels == 0:
            logger.warning(f"{file_path} has no visible (non-transparent) pixels")

        # Sort by weight descending, then apply the requested criterion
        entries.sort(key=lambda item: (-item[1], item[0]))

        # Dominant color is the highest-weight visible color, resolved on
        # the deterministic weight order so it does not depend on sort_by;
        # transparent pixels never count
        dominant_color: Optional[RGB] = entries[0][0] if entries else None

        if sort_by == "hue":
            entries.sort(
                key=lambda item: colorsys.rgb_to_hsv(
                    item[0][0] / 255, item[0][1] / 255, item[0][2] / 255
                )[0]
            )
        elif sort_by == "saturation":
            entries.sort(
                key=lambda item: colorsys.rgb_to_hsv(
                    item[0][0] / 255, item[0][1] / 255, item[0][2] / 255
                )[1],
                reverse=True,
            )
        elif sort_by == "brightness":
            entries.sort(
                key=lambda item: colorsys.rgb_to_hsv(
                    item[0][0] / 255, item[0][1] / 255, item[0][2] / 255
                )[2],
                reverse=True,
            )

        # One ICC transform for the whole palette, not one per color
        cmyk_values = ColorConverter.rgb_to_cmyk_batch(
            [rgb for rgb, _ in entries], method=cmyk_method, profile=cmyk_profile
        )

        colors: List[ColorInfo] = []
        for idx, ((rgb, weight), cmyk) in enumerate(
            tqdm(zip(entries, cmyk_values), total=len(entries), desc="Analyzing colors")
        ):
            harmonies = (
                ColorHarmony.find_harmonies(rgb, engine=harmony_engine)
                if idx < HARMONY_LIMIT
                else {}
            )
            colors.append(ColorInfo(
                rgb=rgb,
                hex=ColorConverter.rgb_to_hex(rgb),
                cmyk=cmyk,
                weight=weight,
                oklch=color_spaces.normalize_oklch(color_spaces.rgb_to_oklch(rgb)),
                harmonies=harmonies,
                contrast=accessibility.contrast_report(rgb, dominant_color),
            ))

        return ImageInfo(
            filename=file_path.name,
            dimensions=dimensions,
            format=original_format,
            colors=colors,
            dominant_color=dominant_color,
            cmyk_profile=(
                Path(cmyk_profile).name if cmyk_profile else DEFAULT_CMYK_PROFILE_NAME
            ),
        )

    def save_analysis(
        self,
        output_dir: Union[str, Path],
        image_info: ImageInfo,
        sort_by: str = "frequency",
        output_format: str = "txt",
        input_base: Optional[Path] = None,
        file_path: Optional[Path] = None,
    ) -> None:
        """Save analysis results to a file.

        Args:
            output_dir: Root directory where analysis files will be saved.
            image_info: ImageInfo object containing the analysis results.
            sort_by: The sorting criterion used (recorded in the output).
            output_format: Output format - 'txt' (default), 'json', or 'css'.
                'css' emits three files: a CSS custom-properties stylesheet,
                a W3C Design Token JSON file, and a Tailwind CSS v4 @theme file.
            input_base: Base input directory used to mirror subdirectory
                structure inside output_dir for batch processing.
            file_path: Original file path; used with input_base to compute
                the relative subdirectory for output.

        Raises:
            ValueError: If output_format is not recognised.
        """
        exporters.save_analysis(
            output_dir,
            image_info,
            sort_by=sort_by,
            output_format=output_format,
            input_base=input_base,
            file_path=file_path,
        )

    def batch_process(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path],
        sort_by: str = "frequency",
        max_colors: Union[int, str] = "auto",
        output_format: str = "txt",
        extractor: str = "perceptual",
        harmony_engine: str = "oklch",
        cmyk_profile: Optional[Union[str, Path]] = None,
        cmyk_method: str = "icc",
    ) -> None:
        """Process all supported images in a directory recursively.

        Args:
            input_dir: Directory containing images to process.
            output_dir: Root directory where analysis results will be saved.
                Subdirectory structure from input_dir is mirrored.
            sort_by: Sorting criterion for colors in each analysis.
            max_colors: Palette size control, as in analyze_image ('auto'
                default, integer 1-256, or 0 for no palette reduction).
            output_format: 'txt', 'json', or 'css'.
            extractor: Palette extraction engine, as in analyze_image.
            harmony_engine: Harmony engine, as in analyze_image.
            cmyk_profile: Optional path to a custom CMYK ICC profile.
            cmyk_method: CMYK conversion method, as in analyze_image.
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        # sorted() gives a deterministic processing order across filesystems
        for file_path in tqdm(sorted(input_dir.rglob('*')), desc="Processing files"):
            if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                logger.info(f"Processing {file_path}...")
                image_info = self.analyze_image(
                    file_path,
                    sort_by=sort_by,
                    max_colors=max_colors,
                    extractor=extractor,
                    harmony_engine=harmony_engine,
                    cmyk_profile=cmyk_profile,
                    cmyk_method=cmyk_method,
                )
                if image_info:
                    try:
                        self.save_analysis(
                            output_dir,
                            image_info,
                            sort_by=sort_by,
                            output_format=output_format,
                            input_base=input_dir,
                            file_path=file_path,
                        )
                    except OSError as exc:
                        # Skip the failed file instead of aborting the batch
                        logger.error(f"Error saving analysis for {file_path}: {exc}")
