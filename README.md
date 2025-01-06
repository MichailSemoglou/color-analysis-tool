# Image Color Analysis Tool

A powerful Python tool for analyzing colors in images, providing detailed information about color distributions, harmonies, and various color space conversions. Perfect for designers, artists, and developers working with color analysis and manipulation.

## Features

- **Comprehensive Color Analysis**: Extract and analyze colors from images
- **Multiple Color Spaces**: Support for RGB, HEX, and CMYK color formats
- **Color Harmony**: Calculate complementary, analogous, triadic, and tetradic color harmonies
- **Batch Processing**: Analyze multiple images in a directory
- **Detailed Reports**: Generate comprehensive analysis reports for each image
- **Format Support**: Works with PNG, JPG, TIFF, WebP, and PSD files

## Installation

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

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Analyze a single image:
```bash
python color_analysis.py path/to/image.jpg output/directory
```

Process all images in a directory:
```bash
python color_analysis.py path/to/image/directory output/directory
```

Enable verbose logging:
```bash
python color_analysis.py path/to/image.jpg output/directory -v
```

### Example Output

The tool generates a detailed analysis file for each image with the following information:
- Image metadata (dimensions, format)
- Color frequency analysis
- RGB, HEX, and CMYK values for each significant color
- Color harmonies for each major color

Example output structure:
```
Image Analysis for example.jpg
Dimensions: 1920x1080
Format: JPEG

Colors (sorted by frequency):
  RGB: (255, 255, 255), HEX: #FFFFFF, CMYK: (0, 0, 0, 0), Frequency: 35.2%
    Harmonies:
      Complementary: [(0, 0, 0)]
      Analogous: [(255, 245, 245), (255, 255, 255), (245, 255, 255)]
      Triadic: [(255, 255, 0), (255, 255, 255), (0, 255, 255)]
```

## API Usage

You can also use the tool as a library in your Python projects:

```python
from color_analysis import ImageAnalyzer

analyzer = ImageAnalyzer()

# Analyze a single image
image_info = analyzer.analyze_image('path/to/image.jpg')

# Save the analysis
analyzer.save_analysis('output/directory', image_info)

# Process multiple images
analyzer.batch_process('input/directory', 'output/directory')
```

## Requirements

- Python 3.7 or higher
- Pillow >= 9.0.0
- tqdm >= 4.65.0
- colormath >= 3.0.0

See `requirements.txt` for detailed version information.

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
pip install -r requirements.txt
```

3. Run tests:
```bash
python -m pytest tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Pillow](https://python-pillow.org/) for image processing capabilities
- [colormath](https://python-colormath.readthedocs.io/) for color space conversions
- [tqdm](https://github.com/tqdm/tqdm) for progress bar functionality
