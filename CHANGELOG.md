# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-08-23

### Added

- `--colors auto` is now the default palette mode: images with at most 256 unique visible colors are analyzed faithfully; above that threshold the palette is quantized to a bounded 32 colors and the decision is logged. Explicit `-c N` (1-256) and `-c 0` (no quantization) are unchanged
- Exporters now cap output at 1000 colors per report with a visible truncation note, guarding against unbounded output from `max_colors=0` runs on high-color images
- CONTRIBUTING.md with development setup and pull request guidelines

## [1.3.0] - 2026-08-22

### Fixed

- Dominant color is now selected from visible pixels only; fully transparent pixels can no longer become the dominant color
- Color frequencies are now calculated against the visible-pixel count instead of the total pixel count, so palettes from images with transparency sum to 100%; a fully transparent image now returns an empty palette with no dominant color instead of reporting misleading frequencies
- Harmony colors are now rounded rather than truncated when converted back to RGB, removing a systematic -1 channel bias
- `hex_to_rgb` now validates its input with a clear `ValueError` for malformed strings and supports three-digit CSS shorthand such as `#fff`
- Removed the unreachable `k == 1` branch in `rgb_to_cmyk` (black is already special-cased)
- Tailwind config keys derived from filenames are now sanitized: spaces and other characters invalid in CSS/Tailwind identifiers are replaced with hyphens
- Quantized analysis (`--colors N`) now preserves the alpha channel: transparent pixels are no longer converted to opaque black before counting
- Fully transparent pixels no longer influence palette boundaries during quantization; their RGB payload is flattened to a single color before median cut runs
- Corrected the 1.1.0 changelog entry below: `get_flattened_data()` was added in Pillow 12.1.0, not Pillow 10
- `analyze_image` now catches `Image.DecompressionBombError` (not an `OSError` subclass): an image exceeding the pixel limit returns None and is skipped in batch processing instead of raising
- Removed the redundant `UnidentifiedImageError` catch (it is an `OSError` subclass)
- `rgb_to_hex`, `rgb_to_cmyk`, and `find_harmonies` now raise `ValueError` for channel values outside 0-255, matching the `hex_to_rgb` validation
- `max_colors` is validated up front: `analyze_image` raises `ValueError` and the CLI exits with a clear message for values outside 0-256, instead of failing inside quantization
- `batch_process` now processes files in sorted order and skips a file whose report cannot be saved instead of aborting the whole batch
- The wheel now ships the `py.typed` marker promised by the `Typing :: Typed` classifier
- Output filenames derived from source images are now collision-resistant: when sanitization alters a name, a stable digest suffix keeps distinct files from overwriting each other, and backslashes are replaced for cross-platform safety
- Filenames are sanitized before being embedded in generated reports and CSS/JS comments, so a crafted filename cannot inject content into output files
- Pixels sharing an RGB value but differing in alpha now aggregate into one palette entry instead of appearing as duplicate colors with split frequencies

### Changed

- Minimum Pillow version raised to 12.3.0, excluding versions affected by the PSD-loader out-of-bounds write (CVE-2026-25990) and later memory-safety advisories; `pip-audit` in CI guards against newer advisories
- Documented why the decompression-bomb limit retains the Pillow default of ~179 MP rather than tightening it
- CI now fails when test coverage drops below 90%
- GitHub Actions are pinned to commit SHAs, CI jobs run with least-privilege permissions and no persisted checkout credentials, and every push and pull request runs `pip-audit`
- The package version is now single-sourced in `pyproject.toml` and read at runtime via `importlib.metadata`
- `mypy` now runs clean on the package, and imports across the package and tests are isort-ordered

### Removed

- Python 3.9 support (end of life since October 2025); the minimum is now Python 3.10
- The deprecated `getdata()` fallback; Pillow >= 12.3.0 always provides `get_flattened_data()`

### Added

- SECURITY.md with a private vulnerability reporting channel
- Alpha-channel regression tests covering mixed transparent/opaque and fully transparent images
- CLI test suite (`tests/test_cli.py`) covering argument validation, output formats, batch mode, and exit codes
- Edge-case tests for hue/saturation/brightness sort orders, grayscale/palette/LA image modes, corrupt input files, oversized-image rejection, and the decompression-bomb guard

## [1.2.0] - 2026-04-28

### Added

- CSS / Design Token Export via `--format css` (CLI) and `output_format='css'` (API): three files are written per image
  - `{filename}_tokens.css` — CSS custom properties (`--color-1: #3a7bd5;`) with dominant-color property
  - `{filename}_tokens.json` — W3C Design Token Community Group format (`$type: "color"`) compatible with Style Dictionary and Figma Variables import
  - `{filename}_tailwind.js` — Tailwind CSS `colors` config snippet ready to paste into `tailwind.config.js`
- 11 new unit tests covering CSS, Design Token, and Tailwind output (including batch processing)

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
- Pixel data read via `get_flattened_data()` (Pillow ≥ 12.1) with fallback to `getdata()`, resolving a deprecation warning

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

[1.4.0]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/MichailSemoglou/color-analysis-tool/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/MichailSemoglou/color-analysis-tool/releases/tag/v1.0.0
