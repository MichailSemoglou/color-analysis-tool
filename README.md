# Image Color Analysis Tool

> The citable, pip-installable standard for image color analysis.

[![CI](https://github.com/MichailSemoglou/color-analysis-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/MichailSemoglou/color-analysis-tool/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/color-analysis-tool.svg)](https://badge.fury.io/py/color-analysis-tool)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/color-analysis-tool?period=total&units=INTERNATIONAL_SYSTEM&left_color=GREY&right_color=BLUE&left_text=downloads)](https://pepy.tech/projects/color-analysis-tool)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17848058.svg)](https://doi.org/10.5281/zenodo.17848058)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

Extract dominant palettes, compute perceptual color harmonies, and export design-ready tokens: in a single reproducible command, with a DOI you can cite.

**Why this repo:**

- **Complete, not fragmented**: perceptual palette extraction (k-means++ in OKLab), harmony reasoning in OKLCh (complementary, analogous, triadic, tetradic), and multi-space conversion (RGB, HEX, CMYK, OKLab, OKLCh) in one API call
- **Design-ready output**: export to CSS custom properties (HEX and OKLCH), W3C Design Tokens, and Tailwind CSS v4 `@theme`, alongside plain text and JSON
- **Research-ready**: WCAG 2.2 and APCA contrast reporting, ICC-based CMYK (FOGRA39), Zenodo DOI, ORCID attribution, deterministic output, and 324 unit tests

## Quickstart

```bash
pip install color-analysis-tool
color-analysis photo.jpg output/
```

## Statement of Need

Computational analysis of visual color is a foundational operation in digital humanities, computational aesthetics, design research, and cultural analytics, yet the tooling landscape forces practitioners into an uncomfortable choice: use JavaScript-first browser libraries (ColorThief, Vibrant.js) that resist integration with Python scientific stacks, or assemble ad hoc combinations of Pillow, NumPy, and custom scripts that are neither reproducible nor citable. Existing Python color extraction libraries provide palette extraction without the color-theory reasoning (harmonic relationships, multi-space conversions, design-token output) that designers, art historians, and accessibility researchers require as primary outputs.

The Image Color Analysis Tool addresses this gap by unifying color extraction, harmony computation, multi-space conversion, and design-token export into a single pip-installable Python library with a first-class CLI, deterministic palette extraction, and structured output formats. A researcher can characterize the complete color composition of an image corpus (dominant palette, perceptual harmonies, print-ready CMYK values, and CSS-ready design tokens) in a single reproducible command, and cite that operation with a persistent DOI.

## Features

- **Perceptual Palette Extraction**: Deterministic k-means++ clustering in OKLab with coverage weights and near-duplicate merging at CIEDE2000 2.2; the v1 exact-counting pipeline remains available via `--extractor legacy`
- **Multiple Color Spaces**: Support for RGB, HEX, CMYK, OKLab, and OKLCh color formats
- **Perceptual Color Harmony**: Complementary, analogous, triadic, and tetradic harmonies by OKLCh hue rotation with hue-preserving gamut mapping; v1 HSV harmonies via `--harmony-engine hsv_legacy`
- **Accessibility Report**: WCAG 2.2 contrast ratios (AA/AAA) against white, black, and the dominant color, plus experimental APCA Lc values, in text, JSON, and token outputs; the CSS custom-properties file carries the white and black ratios
- **Print-Ready CMYK**: ICC-based conversion through the bundled FOGRA39 profile (ISO Coated v2); custom profiles via `--cmyk-profile`; the v1 formula remains as `device_naive`
- **Color Sorting Options**: Sort colors by weight, hue, saturation, or brightness
- **Automatic Palette Sizing**: Bounded palettes out of the box: high-color images are reduced to 32 colors automatically; use `--colors N` for explicit control or `--colors 0` to disable
- **Dominant Color Detection**: Automatically identify the most prominent color
- **Batch Processing**: Analyze multiple images recursively in directories, mirroring subdirectory structure
- **Flexible Output**: Generate reports as plain text, structured JSON, or design-ready CSS tokens
- **Design Token Export**: Output CSS custom properties (HEX and OKLCH), W3C Design Tokens JSON, and Tailwind CSS v4 `@theme` with `--format css`
- **Format Support**: Works with PNG, JPG, TIFF, WebP, and PSD files
- **Progress Tracking**: Visual progress bars for processing status
- **CLI and API**: Use as a command-line tool or import as a Python library
- **Tested**: 324 unit tests covering converters, harmonies, clustering, accessibility, analysis, CLI, and all output formats

## Installation

### From PyPI (Recommended)

```bash
pip install color-analysis-tool
```

### From Source

1. Clone the repository:

```bash
git clone https://github.com/MichailSemoglou/color-analysis-tool.git
cd color-analysis-tool
```

2. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the package:

```bash
# For regular use
pip install .

# For development (editable install with dev dependencies)
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

After installation, you can use the `color-analysis` command:

```bash
# Show all available options
color-analysis --help

# Analyze a single image
color-analysis path/to/image.jpg output/directory

# Process all images in a directory
color-analysis path/to/image/directory output/directory

# Enable verbose logging
color-analysis path/to/image.jpg output/directory -v

# Sort colors by different criteria
color-analysis path/to/image.jpg output/directory -s hue
color-analysis path/to/image.jpg output/directory -s saturation
color-analysis path/to/image.jpg output/directory -s brightness

# Reduce to 32 colors (default is 'auto': an automatic bounded
# palette; -c 0 disables palette reduction entirely)
color-analysis path/to/image.jpg output/directory -c 32

# Output as JSON instead of plain text
color-analysis path/to/image.jpg output/directory -f json

# Export design tokens (CSS custom properties, W3C Design Tokens, Tailwind v4 @theme)
color-analysis path/to/image.jpg output/directory -f css

# Reproduce v1 results (exact counting, HSV harmonies)
color-analysis path/to/image.jpg output/directory --extractor legacy --harmony-engine hsv_legacy

# Combine options
color-analysis path/to/image/directory output/directory -c 64 -s hue -f json -v
color-analysis path/to/image/directory output/directory -c 32 -f css

# Show version
color-analysis --version
```

### Python API

You can also use the tool as a library in your Python projects:

```python
from color_analysis_tool import ImageAnalyzer

analyzer = ImageAnalyzer()

# Analyze a single image with custom sorting
image_info = analyzer.analyze_image('path/to/image.jpg', sort_by='hue')

# Reduce to 32 colors before analysis (recommended for photos)
image_info = analyzer.analyze_image('path/to/image.jpg', max_colors=32)

# Save as plain text (default)
analyzer.save_analysis('output/directory', image_info)

# Save as JSON
analyzer.save_analysis('output/directory', image_info, output_format='json')

# Export design tokens (writes _tokens.css, _tokens.json, _tailwind.css)
analyzer.save_analysis('output/directory', image_info, output_format='css')

# Process multiple images recursively
analyzer.batch_process('input/directory', 'output/directory', sort_by='frequency')

# Batch with palette reduction and JSON output
analyzer.batch_process('input/directory', 'output/directory', max_colors=64, output_format='json')

# Batch with design token export
analyzer.batch_process('input/directory', 'output/directory', max_colors=32, output_format='css')
```

#### Working with Analysis Results

```python
from color_analysis_tool import ImageAnalyzer, ColorConverter, ColorHarmony

analyzer = ImageAnalyzer()
image_info = analyzer.analyze_image('photo.jpg')

# Access image metadata
print(f"Image: {image_info.filename}")
print(f"Dimensions: {image_info.dimensions}")
print(f"Dominant color: {image_info.dominant_color}")

# Iterate through colors
for color in image_info.colors[:10]:  # Top 10 colors
    print(f"RGB: {color.rgb}, HEX: {color.hex}, Weight: {color.weight}%")
    print(f"  OKLCH: {color.oklch}, WCAG on white: {color.contrast.on_white.wcag_ratio}")
    print(f"  Complementary: {color.harmonies['complementary']}")

# Use utility classes directly (static methods - no instantiation needed)
cmyk = ColorConverter.rgb_to_cmyk(255, 128, 64)  # ICC, FOGRA39
oklch = ColorConverter.rgb_to_oklch((255, 128, 64))
harmonies = ColorHarmony.find_harmonies((255, 128, 64))
```

### Example Output

The tool generates a detailed analysis file for each image with the following information:

- Image metadata (dimensions, format)
- Dominant color information
- Palette weights with sorting options
- RGB, HEX, CMYK (FOGRA39), and OKLCH values for each significant color
- WCAG 2.2 contrast ratios and experimental APCA Lc values
- Color harmonies for each major color
- Design tokens (CSS, W3C, Tailwind v4) when using `--format css`

**Plain text output** (`-f txt`, default):

```
Image Analysis for example.png
Dimensions: 100x100
Format: PNG
Dominant Color: RGB(42, 157, 143)

Colors (sorted by frequency):

Color #1:
  RGB: (42, 157, 143)
  HEX: #2a9d8f
  CMYK (FOGRA39 (ISO Coated v2)): (79, 10, 49, 15)
  OKLCH: oklch(0.6304 0.1013 183.0314)
  Weight: 25.0%
  Contrast on white: 3.32:1 (AA: no, AAA: no)
  Contrast on black: 6.32:1 (AA: yes, AAA: no)
  APCA Lc (experimental): on white 60.3, on black -41.4

  Color Harmonies:
    Complementary:
      RGB(188, 110, 131)
    Analogous:
      RGB(85, 155, 108)
      RGB(42, 157, 143)
      RGB(38, 153, 174)
    Triadic:
      RGB(150, 122, 188)
      RGB(42, 157, 143)
      RGB(180, 123, 68)
    Tetradic:
      RGB(42, 157, 143)
      RGB(117, 133, 199)
      RGB(188, 110, 131)
      RGB(158, 146, 60)

Color #2:
  ...
```

**JSON output** (`-f json`; only the first of the four palette entries is shown):

```json
{
  "filename": "example.png",
  "dimensions": { "width": 100, "height": 100 },
  "format": "PNG",
  "sorted_by": "frequency",
  "cmyk_profile": "FOGRA39 (ISO Coated v2)",
  "dominant_color": [42, 157, 143],
  "colors": [
    {
      "rgb": [42, 157, 143],
      "hex": "#2a9d8f",
      "cmyk": [79, 10, 49, 15],
      "weight": 25.0,
      "oklch": [0.6304, 0.1013, 183.0314],
      "wcag": {
        "on_white": { "ratio": 3.32, "aa": false, "aaa": false },
        "on_black": { "ratio": 6.32, "aa": true, "aaa": false },
        "vs_dominant": null
      },
      "apca": { "status": "experimental", "on_white": 60.3, "on_black": -41.4 },
      "harmonies": {
        "complementary": [[188, 110, 131]],
        "analogous": [
          [85, 155, 108],
          [42, 157, 143],
          [38, 153, 174]
        ],
        "triadic": [
          [150, 122, 188],
          [42, 157, 143],
          [180, 123, 68]
        ],
        "tetradic": [
          [42, 157, 143],
          [117, 133, 199],
          [188, 110, 131],
          [158, 146, 60]
        ]
      }
    }
  ]
}
```

**CSS / Design Token output** (`-f css`): three files per image:

`example.png_tokens.css`

```css
/* Color palette extracted from example.png by Image Color Analysis Tool */
/* 4 colors, sorted by frequency */
:root {
  --color-1: #2a9d8f; /* RGB(42, 157, 143) · 25.0% */
  --color-1-oklch: oklch(0.6304 0.1013 183.0314);
  --color-1-contrast-on-white: 3.32;
  --color-1-contrast-on-black: 6.32;
  --color-2: #3a7bd5; /* RGB(58, 123, 213) · 25.0% */
  --color-2-oklch: oklch(0.5862 0.1533 257.2335);
  --color-2-contrast-on-white: 4.22;
  --color-2-contrast-on-black: 4.97;
  --color-dominant: #2a9d8f;
  --color-dominant-oklch: oklch(0.6304 0.1013 183.0314);
}
```

(The example palette has four colors; entries 3 and 4 follow the same pattern.)

`example.png_tokens.json` (W3C Design Token format, compatible with Figma Variables and Style Dictionary; only the first token is shown)

```json
{
  "$schema": "https://design-tokens.github.io/community-group/format/",
  "$metadata": { "source": "example.png" },
  "palette": {
    "color-1": {
      "$type": "color",
      "$value": "#2a9d8f",
      "$description": "RGB(42, 157, 143) · 25.0% of image",
      "$extensions": {
        "com.color-analysis-tool": {
          "oklch": "oklch(0.6304 0.1013 183.0314)",
          "wcag": {
            "on_white": { "ratio": 3.32, "aa": false, "aaa": false },
            "on_black": { "ratio": 6.32, "aa": true, "aaa": false },
            "vs_dominant": null
          },
          "apca": {
            "status": "experimental",
            "on_white": 60.3,
            "on_black": -41.4
          }
        }
      }
    }
  }
}
```

`example.png_tailwind.css` (Tailwind CSS v4 `@theme`)

```css
/* Tailwind CSS v4 palette - extracted from example.png */
/* Import after your tailwindcss import: @import "./example.png_tailwind.css"; */
@theme {
  --color-example-png-1: oklch(0.6304 0.1013 183.0314); /* 25.0% */
  --color-example-png-2: oklch(0.5862 0.1533 257.2335); /* 25.0% */
  --color-example-png-3: oklch(0.6122 0.2082 22.241); /* 25.0% */
  --color-example-png-4: oklch(1 0 0); /* 25.0% */
  --color-example-png-dominant: oklch(0.6304 0.1013 183.0314);
}
```

## Requirements

- Python 3.10 or higher
- Pillow >= 12.3.0 (with LittleCMS support for ICC conversion, bundled in the official wheels)
- tqdm >= 4.65.0

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

1. Clone your fork:

```bash
git clone https://github.com/MichailSemoglou/color-analysis-tool.git
cd color-analysis-tool
```

2. Set up development environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

3. Run tests:

```bash
pytest
```

4. Format code:

```bash
black color_analysis_tool/
isort color_analysis_tool/
```

5. Type checking:

```bash
mypy color_analysis_tool/
```

## Citation

If you use this software in your research, please cite it using the metadata in [CITATION.cff](CITATION.cff). The algorithmic sources cited throughout the codebase are listed in [REFERENCES.md](REFERENCES.md).

### BibTeX

```bibtex
@software{semoglou_color_analysis_tool,
  author       = {Semoglou, Michail},
  title        = {Color Analysis Tool},
  version      = {2.0.0},
  year         = {2026},
  url          = {https://github.com/MichailSemoglou/color-analysis-tool},
  doi          = {10.5281/zenodo.17848058}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Pillow](https://python-pillow.org/) for image processing capabilities
- [tqdm](https://github.com/tqdm/tqdm) for progress bar functionality
- The [European Color Initiative](https://www.eci.org/) for the ISO Coated v2 (ECI) ICC profile bundled under `color_analysis_tool/profiles/`

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a history of changes to this project.

Upgrading from v1? See [MIGRATION.md](MIGRATION.md) for the v2 breaking changes and how to keep the v1 behavior.
