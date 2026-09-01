"""Color Analysis Tool.

A Python tool for analyzing colors in images, providing detailed
information about color distributions, perceptual harmonies, and color
space conversions (RGB, HEX, CMYK, OKLab, OKLCh).

Features:
- Perceptual palette extraction: deterministic k-means++ in OKLab
- Single image and batch processing capabilities
- Dominant color detection
- Color harmony calculations in OKLCh (complementary, analogous,
  triadic, tetradic)
- WCAG 2.2 contrast ratios and experimental APCA Lc values
- ICC-based CMYK conversion (FOGRA39)
- Design token export (CSS custom properties, W3C Design Tokens,
  Tailwind CSS v4)
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
