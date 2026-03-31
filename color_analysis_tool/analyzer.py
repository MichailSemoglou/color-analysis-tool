"""
Core analyzer module for Color Analysis Tool.

This module provides classes for analyzing colors in images, including:
- ColorConverter: Color space conversion utilities
- ColorHarmony: Color harmony calculations
- ImageAnalyzer: Main image analysis functionality
"""

import json
import logging
import colorsys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union

from PIL import Image, UnidentifiedImageError
from tqdm import tqdm

# Guard against decompression bomb attacks
Image.MAX_IMAGE_PIXELS = 178_956_970  # ~170 MP

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases
RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]
CMYK = Tuple[int, int, int, int]

VALID_SORT_OPTIONS = {"frequency", "hue", "saturation", "brightness"}
VALID_OUTPUT_FORMATS = {"txt", "json"}

# Number of top colors for which harmonies are computed
HARMONY_LIMIT = 50


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

        Args:
            hex_color: Hexadecimal color string (e.g., '#FF5733' or 'FF5733')

        Returns:
            RGB tuple of (red, green, blue) values (0-255)
        """
        hex_color = hex_color.lstrip('#')
        r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return (r, g, b)

    @staticmethod
    def rgb_to_hex(rgb: RGB) -> str:
        """Convert RGB color to hexadecimal.

        Args:
            rgb: RGB tuple of (red, green, blue) values (0-255)

        Returns:
            Hexadecimal color string (e.g., '#ff5733')
        """
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
        """
        if r == g == b == 0:
            return (0, 0, 0, 100)

        c = 1 - r / 255
        m = 1 - g / 255
        y = 1 - b / 255
        k = min(c, m, y)

        if k == 1:
            return (0, 0, 0, 100)

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
        """
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
                tuple(int(x * 255) for x in colorsys.hsv_to_rgb(hh / 360, ss, vv))  # type: ignore[misc]
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

        Returns:
            ImageInfo object containing analysis results, or None if analysis fails

        Raises:
            ValueError: If sort_by is not a recognised sort option.
        """
        if sort_by not in VALID_SORT_OPTIONS:
            raise ValueError(
                f"sort_by must be one of {VALID_SORT_OPTIONS}, got {sort_by!r}"
            )

        file_path = Path(file_path)
        try:
            with Image.open(file_path) as img:
                original_format = img.format or "UNKNOWN"
                dimensions = img.size

                if max_colors > 0:
                    # Quantize to a reduced palette for performance and clarity
                    quantized = img.convert("RGB").quantize(colors=max_colors, method=Image.Quantize.MEDIANCUT)
                    image = quantized.convert("RGBA")
                else:
                    image = img.convert("RGBA")

        except (OSError, UnidentifiedImageError, ValueError) as exc:
            logger.error(f"Error opening {file_path}: {exc}")
            return None

        total_pixels = image.width * image.height
        # Use get_flattened_data (Pillow >= 10) with fallback for older versions
        try:
            color_counts = Counter(image.get_flattened_data())
        except AttributeError:
            color_counts = Counter(image.getdata())

        # Filter transparent pixels and sort by frequency descending
        visible_colors = [
            (color, count)
            for color, count in color_counts.most_common()
            if color[3] > 0
        ]

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
            # Dominant color is always the most frequent, regardless of sort order
            most_frequent = color_counts.most_common(1)[0][0]
            dominant_color = (most_frequent[0], most_frequent[1], most_frequent[2])

        colors: List[ColorInfo] = []
        for idx, (color, count) in enumerate(tqdm(visible_colors, desc="Analyzing colors")):
            r, g, b, _ = color
            rgb: RGB = (r, g, b)
            harmonies = (
                ColorHarmony.find_harmonies(rgb) if idx < HARMONY_LIMIT else {}
            )
            colors.append(ColorInfo(
                rgb=rgb,
                hex=ColorConverter.rgb_to_hex(rgb),
                cmyk=ColorConverter.rgb_to_cmyk(r, g, b),
                frequency=round((count / total_pixels) * 100, 2),
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
            output_format: Output format — 'txt' (default) or 'json'.
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
        stem = f"{image_info.filename}_analysis"

        if output_format == "json":
            self._save_json(output_dir / f"{stem}.json", image_info, sort_by)
        else:
            self._save_txt(output_dir / f"{stem}.txt", image_info, sort_by)

    def _save_txt(self, output_file: Path, image_info: ImageInfo, sort_by: str) -> None:
        with output_file.open('w', encoding='utf-8') as f:
            f.write(f"Image Analysis for {image_info.filename}\n")
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
            output_format: 'txt' or 'json'.
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        # rglob returns a generator — no list() needed; tqdm wraps it fine
        for file_path in tqdm(input_dir.rglob('*'), desc="Processing files"):
            if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                logger.info(f"Processing {file_path}...")
                image_info = self.analyze_image(file_path, sort_by=sort_by, max_colors=max_colors)
                if image_info:
                    self.save_analysis(
                        output_dir,
                        image_info,
                        sort_by=sort_by,
                        output_format=output_format,
                        input_base=input_dir,
                        file_path=file_path,
                    )
