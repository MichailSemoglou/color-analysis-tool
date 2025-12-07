"""
Color Analysis Tool
====================

A comprehensive Python tool for analyzing colors in images, providing detailed
information about color distributions, harmonies, and various color space
conversions (RGB, HEX, CMYK).

Features:
- Single image and batch processing capabilities
- Color frequency analysis with multiple sorting options
- Dominant color detection
- Color harmony calculations (complementary, analogous, triadic, tetradic)
- Multiple color space conversions
- Support for various image formats (PNG, JPG, TIFF, WebP, PSD)

Basic Usage:
    from color_analysis_tool import ImageAnalyzer

    analyzer = ImageAnalyzer()
    image_info = analyzer.analyze_image('path/to/image.jpg')
    analyzer.save_analysis('output/directory', image_info)

For more information, visit: https://github.com/MichailSemoglou/color-analysis-tool
"""

__version__ = "1.0.2"
__author__ = "Michail Semoglou"
__email__ = "michail.semoglou@example.com"
__license__ = "MIT"

from .analyzer import (
    ColorInfo,
    ImageInfo,
    ColorConverter,
    ColorHarmony,
    ImageAnalyzer,
)

__all__ = [
    "__version__",
    "ColorInfo",
    "ImageInfo",
    "ColorConverter",
    "ColorHarmony",
    "ImageAnalyzer",
]
