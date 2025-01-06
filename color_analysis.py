#!/usr/bin/env python3
"""
Color Analysis Tool
===================

A comprehensive tool for analyzing colors in images, providing detailed information about
color distributions, harmonies, and various color space conversions (RGB, HEX, CMYK).

Features:
- Single image and batch processing capabilities
- Color frequency analysis
- Color harmony calculations (complementary, analogous, triadic, tetradic)
- Multiple color space conversions
- Support for various image formats (PNG, JPG, TIFF, WebP, PSD)

Requirements:
- Python 3.7+
- Pillow
- tqdm
- colormath

Usage:
    python color_analysis.py <input_path> <output_path>

    input_path: Path to an image file or directory containing images
    output_path: Directory where analysis results will be saved
"""

import os
import sys
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import logging
from pathlib import Path

from PIL import Image
from collections import Counter
import colorsys
from tqdm import tqdm
from colormath.color_objects import sRGBColor, CMYKColor
from colormath.color_conversions import convert_color

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type aliases
RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]
HSV = Tuple[float, float, float]
CMYK = Tuple[int, int, int, int]

@dataclass
class ColorInfo:
    """Data class to store information about a single color."""
    rgb: RGB
    hex: str
    cmyk: CMYK
    frequency: float
    harmonies: Dict[str, List[RGB]]

@dataclass
class ImageInfo:
    """Data class to store analysis results for an image."""
    filename: str
    dimensions: Tuple[int, int]
    format: str
    colors: List[ColorInfo]

class ColorConverter:
    """Utility class for color space conversions."""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> RGB:
        """Convert hexadecimal color to RGB."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def rgb_to_hex(rgb: RGB) -> str:
        """Convert RGB color to hexadecimal."""
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    @staticmethod
    def rgb_to_cmyk(r: int, g: int, b: int) -> CMYK:
        """Convert RGB color to CMYK."""
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
            round(k * 100)
        )

class ColorHarmony:
    """Class for calculating color harmonies."""
    
    @staticmethod
    def find_harmonies(base_color: RGB) -> Dict[str, List[RGB]]:
        """Calculate color harmonies for a given base color."""
        harmonies = {}
        r, g, b = base_color
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        h = h * 360

        # Complementary
        complementary_hue = (h + 180) % 360
        harmonies['complementary'] = [(complementary_hue, s, v)]

        # Analogous
        harmonies['analogous'] = [
            ((h - 30) % 360, s, v),
            (h, s, v),
            ((h + 30) % 360, s, v)
        ]

        # Triadic
        harmonies['triadic'] = [
            ((h + 120) % 360, s, v),
            (h, s, v),
            ((h + 240) % 360, s, v)
        ]

        # Tetradic
        harmonies['tetradic'] = [
            (h, s, v),
            ((h + 90) % 360, s, v),
            ((h + 180) % 360, s, v),
            ((h + 270) % 360, s, v)
        ]

        # Convert all HSV values back to RGB
        return {
            key: [
                tuple(int(x * 255) for x in colorsys.hsv_to_rgb(h / 360, s, v))
                for h, s, v in colors
            ]
            for key, colors in harmonies.items()
        }

class ImageAnalyzer:
    """Main class for image analysis functionality."""
    
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.tiff', '.webp', '.psd'}
    
    def __init__(self):
        self.converter = ColorConverter()
        self.harmony = ColorHarmony()

    def analyze_image(self, file_path: Union[str, Path]) -> Optional[ImageInfo]:
        """
        Analyze colors in an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            ImageInfo object containing analysis results or None if analysis fails
        """
        try:
            file_path = Path(file_path)
            image = Image.open(file_path).convert('RGBA')
            pixels = list(image.getdata())
            total_pixels = len(pixels)

            color_counts = Counter(pixels)
            sorted_colors = color_counts.most_common()

            image_info = ImageInfo(
                filename=file_path.name,
                dimensions=image.size,
                format=image.format,
                colors=[]
            )

            for color, count in tqdm(sorted_colors, desc="Analyzing colors"):
                r, g, b, a = color
                if a == 0:
                    continue

                rgb = (r, g, b)
                color_info = ColorInfo(
                    rgb=rgb,
                    hex=self.converter.rgb_to_hex(rgb),
                    cmyk=self.converter.rgb_to_cmyk(r, g, b),
                    frequency=round((count / total_pixels) * 100, 2),
                    harmonies=self.harmony.find_harmonies(rgb)
                )
                image_info.colors.append(color_info)

            return image_info

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None

    def save_analysis(self, output_dir: Union[str, Path], image_info: ImageInfo) -> None:
        """Save analysis results to a file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{image_info.filename}_analysis.txt"
        
        with output_file.open('w') as f:
            f.write(f"Image Analysis for {image_info.filename}\n")
            f.write(f"Dimensions: {image_info.dimensions[0]}x{image_info.dimensions[1]}\n")
            f.write(f"Format: {image_info.format}\n")
            f.write("\nColors (sorted by frequency):\n")

            for color in image_info.colors:
                f.write(
                    f"  RGB: {color.rgb}, "
                    f"HEX: {color.hex}, "
                    f"CMYK: {color.cmyk}, "
                    f"Frequency: {color.frequency}%\n"
                )
                f.write("    Harmonies:\n")
                for harmony_type, harmony_colors in color.harmonies.items():
                    f.write(f"      {harmony_type.capitalize()}: {harmony_colors}\n")

        logger.info(f"Analysis saved to {output_file}")

    def batch_process(self, input_dir: Union[str, Path], output_dir: Union[str, Path]) -> None:
        """Process all supported images in a directory."""
        input_dir = Path(input_dir)
        
        for file_path in input_dir.rglob('*'):
            if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                logger.info(f"Processing {file_path}...")
                image_info = self.analyze_image(file_path)
                if image_info:
                    self.save_analysis(output_dir, image_info)

def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Image Color Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "input",
        help="Path to input file or directory",
        type=Path
    )
    parser.add_argument(
        "output",
        help="Path to output directory",
        type=Path
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Enable verbose logging",
        action="store_true"
    )
    
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    analyzer = ImageAnalyzer()

    if args.input.is_file():
        logger.info(f"Analyzing single file: {args.input}")
        image_info = analyzer.analyze_image(args.input)
        if image_info:
            analyzer.save_analysis(args.output, image_info)
    elif args.input.is_dir():
        logger.info(f"Batch processing directory: {args.input}")
        analyzer.batch_process(args.input, args.output)
    else:
        logger.error("Invalid input path")
        sys.exit(1)

if __name__ == "__main__":
    main()