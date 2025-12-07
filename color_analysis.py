#!/usr/bin/env python3
"""
Enhanced Color Analysis Tool
============================

A comprehensive tool for analyzing colors in images, providing detailed information about
color distributions, harmonies, and various color space conversions (RGB, HEX, CMYK).

Features:
- Single image and batch processing capabilities
- Color frequency analysis with multiple sorting options
- Dominant color detection
- Color harmony calculations (complementary, analogous, triadic, tetradic)
- Multiple color space conversions
- Support for various image formats (PNG, JPG, TIFF, WebP, PSD)
- Recursive directory scanning for batch processing

Requirements:
- Python 3.7+
- Pillow
- tqdm
- colormath

Usage:
    python color_analysis.py [-h] [-v] [-s {frequency,hue,saturation,brightness}] input output

    input: Path to an image file or directory containing images
    output: Directory where analysis results will be saved
    -s, --sort: Sorting method for colors (default: frequency)
    -v, --verbose: Enable verbose logging
"""

import sys
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
import logging
from pathlib import Path
import argparse

from PIL import Image
from collections import Counter
import colorsys
from tqdm import tqdm

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
    dominant_color: Optional[RGB] = None

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

    def analyze_image(self, file_path: Union[str, Path], sort_by: str = "frequency") -> Optional[ImageInfo]:
        """
        Analyze colors in an image file.
        
        Args:
            file_path: Path to the image file
            sort_by: Sorting criterion for colors (frequency, hue, saturation, brightness)
            
        Returns:
            ImageInfo object containing analysis results or None if analysis fails
        """
        try:
            file_path = Path(file_path)
            # Open image first to get original format
            with Image.open(file_path) as img:
                original_format = img.format
                # Convert to RGBA for processing
                image = img.convert('RGBA')
            
            pixels = list(image.getdata())
            total_pixels = len(pixels)

            color_counts = Counter(pixels)
            sorted_colors = color_counts.most_common()

            # Filter out transparent colors first
            visible_colors = [(color, count) for color, count in sorted_colors if color[3] > 0]
            
            # Apply sorting based on criterion
            if sort_by != "frequency":
                if sort_by == "hue":
                    visible_colors.sort(
                        key=lambda item: colorsys.rgb_to_hsv(item[0][0]/255, item[0][1]/255, item[0][2]/255)[0]
                    )
                elif sort_by == "saturation":
                    visible_colors.sort(
                        key=lambda item: colorsys.rgb_to_hsv(item[0][0]/255, item[0][1]/255, item[0][2]/255)[1],
                        reverse=True
                    )
                elif sort_by == "brightness":
                    visible_colors.sort(
                        key=lambda item: colorsys.rgb_to_hsv(item[0][0]/255, item[0][1]/255, item[0][2]/255)[2],
                        reverse=True
                    )
            sorted_colors = visible_colors

            image_info = ImageInfo(
                filename=file_path.name,
                dimensions=image.size,
                format=original_format,
                colors=[],
                dominant_color=None
            )

            # Set dominant color (most frequent non-transparent color)
            if sorted_colors:
                image_info.dominant_color = sorted_colors[0][0][:3]

            for color, count in tqdm(sorted_colors, desc="Analyzing colors"):
                r, g, b, a = color
                if a == 0:  # Skip fully transparent colors
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

    def save_analysis(self, output_dir: Union[str, Path], image_info: ImageInfo, sort_by: str = "frequency") -> None:
        """Save analysis results to a file."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{image_info.filename}_analysis.txt"
        
        with output_file.open('w') as f:
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
                
                f.write("\n  Color Harmonies:\n")
                for harmony_type, harmony_colors in color.harmonies.items():
                    f.write(f"    {harmony_type.capitalize()}:\n")
                    for harmony_color in harmony_colors:
                        f.write(f"      RGB{harmony_color}\n")

        logger.info(f"Analysis saved to {output_file}")

    def batch_process(self, input_dir: Union[str, Path], output_dir: Union[str, Path], sort_by: str = "frequency") -> None:
        """Process all supported images in a directory recursively."""
        input_dir = Path(input_dir)
        
        for file_path in tqdm(list(input_dir.rglob('*')), desc="Processing files"):
            if file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                logger.info(f"Processing {file_path}...")
                image_info = self.analyze_image(file_path, sort_by=sort_by)
                if image_info:
                    self.save_analysis(output_dir, image_info, sort_by=sort_by)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Enhanced Image Color Analysis Tool",
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
        "-s", "--sort",
        choices=["frequency", "hue", "saturation", "brightness"],
        default="frequency",
        help="Sort colors by specified criterion"
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

    try:
        if args.input.is_file():
            logger.info(f"Analyzing single file: {args.input}")
            image_info = analyzer.analyze_image(args.input, sort_by=args.sort)
            if image_info:
                analyzer.save_analysis(args.output, image_info, sort_by=args.sort)
        elif args.input.is_dir():
            logger.info(f"Batch processing directory: {args.input}")
            analyzer.batch_process(args.input, args.output, sort_by=args.sort)
        else:
            logger.error("Invalid input path")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
