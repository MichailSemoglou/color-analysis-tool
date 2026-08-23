"""
Core analyzer module for Color Analysis Tool.

This module provides classes for analyzing colors in images, including:
- ColorConverter: Color space conversion utilities
- ColorHarmony: Color harmony calculations
- ImageAnalyzer: Main image analysis functionality
"""

import colorsys
import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union, cast

from PIL import Image
from tqdm import tqdm

from . import exporters

# Guard against decompression bomb attacks. This intentionally retains
# Pillow's default limit of ~179 MP rather than tightening it: the tool's
# archival and design audience routinely processes high-resolution scans in
# the 100-170 MP range, so a lower limit would reject legitimate input. The
# explicit assignment keeps the limit stable if Pillow's default ever changes.
Image.MAX_IMAGE_PIXELS = 178_956_970  # Pillow default, ~179 MP

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases
RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]
CMYK = Tuple[int, int, int, int]

VALID_SORT_OPTIONS = {"frequency", "hue", "saturation", "brightness"}

# Number of top colors for which harmonies are computed
HARMONY_LIMIT = 50

# Automatic palette bounds used when max_colors="auto": analyze every unique
# visible color up to the threshold, quantize to the palette size beyond it
AUTO_PALETTE_THRESHOLD = 256
AUTO_PALETTE_SIZE = 32


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
    as duplicates with split frequencies.
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

    Bounded probe for the auto-palette decision: it stops at threshold + 1
    unique colors, so its memory cost does not scale with the number of
    colors in the image.
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

    MEDIANCUT quantizes RGB only, so the alpha channel is reattached
    afterwards. The RGB payload of fully transparent pixels is flattened to
    a single color first: invisible pixels then occupy at most one palette
    slot instead of shifting palette boundaries.
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
        cmyk: CMYK color values as a tuple of (cyan, magenta, yellow, black)
        frequency: Percentage of image pixels with this color
        harmonies: Dictionary of color harmony types to lists of RGB colors
    """
    rgb: RGB
    hex: str
    cmyk: CMYK
    frequency: float
    harmonies: Dict[str, List[RGB]]


@dataclass
class ImageInfo:
    """Data class to store analysis results for an image.

    Attributes:
        filename: Name of the analyzed image file
        dimensions: Image dimensions as (width, height)
        format: Image file format (e.g., 'JPEG', 'PNG')
        colors: List of ColorInfo objects for all colors in the image
        dominant_color: RGB values of the most frequent color
    """
    filename: str
    dimensions: Tuple[int, int]
    format: str
    colors: List[ColorInfo]
    dominant_color: Optional[RGB] = None


class ColorConverter:
    """Utility class for color space conversions."""

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
    def rgb_to_cmyk(r: int, g: int, b: int) -> CMYK:
        """Convert RGB color to CMYK.

        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)

        Returns:
            CMYK tuple of (cyan, magenta, yellow, black) percentages (0-100)

        Raises:
            ValueError: If a channel value falls outside 0-255.
        """
        _validate_rgb((r, g, b), "rgb_to_cmyk")
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


class ColorHarmony:
    """Class for calculating color harmonies."""

    @staticmethod
    def find_harmonies(base_color: RGB) -> Dict[str, List[RGB]]:
        """Calculate color harmonies for a given base color.

        Calculates complementary, analogous, triadic, and tetradic
        color harmonies based on color theory principles.

        Args:
            base_color: RGB tuple of the base color

        Returns:
            Dictionary mapping harmony type names to lists of RGB colors

        Raises:
            ValueError: If base_color does not hold three channel values in 0-255.
        """
        _validate_rgb(base_color, "find_harmonies")
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
        >>> analyzer = ImageAnalyzer()
        >>> image_info = analyzer.analyze_image('photo.jpg', sort_by='hue')
        >>> analyzer.save_analysis('output/', image_info)
    """

    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.webp', '.psd'}

    def analyze_image(
        self,
        file_path: Union[str, Path],
        sort_by: str = "frequency",
        max_colors: Union[int, str] = "auto",
    ) -> Optional[ImageInfo]:
        """Analyze colors in an image file.

        Args:
            file_path: Path to the image file
            sort_by: Sorting criterion for colors. One of:
                'frequency' (default), 'hue', 'saturation', 'brightness'
            max_colors: Palette size control. 'auto' (default) analyzes every
                unique visible color when there are at most 256, and otherwise
                quantizes to a bounded 32-color palette. An integer N (1-256)
                always quantizes to that palette size; 0 disables quantization
                entirely (unbounded output).

        Returns:
            ImageInfo object containing analysis results, or None if analysis
            fails. Frequencies are percentages of the visible (non-transparent)
            pixels. A fully transparent image yields an ImageInfo with an
            empty colors list and dominant_color=None.

        Raises:
            ValueError: If sort_by is not a recognised sort option, or if
                max_colors is neither 'auto' nor an integer in 0-256.
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

        file_path = Path(file_path)
        try:
            with Image.open(file_path) as img:
                original_format = img.format or "UNKNOWN"
                dimensions = img.size
                image = img.convert("RGBA")

        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            logger.error(f"Error opening {file_path}: {exc}")
            return None

        if isinstance(max_colors, str):  # "auto", validated above
            # Bounded probe: the threshold decision must not build a full
            # Counter over a high-color image first
            if _unique_visible_exceeds(image, AUTO_PALETTE_THRESHOLD):
                logger.info(
                    f"{file_path}: more than {AUTO_PALETTE_THRESHOLD} unique "
                    f"visible colors, quantizing to {AUTO_PALETTE_SIZE} (auto palette)"
                )
                image = _quantize_preserving_alpha(image, AUTO_PALETTE_SIZE)
        elif max_colors > 0:
            image = _quantize_preserving_alpha(image, max_colors)

        rgb_counts = _count_visible_rgb(image)

        # Sort by frequency descending
        visible_colors = rgb_counts.most_common()

        # Frequencies are relative to the visible-pixel count, so palettes
        # from images with transparency still sum to 100%. A fully
        # transparent image yields an empty palette and no dominant color.
        visible_pixels = sum(count for _, count in visible_colors)
        if visible_pixels == 0:
            logger.warning(f"{file_path} has no visible (non-transparent) pixels")

        if sort_by == "hue":
            visible_colors.sort(
                key=lambda item: colorsys.rgb_to_hsv(
                    item[0][0] / 255, item[0][1] / 255, item[0][2] / 255
                )[0]
            )
        elif sort_by == "saturation":
            visible_colors.sort(
                key=lambda item: colorsys.rgb_to_hsv(
                    item[0][0] / 255, item[0][1] / 255, item[0][2] / 255
                )[1],
                reverse=True,
            )
        elif sort_by == "brightness":
            visible_colors.sort(
                key=lambda item: colorsys.rgb_to_hsv(
                    item[0][0] / 255, item[0][1] / 255, item[0][2] / 255
                )[2],
                reverse=True,
            )
        # "frequency" is already the default order from most_common()

        dominant_color: Optional[RGB] = None
        if visible_colors:
            # Dominant color is the most frequent visible color, regardless
            # of sort order; fully transparent pixels are never selected
            most_frequent = max(visible_colors, key=lambda item: item[1])[0]
            dominant_color = (most_frequent[0], most_frequent[1], most_frequent[2])

        colors: List[ColorInfo] = []
        for idx, (color, count) in enumerate(tqdm(visible_colors, desc="Analyzing colors")):
            r, g, b = color
            rgb: RGB = (r, g, b)
            harmonies = (
                ColorHarmony.find_harmonies(rgb) if idx < HARMONY_LIMIT else {}
            )
            colors.append(ColorInfo(
                rgb=rgb,
                hex=ColorConverter.rgb_to_hex(rgb),
                cmyk=ColorConverter.rgb_to_cmyk(r, g, b),
                frequency=round((count / visible_pixels) * 100, 2),
                harmonies=harmonies,
            ))

        return ImageInfo(
            filename=file_path.name,
            dimensions=dimensions,
            format=original_format,
            colors=colors,
            dominant_color=dominant_color,
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
            output_format: Output format — 'txt' (default), 'json', or 'css'.
                'css' emits three files: a CSS custom-properties stylesheet,
                a W3C Design Token JSON file, and a Tailwind config snippet.
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
    ) -> None:
        """Process all supported images in a directory recursively.

        Args:
            input_dir: Directory containing images to process.
            output_dir: Root directory where analysis results will be saved.
                Subdirectory structure from input_dir is mirrored.
            sort_by: Sorting criterion for colors in each analysis.
            max_colors: Palette size control, as in analyze_image ('auto'
                default, integer 1-256, or 0 for no quantization).
            output_format: 'txt', 'json', or 'css'.
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        # sorted() gives a deterministic processing order across filesystems
        for file_path in tqdm(sorted(input_dir.rglob('*')), desc="Processing files"):
            if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                logger.info(f"Processing {file_path}...")
                image_info = self.analyze_image(file_path, sort_by=sort_by, max_colors=max_colors)
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
