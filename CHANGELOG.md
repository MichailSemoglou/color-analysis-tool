# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0]

### Added

- Color quantization support via `--colors N` CLI flag and `max_colors` parameter in `analyze_image` and `batch_process`; reduces images to a meaningful palette using median-cut before analysis
- JSON output format via `--format json` CLI flag and `output_format` parameter in `save_analysis` and `batch_process`
- 50 unit tests covering `ColorConverter`, `ColorHarmony`, `ImageAnalyzer`, `save_analysis`, and `batch_process`
- GitHub Actions CI workflow running tests and linting across Python 3.9–3.13

### Changed

- `batch_process` now mirrors the input subdirectory structure in the output directory (previously all outputs landed flat)
- Color harmonies are now computed only for the top 50 colors per image instead of every unique pixel color, significantly reducing processing time on large images
- `sort_by` parameter now raises `ValueError` immediately for unrecognised values instead of silently falling back to frequency sorting
- `save_analysis` raises `ValueError` for unrecognised `output_format` values
- Minimum supported Python version raised to 3.9

### Fixed

- `hex_to_rgb` now returns a correctly typed `Tuple[int, int, int]` instead of a variable-length generator tuple
- Image open errors now catch specific exceptions (`OSError`, `UnidentifiedImageError`) instead of a bare `except Exception`, preventing silent swallowing of unrelated errors
- Added `Image.MAX_IMAGE_PIXELS` guard to protect against decompression bomb attacks
- Pixel data read via `get_flattened_data()` (Pillow ≥ 10) with fallback to `getdata()`, resolving a deprecation warning

### Removed

- `color_analysis.py` legacy standalone script (superseded by the `color_analysis_tool` package)
- Placeholder `__email__` field from `__init__.py`

## [1.0.2]

### Added

- DOI badge and citation information in README (10.5281/zenodo.17848059)

## [1.0.1]

### Changed

- Removed unused `colormath` dependency (CMYK conversion uses built-in algorithm)
- Removed unused `os` import from the legacy standalone script
- Lighter package with fewer dependencies (only Pillow and tqdm required)

## [1.0.0]

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
- Support for multiple image formats: PNG, JPG/JPEG, TIFF, WebP, and PSD
- Command-line interface (`color-analysis` command)
- Python API for library usage
- Progress bars for batch processing
- Detailed text reports with full color information
- MIT License
- CITATION.cff for academic citations
- Zenodo integration for DOI minting

### Changed

- Built with Python 3.7+ compatibility
- PEP 621 compliant packaging with `pyproject.toml`
- Type hints throughout the codebase

[Unreleased]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/MichailSemoglou/color-analysis-tool/releases/tag/v1.0.0
