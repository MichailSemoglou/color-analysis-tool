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

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    # Single source of truth: the [project] version in pyproject.toml
    __version__ = _version("color-analysis-tool")
except PackageNotFoundError:  # pragma: no cover - bare source checkout
    __version__ = "unknown"

__author__ = "Michail Semoglou"
__license__ = "MIT"

from .analyzer import (
    ColorConverter,
    ColorHarmony,
    ColorInfo,
    ImageAnalyzer,
    ImageInfo,
)

__all__ = [
    "__version__",
    "ColorInfo",
    "ImageInfo",
    "ColorConverter",
    "ColorHarmony",
    "ImageAnalyzer",
]
