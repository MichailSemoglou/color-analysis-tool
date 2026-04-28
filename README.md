# Image Color Analysis Tool

> The citable, pip-installable standard for image color analysis.

[![CI](https://github.com/MichailSemoglou/color-analysis-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/MichailSemoglou/color-analysis-tool/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/color-analysis-tool.svg)](https://badge.fury.io/py/color-analysis-tool)
[![PyPI Downloads](https://img.shields.io/pypi/dm/color-analysis-tool.svg)](https://pypistats.org/packages/color-analysis-tool)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19851366.svg)](https://doi.org/10.5281/zenodo.19851366)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Extract dominant palettes, compute color harmonies, and export design-ready tokens — in a single reproducible command, with a DOI you can cite.

**Why this repo:**

- **Complete, not fragmented** — color extraction, harmony reasoning (complementary, analogous, triadic, tetradic), and multi-space conversion (RGB, HEX, CMYK) in one API call
- **Design-ready output** — export directly to CSS custom properties, W3C Design Tokens, and Tailwind config alongside plain text and JSON
- **Research-ready** — Zenodo DOI, ORCID attribution, deterministic output, and 60 unit tests

## Quickstart

```bash
pip install color-analysis-tool
color-analysis photo.jpg output/
```

## Statement of Need

Computational analysis of visual color is a foundational operation in digital humanities, computational aesthetics, design research, and cultural analytics, yet the tooling landscape forces practitioners into an uncomfortable choice: use JavaScript-first browser libraries (ColorThief, Vibrant.js) that resist integration with Python scientific stacks, or assemble ad hoc combinations of Pillow, NumPy, and custom scripts that are neither reproducible nor citable. Existing Python color extraction libraries provide palette extraction without the color-theory reasoning — harmonic relationships, multi-space conversions, design-token output — that designers, art historians, and accessibility researchers require as primary outputs.

The Image Color Analysis Tool addresses this gap by unifying color extraction, harmony computation, multi-space conversion, and design-token export into a single pip-installable Python library with a first-class CLI, deterministic quantization, and structured output formats. A researcher can characterize the complete color composition of an image corpus — dominant palette, perceptual harmonies, print-ready CMYK values, and CSS-ready design tokens — in a single reproducible command, and cite that operation with a persistent DOI.

## Features

- **Comprehensive Color Analysis**: Extract and analyze colors from images
- **Multiple Color Spaces**: Support for RGB, HEX, and CMYK color formats
- **Color Harmony**: Calculate complementary, analogous, triadic, and tetradic color harmonies
- **Color Sorting Options**: Sort colors by frequency, hue, saturation, or brightness
- **Color Quantization**: Reduce images to a meaningful palette (e.g. 32 dominant colors) for faster, cleaner analysis
- **Dominant Color Detection**: Automatically identify the most prominent color
- **Batch Processing**: Analyze multiple images recursively in directories, mirroring subdirectory structure
- **Flexible Output**: Generate reports as plain text, structured JSON, or design-ready CSS tokens
- **Design Token Export**: Output CSS custom properties, W3C Design Tokens JSON, and Tailwind config snippets with `--format css`
- **Format Support**: Works with PNG, JPG, TIFF, WebP, and PSD files
- **Progress Tracking**: Visual progress bars for processing status
- **CLI and API**: Use as a command-line tool or import as a Python library
- **Tested**: 60 unit tests covering converters, harmonies, analysis, and all output formats

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

# Quantize to 32 dominant colors (faster and cleaner for photos)
color-analysis path/to/image.jpg output/directory -c 32

# Output as JSON instead of plain text
color-analysis path/to/image.jpg output/directory -f json

# Export design tokens (CSS custom properties, W3C Design Tokens, Tailwind config)
color-analysis path/to/image.jpg output/directory -f css

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

# Quantize to 32 colors before analysis (recommended for photos)
image_info = analyzer.analyze_image('path/to/image.jpg', max_colors=32)

# Save as plain text (default)
analyzer.save_analysis('output/directory', image_info)

# Save as JSON
analyzer.save_analysis('output/directory', image_info, output_format='json')

# Export design tokens (writes _tokens.css, _tokens.json, _tailwind.js)
analyzer.save_analysis('output/directory', image_info, output_format='css')

# Process multiple images recursively
analyzer.batch_process('input/directory', 'output/directory', sort_by='frequency')

# Batch with quantization and JSON output
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
    print(f"RGB: {color.rgb}, HEX: {color.hex}, Frequency: {color.frequency}%")
    print(f"  Complementary: {color.harmonies['complementary']}")

# Use utility classes directly (static methods — no instantiation needed)
cmyk = ColorConverter.rgb_to_cmyk(255, 128, 64)
harmonies = ColorHarmony.find_harmonies((255, 128, 64))
```

### Example Output

The tool generates a detailed analysis file for each image with the following information:

- Image metadata (dimensions, format)
- Dominant color information
- Color frequency analysis with sorting options
- RGB, HEX, and CMYK values for each significant color
- Color harmonies for each major color
- Design tokens (CSS, W3C, Tailwind) when using `--format css`

**Plain text output** (`-f txt`, default):

```
Image Analysis for example.jpg
Dimensions: 1920x1080
Format: JPEG
Dominant Color: RGB(255, 255, 255)

Colors (sorted by frequency):

Color #1:
  RGB: (255, 255, 255)
  HEX: #ffffff
  CMYK: (0, 0, 0, 0)
  Frequency: 35.2%

  Color Harmonies:
    Complementary:
      RGB(0, 0, 0)
    Analogous:
      RGB(255, 245, 245)
      RGB(255, 255, 255)
      RGB(245, 255, 255)
    Triadic:
      RGB(255, 255, 0)
      RGB(255, 255, 255)
      RGB(0, 255, 255)
    Tetradic:
      RGB(255, 255, 255)
      RGB(255, 0, 255)
      RGB(0, 0, 0)
      RGB(0, 255, 0)
```

**JSON output** (`-f json`):

```json
{
  "filename": "example.jpg",
  "dimensions": { "width": 1920, "height": 1080 },
  "format": "JPEG",
  "sorted_by": "frequency",
  "dominant_color": [255, 255, 255],
  "colors": [
    {
      "rgb": [255, 255, 255],
      "hex": "#ffffff",
      "cmyk": [0, 0, 0, 0],
      "frequency": 35.2,
      "harmonies": {
        "complementary": [[0, 0, 0]],
        "analogous": [
          [255, 245, 245],
          [255, 255, 255],
          [245, 255, 255]
        ],
        "triadic": [
          [255, 255, 0],
          [255, 255, 255],
          [0, 255, 255]
        ],
        "tetradic": [
          [255, 255, 255],
          [255, 0, 255],
          [0, 0, 0],
          [0, 255, 0]
        ]
      }
    }
  ]
}
```

**CSS / Design Token output** (`-f css`) — three files per image:

`example.jpg_tokens.css`

```css
/* Color palette extracted from example.jpg by Image Color Analysis Tool */
:root {
  --color-1: #ffffff; /* RGB(255, 255, 255) · 35.2% */
  --color-2: #3a7bd5; /* RGB(58, 123, 213) · 18.4% */
  --color-dominant: #ffffff;
}
```

`example.jpg_tokens.json` (W3C Design Token format, compatible with Figma Variables and Style Dictionary)

```json
{
  "$schema": "https://design-tokens.github.io/community-group/format/",
  "palette": {
    "color-1": {
      "$type": "color",
      "$value": "#ffffff",
      "$description": "RGB(255, 255, 255) · 35.2% of image"
    },
    "color-2": {
      "$type": "color",
      "$value": "#3a7bd5",
      "$description": "RGB(58, 123, 213) · 18.4% of image"
    },
    "color-dominant": {
      "$type": "color",
      "$value": "#ffffff",
      "$description": "Most frequent color in the image"
    }
  }
}
```

`example.jpg_tailwind.js`

```js
// Tailwind CSS palette — extracted from example.jpg
// Paste inside the `colors` key of your tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        "example-jpg": {
          1: "#ffffff", // 35.2%
          2: "#3a7bd5", // 18.4%
          dominant: "#ffffff",
        },
      },
    },
  },
};
```

## Requirements

- Python 3.9 or higher
- Pillow >= 9.0.0
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

If you use this software in your research, please cite it using the metadata in [CITATION.cff](CITATION.cff):

### BibTeX

```bibtex
@software{semoglou_color_analysis_tool,
  author       = {Semoglou, Michail},
  title        = {Color Analysis Tool},
  version      = {1.2.0},
  year         = {2026},
  url          = {https://github.com/MichailSemoglou/color-analysis-tool},
  doi          = {10.5281/zenodo.19851366}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Pillow](https://python-pillow.org/) for image processing capabilities
- [tqdm](https://github.com/tqdm/tqdm) for progress bar functionality

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a history of changes to this project.
