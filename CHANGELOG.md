# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.2] - 2025-01-07

### Added
- DOI badge and citation information in README (10.5281/zenodo.17848059)

## [1.0.1] - 2025-01-07

### Changed
- Removed unused `colormath` dependency (CMYK conversion uses built-in algorithm)
- Removed unused `os` import from color_analysis.py
- Lighter package with fewer dependencies (only Pillow and tqdm required)

## [1.0.0] - 2025-01-06

### Added
- Initial stable release
- Comprehensive color analysis for images
- Multiple color space support (RGB, HEX, CMYK)
- Color harmony calculations:
  - Complementary colors (180° hue offset)
  - Analogous colors (±30° hue offset)
  - Triadic colors (120° hue spacing)
  - Tetradic colors (90° hue spacing)
- Multiple sorting options for colors:
  - By frequency (default)
  - By hue
  - By saturation
  - By brightness
- Dominant color detection
- Batch processing with recursive directory scanning
- Support for multiple image formats:
  - PNG
  - JPG/JPEG
  - TIFF
  - WebP
  - PSD
- Command-line interface (`color-analysis` command)
- Python API for library usage
- Progress bars for batch processing
- Detailed text reports with full color information
- MIT License
- CITATION.cff for academic citations
- Zenodo integration for DOI minting

### Technical Details
- Built with Python 3.7+ compatibility
- Uses Pillow for image processing
- Uses tqdm for progress visualization
- PEP 621 compliant packaging with pyproject.toml
- Type hints throughout the codebase

[Unreleased]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/MichailSemoglou/color-analysis-tool/releases/tag/v1.0.0
