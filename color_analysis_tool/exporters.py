"""Exporters for analysis results: plain text, JSON, and design tokens.

This module holds the output layer of the tool. save_analysis writes an
ImageInfo as a text report, a JSON document, or three design-token files
(CSS custom properties, W3C Design Tokens JSON, Tailwind config snippet).
The public entry point remains ImageAnalyzer.save_analysis, which
delegates here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Union

if TYPE_CHECKING:
    from .analyzer import ImageInfo

logger = logging.getLogger(__name__)

VALID_OUTPUT_FORMATS = {"txt", "json", "css"}

# Hard cap on colors written by any exporter (safety valve for max_colors=0)
MAX_OUTPUT_COLORS = 1000


def _sanitize_display_name(name: str) -> str:
    """Return a filename safe to embed in generated reports and comments.

    Strips block-comment terminators, line breaks, and control characters
    so a hostile filename cannot inject content into generated files.
    """
    name = name.replace("*/", "")
    name = re.sub(r"[\r\n\u2028\u2029]+", " ", name)
    return "".join(c for c in name if c.isprintable())


def _safe_output_stem(name: str) -> str:
    """Return a filesystem-safe, collision-resistant stem for output files.

    Builds on the display sanitizer, additionally replacing backslashes
    (legal in POSIX filenames, but a path separator on Windows). When
    sanitization modified the name, a stable digest of the original is
    appended so two different source files cannot overwrite each other.
    """
    safe = _sanitize_display_name(name).replace("\\", "-")
    if safe != name:
        # os.fsencode preserves surrogate-escaped bytes from non-UTF-8
        # filenames, where str.encode("utf-8") would raise
        digest = hashlib.sha256(os.fsencode(name)).hexdigest()[:8]
        safe = f"{safe}-{digest}"
    return safe


def save_analysis(
    output_dir: Union[str, Path],
    image_info: ImageInfo,
    sort_by: str = "frequency",
    output_format: str = "txt",
    input_base: Optional[Path] = None,
    file_path: Optional[Path] = None,
) -> None:
    """Save analysis results to a file.

    Args:
        output_dir: Root directory where analysis files will be saved.
        image_info: ImageInfo object containing the analysis results.
        sort_by: The sorting criterion used (recorded in the output).
        output_format: Output format — 'txt' (default), 'json', or 'css'.
            'css' emits three files: a CSS custom-properties stylesheet,
            a W3C Design Token JSON file, and a Tailwind config snippet.
        input_base: Base input directory used to mirror subdirectory
            structure inside output_dir for batch processing.
        file_path: Original file path; used with input_base to compute
            the relative subdirectory for output.

    Raises:
        ValueError: If output_format is not recognised.
    """
    if output_format not in VALID_OUTPUT_FORMATS:
        raise ValueError(
            f"output_format must be one of {VALID_OUTPUT_FORMATS}, got {output_format!r}"
        )

    output_dir = Path(output_dir)

    # Mirror subdirectory structure when batch-processing
    if input_base is not None and file_path is not None:
        try:
            rel = file_path.parent.relative_to(input_base)
            output_dir = output_dir / rel
        except ValueError:
            pass  # file_path not under input_base — write flat

    output_dir.mkdir(parents=True, exist_ok=True)

    # Safety valve: bound exporter output even for unbounded analyses
    # (max_colors=0 on a high-color image)
    truncated_from: Optional[int] = None
    if len(image_info.colors) > MAX_OUTPUT_COLORS:
        truncated_from = len(image_info.colors)
        logger.warning(
            f"Truncating output to the first {MAX_OUTPUT_COLORS} of "
            f"{truncated_from} colors; use max_colors to bound the palette"
        )
        image_info = replace(image_info, colors=image_info.colors[:MAX_OUTPUT_COLORS])

    stem = f"{_safe_output_stem(image_info.filename)}_analysis"

    if output_format == "json":
        _save_json(output_dir / f"{stem}.json", image_info, sort_by, truncated_from)
    elif output_format == "css":
        _save_css(output_dir, image_info, truncated_from)
    else:
        _save_txt(output_dir / f"{stem}.txt", image_info, sort_by, truncated_from)


def _save_txt(
    output_file: Path,
    image_info: ImageInfo,
    sort_by: str,
    truncated_from: Optional[int] = None,
) -> None:
    with output_file.open('w', encoding='utf-8') as f:
        f.write(f"Image Analysis for {_sanitize_display_name(image_info.filename)}\n")
        f.write(f"Dimensions: {image_info.dimensions[0]}x{image_info.dimensions[1]}\n")
        f.write(f"Format: {image_info.format}\n")

        if image_info.dominant_color:
            f.write(f"Dominant Color: RGB{image_info.dominant_color}\n")

        if truncated_from:
            f.write(
                f"Note: truncated to the first {MAX_OUTPUT_COLORS} "
                f"of {truncated_from} colors.\n"
            )

        f.write(f"\nColors (sorted by {sort_by}):\n")
        for idx, color in enumerate(image_info.colors, 1):
            f.write(f"\nColor #{idx}:\n")
            f.write(f"  RGB: {color.rgb}\n")
            f.write(f"  HEX: {color.hex}\n")
            f.write(f"  CMYK: {color.cmyk}\n")
            f.write(f"  Frequency: {color.frequency}%\n")

            if color.harmonies:
                f.write("\n  Color Harmonies:\n")
                for harmony_type, harmony_colors in color.harmonies.items():
                    f.write(f"    {harmony_type.capitalize()}:\n")
                    for harmony_color in harmony_colors:
                        f.write(f"      RGB{harmony_color}\n")

    logger.info(f"Analysis saved to {output_file}")


def _save_json(
    output_file: Path,
    image_info: ImageInfo,
    sort_by: str,
    truncated_from: Optional[int] = None,
) -> None:
    data: Dict[str, object] = {
        "filename": image_info.filename,
        "dimensions": {"width": image_info.dimensions[0], "height": image_info.dimensions[1]},
        "format": image_info.format,
        "sorted_by": sort_by,
        "dominant_color": list(image_info.dominant_color) if image_info.dominant_color else None,
        "colors": [
            {
                "rgb": list(c.rgb),
                "hex": c.hex,
                "cmyk": list(c.cmyk),
                "frequency": c.frequency,
                "harmonies": {k: [list(v) for v in vs] for k, vs in c.harmonies.items()},
            }
            for c in image_info.colors
        ],
    }
    if truncated_from:
        data["truncated_from"] = truncated_from
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    logger.info(f"Analysis saved to {output_file}")


def _save_css(
    output_dir: Path,
    image_info: ImageInfo,
    truncated_from: Optional[int] = None,
) -> None:
    """Save palette as CSS custom properties, W3C Design Tokens, and Tailwind config.

    Three files are written to output_dir:
    - {filename}_tokens.css   — CSS custom properties
    - {filename}_tokens.json  — W3C Design Token Community Group format
    - {filename}_tailwind.js  — Tailwind CSS colors config snippet

    Args:
        output_dir: Directory to write the three token files into.
        image_info: ImageInfo object containing the analysis results.
        truncated_from: When set, the original color count before
            truncation; a note is recorded in all three files.
    """
    # Deferred import: analyzer imports this module for delegation, so
    # importing analyzer here at module level would be circular
    from .analyzer import ColorConverter

    stem = _safe_output_stem(image_info.filename)
    colors = image_info.colors

    # ── CSS custom properties ─────────────────────────────────────────
    css_lines = [
        f"/* Color palette extracted from {stem} by Image Color Analysis Tool */",
        f"/* {len(colors)} colors, sorted by frequency */",
    ]
    if truncated_from:
        css_lines.append(
            f"/* Note: truncated to the first {MAX_OUTPUT_COLORS} "
            f"of {truncated_from} colors */"
        )
    css_lines.append(":root {")
    for idx, color in enumerate(colors, 1):
        r, g, b = color.rgb
        css_lines.append(
            f"  --color-{idx}: {color.hex};  "
            f"/* RGB({r}, {g}, {b}) · {color.frequency}% */"
        )
    if image_info.dominant_color:
        css_lines.append(f"  --color-dominant: "
                         f"{ColorConverter.rgb_to_hex(image_info.dominant_color)};")
    css_lines.append("}")
    css_file = output_dir / f"{stem}_tokens.css"
    css_file.write_text("\n".join(css_lines), encoding="utf-8")
    logger.info(f"CSS tokens saved to {css_file}")

    # ── W3C Design Token Community Group format ───────────────────────
    # Spec: https://design-tokens.github.io/community-group/format/
    token_dict: Dict[str, object] = {}
    for idx, color in enumerate(colors, 1):
        token_dict[f"color-{idx}"] = {
            "$type": "color",
            "$value": color.hex,
            "$description": (
                f"RGB({color.rgb[0]}, {color.rgb[1]}, {color.rgb[2]}) · "
                f"{color.frequency}% of image"
            ),
        }
    if image_info.dominant_color:
        token_dict["color-dominant"] = {
            "$type": "color",
            "$value": ColorConverter.rgb_to_hex(image_info.dominant_color),
            "$description": "Most frequent color in the image",
        }
    metadata: Dict[str, object] = {"source": stem}
    if truncated_from:
        metadata["truncated_from"] = truncated_from
    tokens_wrapper = {
        "$schema": "https://design-tokens.github.io/community-group/format/",
        "$metadata": metadata,
        "palette": token_dict,
    }
    tokens_file = output_dir / f"{stem}_tokens.json"
    tokens_file.write_text(json.dumps(tokens_wrapper, indent=2), encoding="utf-8")
    logger.info(f"Design tokens saved to {tokens_file}")

    # ── Tailwind CSS colors config snippet ────────────────────────────
    # The key is derived from the filename and becomes a class-name
    # fragment, so replace runs of characters invalid in CSS/Tailwind
    # identifiers (spaces, dots, etc.) with hyphens
    tw_key = re.sub(r"[^A-Za-z0-9_-]+", "-", stem)
    tw_entries = [
        f"  '{idx}': '{color.hex}',  // {color.frequency}%"
        for idx, color in enumerate(colors, 1)
    ]
    if image_info.dominant_color:
        tw_entries.append(
            f"  'dominant': '{ColorConverter.rgb_to_hex(image_info.dominant_color)}',"
        )
    tw_lines = [
        f"// Tailwind CSS palette — extracted from {stem}",
        "// Paste inside the `colors` key of your tailwind.config.js",
    ]
    if truncated_from:
        tw_lines.append(
            f"// Note: truncated to the first {MAX_OUTPUT_COLORS} "
            f"of {truncated_from} colors"
        )
    tw_lines += [
        "module.exports = {",
        "  theme: {",
        "    extend: {",
        "      colors: {",
        f"        '{tw_key}': {{",
    ]
    tw_lines.extend(f"          {e}" for e in tw_entries)
    tw_lines += [
        "        },",
        "      },",
        "    },",
        "  },",
        "};",
    ]
    tw_file = output_dir / f"{stem}_tailwind.js"
    tw_file.write_text("\n".join(tw_lines), encoding="utf-8")
    logger.info(f"Tailwind config saved to {tw_file}")
