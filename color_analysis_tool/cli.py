"""Command-line interface for Color Analysis Tool.

This module provides the CLI entry point for the color analysis tool,
allowing users to analyze images from the command line.

Usage:
    color-analysis [-h] [-v] [-s {frequency,hue,saturation,brightness}]
                   [-c COLORS] [-f {txt,json,css}]
                   [--extractor {perceptual,legacy}]
                   [--harmony-engine {oklch,hsv_legacy}]
                   [--cmyk-profile PATH] [--cmyk-method {icc,device_naive}]
                   input output

Examples:
    color-analysis image.jpg output/
    color-analysis images/ output/ -s hue -v
    color-analysis image.jpg output/ -c 32 -f json
    color-analysis image.jpg output/ -c 32 -f css
    color-analysis image.jpg output/ --extractor legacy --harmony-engine hsv_legacy
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Union

from .analyzer import ImageAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="color-analysis",
        description="Deterministic, color-managed color analysis for computational color research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  color-analysis image.jpg output/                  Analyze single image
  color-analysis images/ output/                    Batch process directory
  color-analysis image.jpg output/ -s hue           Sort by hue
  color-analysis image.jpg output/ -c 32            Reduce to 32 colors
  color-analysis image.jpg output/ -f json          Output as JSON
  color-analysis images/ output/ -c 64 -f json -v   Full options
  color-analysis image.jpg output/ --extractor legacy   v1 extraction pipeline

For more information, visit: https://github.com/MichailSemoglou/color-analysis-tool
        """
    )
    parser.add_argument(
        "input",
        help="Path to input file or directory",
        type=Path
    )
    parser.add_argument(
        "output",
        help="Path to output directory",
        type=Path
    )
    parser.add_argument(
        "-s", "--sort",
        choices=["frequency", "hue", "saturation", "brightness"],
        default="frequency",
        help="Sort colors by specified criterion (default: frequency)"
    )
    parser.add_argument(
        "-c", "--colors",
        default="auto",
        metavar="N",
        help=(
            "Reduce the image to at most N colors (1-256) before analysis. "
            "Produces a clean, meaningful palette and speeds up processing. "
            "0 disables palette reduction; 'auto' (default) bounds the "
            "palette automatically"
        )
    )
    parser.add_argument(
        "-f", "--format",
        choices=["txt", "json", "css"],
        default="txt",
        dest="output_format",
        help=(
            "Output format (default: txt). "
            "'css' emits three design-token files: "
            "{name}_tokens.css (CSS custom properties, HEX and OKLCH), "
            "{name}_tokens.json (W3C Design Token format), and "
            "{name}_tailwind.css (Tailwind CSS v4 @theme)."
        )
    )
    parser.add_argument(
        "--extractor",
        choices=["perceptual", "legacy"],
        default="perceptual",
        help=(
            "Palette extraction engine (default: perceptual). "
            "'perceptual' clusters colors with deterministic k-means++ in "
            "OKLab and merges near-duplicates (CIEDE2000 2.2); "
            "'legacy' reproduces the v1 exact-counting pipeline"
        )
    )
    parser.add_argument(
        "--harmony-engine",
        choices=["oklch", "hsv_legacy"],
        default="oklch",
        dest="harmony_engine",
        help=(
            "Harmony engine (default: oklch). 'oklch' rotates hue in OKLCh "
            "with hue-preserving gamut mapping; "
            "'hsv_legacy' reproduces the v1 HSV harmonies"
        )
    )
    parser.add_argument(
        "--cmyk-profile",
        metavar="PATH",
        default=None,
        dest="cmyk_profile",
        help=(
            "Path to a custom CMYK ICC profile for the CMYK values "
            "(default: bundled FOGRA39 profile, ISO Coated v2)"
        )
    )
    parser.add_argument(
        "--cmyk-method",
        choices=["icc", "device_naive"],
        default="icc",
        dest="cmyk_method",
        help=(
            "CMYK conversion method (default: icc). "
            "'device_naive' reproduces the v1 formula"
        )
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Enable verbose logging",
        action="store_true"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {_get_version()}"
    )

    args = parser.parse_args()

    if args.colors == "auto":
        colors: Union[int, str] = "auto"
    else:
        try:
            colors = int(args.colors)
        except ValueError:
            parser.error("--colors must be 'auto' or an integer between 0 and 256")
        if not 0 <= colors <= 256:
            parser.error("--colors must be 'auto' or an integer between 0 and 256")

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("color_analysis_tool").setLevel(logging.DEBUG)

    analyzer = ImageAnalyzer()

    try:
        if args.input.is_file():
            logger.info(f"Analyzing single file: {args.input}")
            image_info = analyzer.analyze_image(
                args.input,
                sort_by=args.sort,
                max_colors=colors,
                extractor=args.extractor,
                harmony_engine=args.harmony_engine,
                cmyk_profile=args.cmyk_profile,
                cmyk_method=args.cmyk_method,
            )
            if image_info:
                analyzer.save_analysis(
                    args.output,
                    image_info,
                    sort_by=args.sort,
                    output_format=args.output_format,
                )
                logger.info("Analysis complete!")
            else:
                logger.error("Failed to analyze image")
                sys.exit(1)
        elif args.input.is_dir():
            logger.info(f"Batch processing directory: {args.input}")
            analyzer.batch_process(
                args.input,
                args.output,
                sort_by=args.sort,
                max_colors=colors,
                output_format=args.output_format,
                extractor=args.extractor,
                harmony_engine=args.harmony_engine,
                cmyk_profile=args.cmyk_profile,
                cmyk_method=args.cmyk_method,
            )
            logger.info("Batch processing complete!")
        else:
            logger.error(f"Invalid input path: {args.input}")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)


def _get_version() -> str:
    """Get the package version."""
    try:
        from . import __version__
        return __version__
    except ImportError:
        return "unknown"


if __name__ == "__main__":
    main()
