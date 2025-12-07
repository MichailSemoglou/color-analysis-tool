# Image Color Analysis Tool

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17848059.svg)](https://doi.org/10.5281/zenodo.17848059)
[![PyPI version](https://badge.fury.io/py/color-analysis-tool.svg)](https://badge.fury.io/py/color-analysis-tool)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

A powerful Python tool for analyzing colors in images, providing detailed information about color distributions, harmonies, and various color space conversions. Perfect for designers, artists, and developers working with color analysis and manipulation.

## Features

- **Comprehensive Color Analysis**: Extract and analyze colors from images
- **Multiple Color Spaces**: Support for RGB, HEX, and CMYK color formats
- **Color Harmony**: Calculate complementary, analogous, triadic, and tetradic color harmonies
- **Color Sorting Options**: Sort colors by frequency, hue, saturation, or brightness
- **Dominant Color Detection**: Automatically identify the most prominent color
- **Batch Processing**: Analyze multiple images recursively in directories
- **Detailed Reports**: Generate comprehensive analysis reports for each image
- **Format Support**: Works with PNG, JPG, TIFF, WebP, and PSD files
- **Progress Tracking**: Visual progress bars for processing status
- **CLI and API**: Use as a command-line tool or import as a Python library

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

# Save the analysis
analyzer.save_analysis('output/directory', image_info)

# Process multiple images recursively
analyzer.batch_process('input/directory', 'output/directory', sort_by='frequency')
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

# Use utility classes directly
converter = ColorConverter()
cmyk = converter.rgb_to_cmyk(255, 128, 64)

harmony = ColorHarmony()
harmonies = harmony.find_harmonies((255, 128, 64))
```

### Example Output

The tool generates a detailed analysis file for each image with the following information:
- Image metadata (dimensions, format)
- Dominant color information
- Color frequency analysis with sorting options
- RGB, HEX, and CMYK values for each significant color
- Color harmonies for each major color

Example output structure:
```
Image Analysis for example.jpg
Dimensions: 1920x1080
Format: JPEG
Dominant Color: RGB(255, 255, 255)

Colors (sorted by frequency):
  RGB: (255, 255, 255), HEX: #FFFFFF, CMYK: (0, 0, 0, 0), Frequency: 35.2%
    Harmonies:
      Complementary: [(0, 0, 0)]
      Analogous: [(255, 245, 245), (255, 255, 255), (245, 255, 255)]
      Triadic: [(255, 255, 0), (255, 255, 255), (0, 255, 255)]
```

## Requirements

- Python 3.7 or higher
- Pillow >= 9.0.0
- tqdm >= 4.65.0

## Citation

If you use this software in your research, please cite it using the metadata in [CITATION.cff](CITATION.cff):

```bibtex
@software{semoglou_color_analysis_tool,
  author       = {Semoglou, Michail},
  title        = {Color Analysis Tool},
  version      = {1.0.2},
  year         = {2025},
  url          = {https://github.com/MichailSemoglou/color-analysis-tool},
  doi          = {10.5281/zenodo.17848059}
}
```

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
git clone https://github.com/YOUR_USERNAME/color-analysis-tool.git
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
If you use this tool in your projects or research, please cite it as follows:

### APA Format
```
Semoglou, M. (2025). Image Color Analysis Tool [Computer software]. GitHub. https://github.com/MichailSemoglou/color-analysis-tool
```

### BibTeX
```bibtex
@software{semoglou2025coloranalysis,
  author = {Semoglou, Michail},
  title = {Image Color Analysis Tool},
  year = {2025},
  url = {https://github.com/MichailSemoglou/color-analysis-tool},
  version = {1.0.0}
}
```

### Chicago Format
```
Semoglou, Michail. 2025. "Image Color Analysis Tool." GitHub. https://github.com/MichailSemoglou/color-analysis-tool.
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Pillow](https://python-pillow.org/) for image processing capabilities
- [tqdm](https://github.com/tqdm/tqdm) for progress bar functionality

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a history of changes to this project.
