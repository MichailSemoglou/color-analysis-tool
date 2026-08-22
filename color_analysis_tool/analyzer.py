"""
Core analyzer module for Color Analysis Tool.

This module provides classes for analyzing colors in images, including:
- ColorConverter: Color space conversion utilities
- ColorHarmony: Color harmony calculations
- ImageAnalyzer: Main image analysis functionality
"""

import colorsys
import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, cast

from PIL import Image
from tqdm import tqdm

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
VALID_OUTPUT_FORMATS = {"txt", "json", "css"}

# Number of top colors for which harmonies are computed
HARMONY_LIMIT = 50


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


def _sanitize_display_name(name: str) -> str:
    """Return a filename safe to embed in generated reports and comments.

    Strips block-comment terminators, line breaks, and control characters
    so a hostile filename cannot inject content into generated files.
    """
    name = name.replace("*/", "")
    name = re.sub(r"[\r\n\u2028\u2029]+", " ", name)
    return "".join(c for c in name if c.isprintable())


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
        max_colors: int = 0,
    ) -> Optional[ImageInfo]:
        """Analyze colors in an image file.

        Args:
            file_path: Path to the image file
            sort_by: Sorting criterion for colors. One of:
                'frequency' (default), 'hue', 'saturation', 'brightness'
            max_colors: Maximum number of colors to include in results.
                Use 0 (default) for all colors. When > 0 the image is
                first quantized to that palette size, which both speeds
                up processing and produces a clean, meaningful palette.
                Must be between 0 and 256.

        Returns:
            ImageInfo object containing analysis results, or None if analysis
            fails. Frequencies are percentages of the visible (non-transparent)
            pixels. A fully transparent image yields an ImageInfo with an
            empty colors list and dominant_color=None.

        Raises:
            ValueError: If sort_by is not a recognised sort option, or if
                max_colors is outside the range 0-256.
        """
        if sort_by not in VALID_SORT_OPTIONS:
            raise ValueError(
                f"sort_by must be one of {VALID_SORT_OPTIONS}, got {sort_by!r}"
            )
        if not 0 <= max_colors <= 256:
            raise ValueError(
                f"max_colors must be between 0 and 256, got {max_colors!r}"
            )

        file_path = Path(file_path)
        try:
            with Image.open(file_path) as img:
                original_format = img.format or "UNKNOWN"
                dimensions = img.size

                if max_colors > 0:
                    # Quantize to a reduced palette for performance and clarity.
                    # MEDIANCUT quantizes RGB only, so the original alpha
                    # channel is reattached afterwards; transparent pixels
                    # stay transparent instead of becoming opaque black.
                    rgba = img.convert("RGBA")
                    rgb_image = rgba.convert("RGB")
                    # Flatten the RGB payload of fully transparent pixels to a
                    # single color: invisible pixels then occupy at most one
                    # palette slot instead of shifting palette boundaries.
                    transparent_mask = rgba.getchannel("A").point(lambda a: 255 if a == 0 else 0)
                    rgb_image.paste((0, 0, 0), mask=transparent_mask)
                    quantized = rgb_image.quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
                    image = quantized.convert("RGB")
                    image.putalpha(rgba.getchannel("A"))
                else:
                    image = img.convert("RGBA")

        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            logger.error(f"Error opening {file_path}: {exc}")
            return None

        # Aggregate by RGB value after dropping fully transparent pixels:
        # alpha only decides whether a pixel is visible, so semi-transparent
        # variants of one color merge into a single palette entry instead of
        # appearing as duplicates with split frequencies
        # (cast: Pillow types get_flattened_data loosely; the image is RGBA
        # by construction in both branches above)
        pixels = cast(List[RGBA], image.get_flattened_data())
        rgb_counts: Counter[RGB] = Counter()
        for (r, g, b, a), count in Counter(pixels).items():
            if a > 0:
                rgb_counts[(r, g, b)] += count

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
        if output_format not in VALID_OUTPUT_FORMATS:
            raise ValueError(
                f"output_format must be one of {VALID_OUTPUT_FORMATS}, got {output_format!r}"
            )

        output_dir = Path(output_dir)

        # Mirror subdirectory structure when batch-processing
        if input_base is not None and file_path is not None:
            try:
                rel = file_path.parent.relative_to(input_base)
                output_dir = output_dir / rel
            except ValueError:
                pass  # file_path not under input_base — write flat

        output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{_sanitize_display_name(image_info.filename)}_analysis"

        if output_format == "json":
            self._save_json(output_dir / f"{stem}.json", image_info, sort_by)
        elif output_format == "css":
            self._save_css(output_dir, image_info)
        else:
            self._save_txt(output_dir / f"{stem}.txt", image_info, sort_by)

    def _save_txt(self, output_file: Path, image_info: ImageInfo, sort_by: str) -> None:
        with output_file.open('w', encoding='utf-8') as f:
            f.write(f"Image Analysis for {_sanitize_display_name(image_info.filename)}\n")
            f.write(f"Dimensions: {image_info.dimensions[0]}x{image_info.dimensions[1]}\n")
            f.write(f"Format: {image_info.format}\n")

            if image_info.dominant_color:
                f.write(f"Dominant Color: RGB{image_info.dominant_color}\n")

            f.write(f"\nColors (sorted by {sort_by}):\n")
            for idx, color in enumerate(image_info.colors, 1):
                f.write(f"\nColor #{idx}:\n")
                f.write(f"  RGB: {color.rgb}\n")
                f.write(f"  HEX: {color.hex}\n")
                f.write(f"  CMYK: {color.cmyk}\n")
                f.write(f"  Frequency: {color.frequency}%\n")

                if color.harmonies:
                    f.write("\n  Color Harmonies:\n")
                    for harmony_type, harmony_colors in color.harmonies.items():
                        f.write(f"    {harmony_type.capitalize()}:\n")
                        for harmony_color in harmony_colors:
                            f.write(f"      RGB{harmony_color}\n")

        logger.info(f"Analysis saved to {output_file}")

    def _save_json(self, output_file: Path, image_info: ImageInfo, sort_by: str) -> None:
        data = {
            "filename": image_info.filename,
            "dimensions": {"width": image_info.dimensions[0], "height": image_info.dimensions[1]},
            "format": image_info.format,
            "sorted_by": sort_by,
            "dominant_color": list(image_info.dominant_color) if image_info.dominant_color else None,
            "colors": [
                {
                    "rgb": list(c.rgb),
                    "hex": c.hex,
                    "cmyk": list(c.cmyk),
                    "frequency": c.frequency,
                    "harmonies": {k: [list(v) for v in vs] for k, vs in c.harmonies.items()},
                }
                for c in image_info.colors
            ],
        }
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Analysis saved to {output_file}")

    def _save_css(self, output_dir: Path, image_info: ImageInfo) -> None:
        """Save palette as CSS custom properties, W3C Design Tokens, and Tailwind config.

        Three files are written to output_dir:
        - {filename}_tokens.css   — CSS custom properties
        - {filename}_tokens.json  — W3C Design Token Community Group format
        - {filename}_tailwind.js  — Tailwind CSS colors config snippet

        Args:
            output_dir: Directory to write the three token files into.
            image_info: ImageInfo object containing the analysis results.
        """
        stem = _sanitize_display_name(image_info.filename)
        colors = image_info.colors

        # ── CSS custom properties ─────────────────────────────────────────
        css_lines = [
            f"/* Color palette extracted from {stem} by Image Color Analysis Tool */",
            f"/* {len(colors)} colors, sorted by frequency */",
            ":root {",
        ]
        for idx, color in enumerate(colors, 1):
            r, g, b = color.rgb
            css_lines.append(
                f"  --color-{idx}: {color.hex};  "
                f"/* RGB({r}, {g}, {b}) · {color.frequency}% */"
            )
        if image_info.dominant_color:
            css_lines.append(f"  --color-dominant: "
                             f"{ColorConverter.rgb_to_hex(image_info.dominant_color)};")
        css_lines.append("}")
        css_file = output_dir / f"{stem}_tokens.css"
        css_file.write_text("\n".join(css_lines), encoding="utf-8")
        logger.info(f"CSS tokens saved to {css_file}")

        # ── W3C Design Token Community Group format ───────────────────────
        # Spec: https://design-tokens.github.io/community-group/format/
        token_dict: Dict[str, object] = {}
        for idx, color in enumerate(colors, 1):
            token_dict[f"color-{idx}"] = {
                "$type": "color",
                "$value": color.hex,
                "$description": (
                    f"RGB({color.rgb[0]}, {color.rgb[1]}, {color.rgb[2]}) · "
                    f"{color.frequency}% of image"
                ),
            }
        if image_info.dominant_color:
            token_dict["color-dominant"] = {
                "$type": "color",
                "$value": ColorConverter.rgb_to_hex(image_info.dominant_color),
                "$description": "Most frequent color in the image",
            }
        tokens_wrapper = {
            "$schema": "https://design-tokens.github.io/community-group/format/",
            "$metadata": {"source": stem},
            "palette": token_dict,
        }
        tokens_file = output_dir / f"{stem}_tokens.json"
        tokens_file.write_text(json.dumps(tokens_wrapper, indent=2), encoding="utf-8")
        logger.info(f"Design tokens saved to {tokens_file}")

        # ── Tailwind CSS colors config snippet ────────────────────────────
        # The key is derived from the filename and becomes a class-name
        # fragment, so replace runs of characters invalid in CSS/Tailwind
        # identifiers (spaces, dots, etc.) with hyphens
        tw_key = re.sub(r"[^A-Za-z0-9_-]+", "-", stem)
        tw_entries = [
            f"  '{idx}': '{color.hex}',  // {color.frequency}%"
            for idx, color in enumerate(colors, 1)
        ]
        if image_info.dominant_color:
            tw_entries.append(
                f"  'dominant': '{ColorConverter.rgb_to_hex(image_info.dominant_color)}',"
            )
        tw_lines = [
            f"// Tailwind CSS palette — extracted from {stem}",
            "// Paste inside the `colors` key of your tailwind.config.js",
            "module.exports = {",
            "  theme: {",
            "    extend: {",
            "      colors: {",
            f"        '{tw_key}': {{",
        ]
        tw_lines.extend(f"          {e}" for e in tw_entries)
        tw_lines += [
            "        },",
            "      },",
            "    },",
            "  },",
            "};",
        ]
        tw_file = output_dir / f"{stem}_tailwind.js"
        tw_file.write_text("\n".join(tw_lines), encoding="utf-8")
        logger.info(f"Tailwind config saved to {tw_file}")

    def batch_process(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path],
        sort_by: str = "frequency",
        max_colors: int = 0,
        output_format: str = "txt",
    ) -> None:
        """Process all supported images in a directory recursively.

        Args:
            input_dir: Directory containing images to process.
            output_dir: Root directory where analysis results will be saved.
                Subdirectory structure from input_dir is mirrored.
            sort_by: Sorting criterion for colors in each analysis.
            max_colors: Palette size for quantization (0 = no quantization).
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
