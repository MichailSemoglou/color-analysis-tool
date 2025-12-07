"""
Command-line interface for Color Analysis Tool.

This module provides the CLI entry point for the color analysis tool,
allowing users to analyze images from the command line.

Usage:
    color-analysis [-h] [-v] [-s {frequency,hue,saturation,brightness}] input output

Examples:
    color-analysis image.jpg output/
    color-analysis images/ output/ -s hue -v
"""

import sys
import argparse
import logging
from pathlib import Path

from .analyzer import ImageAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="color-analysis",
        description="Enhanced Image Color Analysis Tool - Analyze colors in images with detailed reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  color-analysis image.jpg output/           Analyze single image
  color-analysis images/ output/             Batch process directory
  color-analysis image.jpg output/ -s hue    Sort by hue
  color-analysis images/ output/ -v          Verbose output

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

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("color_analysis_tool").setLevel(logging.DEBUG)

    analyzer = ImageAnalyzer()

    try:
        if args.input.is_file():
            logger.info(f"Analyzing single file: {args.input}")
            image_info = analyzer.analyze_image(args.input, sort_by=args.sort)
            if image_info:
                analyzer.save_analysis(args.output, image_info, sort_by=args.sort)
                logger.info("Analysis complete!")
            else:
                logger.error("Failed to analyze image")
                sys.exit(1)
        elif args.input.is_dir():
            logger.info(f"Batch processing directory: {args.input}")
            analyzer.batch_process(args.input, args.output, sort_by=args.sort)
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
