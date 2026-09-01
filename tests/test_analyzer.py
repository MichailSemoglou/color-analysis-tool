"""Tests for ImageAnalyzer using synthetic in-memory images."""

import json
import os

import pytest
from PIL import Image

from color_analysis_tool.analyzer import ColorConverter, ColorInfo, ImageAnalyzer, ImageInfo


@pytest.fixture
def red_image(tmp_path):
    """A 10x10 solid red PNG."""
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    path = tmp_path / "red.png"
    img.save(path)
    return path


@pytest.fixture
def two_color_image(tmp_path):
    """A 10x10 image that is half red (top 5 rows) half blue (bottom 5 rows)."""
    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    for y in range(5, 10):
        for x in range(10):
            img.putpixel((x, y), (0, 0, 255))
    path = tmp_path / "two_color.png"
    img.save(path)
    return path


@pytest.fixture
def analyzer():
    return ImageAnalyzer()


@pytest.fixture
def mixed_alpha_image(tmp_path):
    """A 10x10 RGBA image: 60 fully transparent pixels, 40 opaque red pixels."""
    img = Image.new("RGBA", (10, 10), color=(0, 0, 0, 0))
    for y in range(6, 10):
        for x in range(10):
            img.putpixel((x, y), (255, 0, 0, 255))
    path = tmp_path / "mixed_alpha.png"
    img.save(path)
    return path


@pytest.fixture
def fully_transparent_image(tmp_path):
    """A 10x10 RGBA image in which every pixel is fully transparent."""
    img = Image.new("RGBA", (10, 10), color=(0, 0, 0, 0))
    path = tmp_path / "transparent.png"
    img.save(path)
    return path


@pytest.fixture
def high_color_image(tmp_path):
    """A 32x32 RGB image with 1024 unique colors (above the auto threshold)."""
    img = Image.new("RGB", (32, 32))
    for i in range(1024):
        img.putpixel((i % 32, i // 32), (i % 256, i // 256, (i * 7) % 256))
    path = tmp_path / "high_color.png"
    img.save(path)
    return path


# ── analyze_image ────────────────────────────────────────────────────────────

class TestAnalyzeImage:
    def test_returns_image_info(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert isinstance(result, ImageInfo)

    def test_filename(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert result.filename == "red.png"

    def test_dimensions(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert result.dimensions == (10, 10)

    def test_dominant_color_solid_red(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert result.dominant_color == (255, 0, 0)

    def test_colors_list_not_empty(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert len(result.colors) > 0

    def test_color_info_fields(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        color = result.colors[0]
        assert isinstance(color, ColorInfo)
        assert color.rgb == (255, 0, 0)
        assert color.hex == "#ff0000"
        assert color.weight == 100.0

    def test_color_info_perceptual_fields(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        color = result.colors[0]
        assert color.oklch == pytest.approx((0.628, 0.2577, 29.2339), abs=1e-3)
        assert color.contrast is not None
        assert color.contrast.on_white.wcag_ratio == pytest.approx(4.0, abs=0.01)
        # The analyzed color is the dominant color: no self-comparison
        assert color.contrast.vs_dominant is None

    def test_cmyk_is_icc_based_by_default(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert result.colors[0].cmyk == ColorConverter.rgb_to_cmyk(255, 0, 0)
        assert result.cmyk_profile == "FOGRA39 (ISO Coated v2)"

    def test_two_colors_detected(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image)
        rgbs = [c.rgb for c in result.colors]
        assert (255, 0, 0) in rgbs
        assert (0, 0, 255) in rgbs

    def test_frequencies_sum_to_100(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image)
        total = sum(c.weight for c in result.colors)
        assert abs(total - 100.0) < 0.1

    def test_invalid_sort_raises(self, analyzer, red_image):
        with pytest.raises(ValueError, match="sort_by"):
            analyzer.analyze_image(red_image, sort_by="luminance")

    def test_max_colors_above_256_raises(self, analyzer, red_image):
        with pytest.raises(ValueError, match="max_colors"):
            analyzer.analyze_image(red_image, max_colors=257)

    def test_max_colors_negative_raises(self, analyzer, red_image):
        with pytest.raises(ValueError, match="max_colors"):
            analyzer.analyze_image(red_image, max_colors=-1)

    def test_max_colors_fractional_raises(self, analyzer, red_image):
        # 1.5 passes a bare range check but is not a valid palette size
        with pytest.raises(ValueError, match="max_colors"):
            analyzer.analyze_image(red_image, max_colors=1.5)

    def test_missing_file_returns_none(self, analyzer, tmp_path):
        result = analyzer.analyze_image(tmp_path / "nonexistent.png")
        assert result is None

    def test_max_colors_reduces_palette(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image, max_colors=2)
        assert result is not None
        assert len(result.colors) <= 2

    def test_sort_by_frequency(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image, sort_by="frequency")
        freqs = [c.weight for c in result.colors]
        assert freqs == sorted(freqs, reverse=True)

    def test_harmonies_present_for_first_color(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert result.colors[0].harmonies != {}

    def test_harmonies_absent_beyond_limit(self, analyzer, tmp_path):
        # Build an image with more than HARMONY_LIMIT unique colors
        from color_analysis_tool.analyzer import HARMONY_LIMIT
        size = HARMONY_LIMIT + 10
        img = Image.new("RGB", (size, 1))
        for x in range(size):
            img.putpixel((x, 0), (x, x, x))
        path = tmp_path / "many_colors.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result is not None
        # Colors beyond HARMONY_LIMIT should have empty harmonies
        for color in result.colors[HARMONY_LIMIT:]:
            assert color.harmonies == {}


# ── save_analysis (txt) ───────────────────────────────────────────────────────

class TestSaveAnalysisTxt:
    def test_creates_txt_file(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info)
        assert (tmp_path / "red.png_analysis.txt").exists()

    def test_txt_contains_filename(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "red.png_analysis.txt").read_text()
        assert "red.png" in content

    def test_txt_contains_dominant_color(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "red.png_analysis.txt").read_text()
        assert "255" in content

    def test_invalid_format_raises(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        with pytest.raises(ValueError, match="output_format"):
            analyzer.save_analysis(tmp_path, info, output_format="xml")


# ── save_analysis (json) ─────────────────────────────────────────────────────

class TestSaveAnalysisJson:
    def test_creates_json_file(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        assert (tmp_path / "red.png_analysis.json").exists()

    def test_json_is_valid(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        data = json.loads((tmp_path / "red.png_analysis.json").read_text())
        assert data["filename"] == "red.png"
        assert "colors" in data
        assert "dominant_color" in data

    def test_json_dominant_color(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        data = json.loads((tmp_path / "red.png_analysis.json").read_text())
        assert data["dominant_color"] == [255, 0, 0]

    def test_json_color_fields(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        data = json.loads((tmp_path / "red.png_analysis.json").read_text())
        color = data["colors"][0]
        assert "rgb" in color
        assert "hex" in color
        assert "cmyk" in color
        assert "weight" in color
        assert "oklch" in color
        assert "wcag" in color
        assert "apca" in color
        assert "harmonies" in color

    def test_json_wcag_and_apca_structure(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        data = json.loads((tmp_path / "red.png_analysis.json").read_text())
        color = data["colors"][0]
        on_white = color["wcag"]["on_white"]
        assert set(on_white.keys()) == {"ratio", "aa", "aaa"}
        assert on_white["ratio"] == pytest.approx(4.0, abs=0.01)
        # The analyzed color is the dominant color: no self-comparison
        assert color["wcag"]["vs_dominant"] is None
        assert color["apca"]["status"] == "experimental"
        assert isinstance(color["apca"]["on_white"], float)

    def test_json_records_cmyk_profile(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        data = json.loads((tmp_path / "red.png_analysis.json").read_text())
        assert data["cmyk_profile"] == "FOGRA39 (ISO Coated v2)"


# ── batch_process ─────────────────────────────────────────────────────────────

class TestBatchProcess:
    def test_processes_all_images(self, analyzer, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        for name, color in [("a.png", (255, 0, 0)), ("b.png", (0, 255, 0))]:
            img = Image.new("RGB", (5, 5), color=color)
            img.save(input_dir / name)

        output_dir = tmp_path / "output"
        analyzer.batch_process(input_dir, output_dir)

        assert (output_dir / "a.png_analysis.txt").exists()
        assert (output_dir / "b.png_analysis.txt").exists()

    def test_mirrors_subdirectory_structure(self, analyzer, tmp_path):
        input_dir = tmp_path / "input"
        sub = input_dir / "sub"
        sub.mkdir(parents=True)
        img = Image.new("RGB", (5, 5), color=(0, 0, 255))
        img.save(sub / "c.png")

        output_dir = tmp_path / "output"
        analyzer.batch_process(input_dir, output_dir)

        assert (output_dir / "sub" / "c.png_analysis.txt").exists()

    def test_batch_json_output(self, analyzer, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        img = Image.new("RGB", (5, 5), color=(10, 20, 30))
        img.save(input_dir / "img.png")

        output_dir = tmp_path / "output"
        analyzer.batch_process(input_dir, output_dir, output_format="json")

        assert (output_dir / "img.png_analysis.json").exists()

    def test_continues_after_save_failure(self, analyzer, tmp_path, monkeypatch):
        # A file whose report cannot be saved must not abort the batch
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        for name, color in [("a.png", (255, 0, 0)), ("b.png", (0, 255, 0))]:
            Image.new("RGB", (5, 5), color=color).save(input_dir / name)

        original_save = ImageAnalyzer.save_analysis

        def failing_save(self, output_dir, image_info, **kwargs):
            if image_info.filename == "a.png":
                raise OSError("simulated disk failure")
            return original_save(self, output_dir, image_info, **kwargs)

        monkeypatch.setattr(ImageAnalyzer, "save_analysis", failing_save)
        output_dir = tmp_path / "output"
        analyzer.batch_process(input_dir, output_dir)
        assert (output_dir / "b.png_analysis.txt").exists()

    def test_processes_files_in_sorted_order(self, analyzer, tmp_path, monkeypatch):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        for name in ("c.png", "a.png", "b.png"):
            Image.new("RGB", (5, 5), color=(1, 2, 3)).save(input_dir / name)

        processed = []
        original_analyze = ImageAnalyzer.analyze_image

        def recording_analyze(self, file_path, **kwargs):
            processed.append(file_path.name)
            return original_analyze(self, file_path, **kwargs)

        monkeypatch.setattr(ImageAnalyzer, "analyze_image", recording_analyze)
        analyzer.batch_process(input_dir, tmp_path / "output")
        assert processed == ["a.png", "b.png", "c.png"]


# ── save_analysis (css) ───────────────────────────────────────────────────────

class TestSaveAnalysisCss:
    def test_creates_three_files(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        assert (tmp_path / "red.png_tokens.css").exists()
        assert (tmp_path / "red.png_tokens.json").exists()
        assert (tmp_path / "red.png_tailwind.css").exists()

    def test_css_contains_custom_property(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tokens.css").read_text()
        assert "--color-1:" in content
        assert "#ff0000" in content

    def test_css_contains_root_selector(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tokens.css").read_text()
        assert ":root {" in content

    def test_css_dominant_property(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tokens.css").read_text()
        assert "--color-dominant:" in content

    def test_css_records_sort_order(self, analyzer, two_color_image, tmp_path):
        # Regression: the CSS header must record the actual sort criterion
        info = analyzer.analyze_image(two_color_image, sort_by="hue")
        analyzer.save_analysis(tmp_path, info, sort_by="hue", output_format="css")
        content = (tmp_path / "two_color.png_tokens.css").read_text()
        assert "sorted by hue" in content

    def test_tokens_json_is_valid(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        data = json.loads((tmp_path / "red.png_tokens.json").read_text())
        assert "$schema" in data
        assert "palette" in data
        assert "color-1" in data["palette"]

    def test_tokens_json_color_type(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        data = json.loads((tmp_path / "red.png_tokens.json").read_text())
        entry = data["palette"]["color-1"]
        assert entry["$type"] == "color"
        assert entry["$value"] == "#ff0000"

    def test_tokens_json_dominant_entry(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        data = json.loads((tmp_path / "red.png_tokens.json").read_text())
        assert "color-dominant" in data["palette"]

    def test_tailwind_contains_theme_block(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tailwind.css").read_text()
        assert "@theme {" in content
        assert "oklch(" in content

    def test_tailwind_import_hint_names_generated_file(self, analyzer, red_image, tmp_path):
        # The import hint must reference the file actually written
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tailwind.css").read_text()
        assert '@import "./red.png_tailwind.css"' in content

    def test_tailwind_uses_css_variable_keys(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tailwind.css").read_text()
        assert "--color-red-png-1:" in content
        assert "--color-red-png-dominant:" in content

    def test_batch_css_output(self, analyzer, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        img = Image.new("RGB", (5, 5), color=(0, 128, 255))
        img.save(input_dir / "img.png")

        output_dir = tmp_path / "output"
        analyzer.batch_process(input_dir, output_dir, output_format="css")

        assert (output_dir / "img.png_tokens.css").exists()
        assert (output_dir / "img.png_tokens.json").exists()
        assert (output_dir / "img.png_tailwind.css").exists()

    def test_tailwind_key_sanitized(self, analyzer, tmp_path):
        img = Image.new("RGB", (5, 5), color=(255, 0, 0))
        path = tmp_path / "my image 01.png"
        img.save(path)
        info = analyzer.analyze_image(path)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "my image 01.png_tailwind.css").read_text()
        assert "--color-my-image-01-png-1:" in content


# ── alpha channel handling ─────────────────────────────────────────────────

class TestAlphaChannel:
    def test_dominant_color_ignores_transparent_pixels(self, analyzer, mixed_alpha_image):
        # Regression: transparent pixels outnumber red 60:40 but must not win
        result = analyzer.analyze_image(mixed_alpha_image)
        assert result.dominant_color == (255, 0, 0)

    def test_transparent_pixels_excluded_from_colors(self, analyzer, mixed_alpha_image):
        result = analyzer.analyze_image(mixed_alpha_image)
        assert len(result.colors) == 1
        assert result.colors[0].rgb == (255, 0, 0)

    def test_frequency_relative_to_visible_pixels(self, analyzer, mixed_alpha_image):
        # 40 visible pixels out of 100 total; frequency must be 100%, not 40%
        result = analyzer.analyze_image(mixed_alpha_image)
        assert result.colors[0].weight == 100.0

    def test_partially_transparent_pixels_are_visible(self, analyzer, tmp_path):
        # Any pixel with alpha > 0 counts as visible
        img = Image.new("RGBA", (10, 10), color=(0, 0, 255, 1))
        path = tmp_path / "barely_visible.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (0, 0, 255)
        assert result.colors[0].weight == 100.0

    def test_fully_transparent_image_returns_empty_palette(self, analyzer, fully_transparent_image):
        result = analyzer.analyze_image(fully_transparent_image)
        assert result is not None
        assert result.colors == []
        assert result.dominant_color is None

    def test_fully_transparent_image_json_output(self, analyzer, fully_transparent_image, tmp_path):
        info = analyzer.analyze_image(fully_transparent_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        data = json.loads((tmp_path / "transparent.png_analysis.json").read_text())
        assert data["dominant_color"] is None
        assert data["colors"] == []

    @pytest.mark.parametrize("extractor", ["perceptual", "legacy"])
    def test_palette_reduction_preserves_alpha(self, analyzer, mixed_alpha_image, extractor):
        # Regression: --colors N must not turn transparent pixels opaque black
        # (the original bug lived in the legacy quantization path)
        result = analyzer.analyze_image(mixed_alpha_image, max_colors=4, extractor=extractor)
        assert result.dominant_color == (255, 0, 0)
        assert len(result.colors) == 1
        assert result.colors[0].weight == 100.0

    @pytest.mark.parametrize("extractor", ["perceptual", "legacy"])
    def test_reduced_fully_transparent_image(self, analyzer, fully_transparent_image, extractor):
        result = analyzer.analyze_image(fully_transparent_image, max_colors=4, extractor=extractor)
        assert result is not None
        assert result.colors == []
        assert result.dominant_color is None

    @pytest.mark.parametrize("extractor", ["perceptual", "legacy"])
    def test_transparent_payload_does_not_shift_palette(self, analyzer, tmp_path, extractor):
        # Regression: noisy RGB payloads under fully transparent pixels must
        # not consume palette slots or blend visible colors during palette
        # reduction (the original bug lived in the legacy quantization path)
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(4):
            for x in range(8):
                img.putpixel((x, y), (
                    (x * 37 + y * 91) % 256,
                    (x * 53 + y * 17) % 256,
                    (x * 11 + y * 71) % 256,
                    0,
                ))
        visible = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        for y in range(4, 8):
            for x in range(8):
                img.putpixel((x, y), visible[x // 2] + (255,))
        path = tmp_path / "noisy_alpha.png"
        img.save(path)
        result = analyzer.analyze_image(path, max_colors=5, extractor=extractor)
        assert {c.rgb for c in result.colors} == set(visible)
        assert result.dominant_color in visible

    def test_same_rgb_different_alpha_merges(self, analyzer, tmp_path):
        # Regression: pixels sharing an RGB value but differing in (non-zero)
        # alpha must aggregate into one entry, not split into duplicates
        img = Image.new("RGBA", (10, 10), (255, 0, 0, 255))
        for y in range(6, 10):
            for x in range(10):
                img.putpixel((x, y), (255, 0, 0, 128))
        path = tmp_path / "anti_aliased.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert len(result.colors) == 1
        assert result.colors[0].rgb == (255, 0, 0)
        assert result.colors[0].weight == 100.0
        assert result.dominant_color == (255, 0, 0)


def _make_two_color_image(path, top, bottom, size=10):
    """Build an image: top half `top` color, bottom half `bottom` color."""
    img = Image.new("RGB", (size, size), color=top)
    for y in range(size // 2, size):
        for x in range(size):
            img.putpixel((x, y), bottom)
    img.save(path)
    return path


# ── sort orders ─────────────────────────────────────────────────────────────

class TestSortOrders:
    def test_sort_by_hue_ascending(self, analyzer, tmp_path):
        # Green is encountered first, so most_common() lists it first;
        # hue sorting must reorder red (0 deg) before green (120 deg)
        path = _make_two_color_image(tmp_path / "hue.png", (0, 255, 0), (255, 0, 0))
        result = analyzer.analyze_image(path, sort_by="hue")
        assert [c.rgb for c in result.colors] == [(255, 0, 0), (0, 255, 0)]

    def test_sort_by_saturation_descending(self, analyzer, tmp_path):
        # Gray (saturation 0) first, so saturation sorting must move red up
        path = _make_two_color_image(tmp_path / "sat.png", (128, 128, 128), (255, 0, 0))
        result = analyzer.analyze_image(path, sort_by="saturation")
        assert [c.rgb for c in result.colors] == [(255, 0, 0), (128, 128, 128)]

    def test_sort_by_brightness_descending(self, analyzer, tmp_path):
        # Black (brightness 0) first, so brightness sorting must move white up
        path = _make_two_color_image(tmp_path / "bri.png", (0, 0, 0), (255, 255, 255))
        result = analyzer.analyze_image(path, sort_by="brightness")
        assert [c.rgb for c in result.colors] == [(255, 255, 255), (0, 0, 0)]

    def test_dominant_color_independent_of_sort(self, analyzer, tmp_path):
        # Green wins by frequency (80%) even though red sorts first by hue
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        for y in range(10):
            for x in range(2, 10):
                img.putpixel((x, y), (0, 255, 0))
        path = tmp_path / "mixed.png"
        img.save(path)
        result = analyzer.analyze_image(path, sort_by="hue")
        assert result.dominant_color == (0, 255, 0)
        assert result.colors[0].rgb == (255, 0, 0)


# ── image modes and input robustness ────────────────────────────────────────

class TestImageModes:
    def test_grayscale_image(self, analyzer, tmp_path):
        img = Image.new("L", (10, 10), color=200)
        path = tmp_path / "gray.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (200, 200, 200)

    def test_palette_image(self, analyzer, tmp_path):
        img = Image.new("P", (10, 10), color=0)
        img.putpalette([255, 0, 0] + [0, 0, 0] * 255)  # palette index 0 = red
        path = tmp_path / "palette.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (255, 0, 0)

    def test_la_image(self, analyzer, tmp_path):
        img = Image.new("LA", (10, 10), color=(200, 255))
        path = tmp_path / "la.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (200, 200, 200)

    def test_corrupt_file_returns_none(self, analyzer, tmp_path):
        path = tmp_path / "corrupt.png"
        path.write_bytes(b"not actually an image")
        assert analyzer.analyze_image(path) is None


# ── save_analysis edge cases ─────────────────────────────────────────────────

class TestSaveAnalysisEdgeCases:
    def test_input_base_mismatch_writes_flat(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        out = tmp_path / "out"
        analyzer.save_analysis(out, info, input_base=tmp_path / "elsewhere", file_path=red_image)
        assert (out / "red.png_analysis.txt").exists()

    def test_css_output_with_empty_palette(self, analyzer, fully_transparent_image, tmp_path):
        info = analyzer.analyze_image(fully_transparent_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        css = (tmp_path / "transparent.png_tokens.css").read_text()
        assert ":root {" in css
        assert "--color-dominant" not in css


# ── filename sanitization in generated files ─────────────────────────────────

class TestFilenameSanitization:
    @staticmethod
    def _info(filename, rgb=(255, 0, 0)):
        # Synthetic result: hostile names never touch the disk, keeping these
        # tests portable to platforms that forbid such filenames (Windows)
        color = ColorInfo(
            rgb=rgb,
            hex=ColorConverter.rgb_to_hex(rgb),
            cmyk=ColorConverter.rgb_to_cmyk(*rgb),
            weight=100.0,
            oklch=ColorConverter.rgb_to_oklch(rgb),
            harmonies={},
        )
        return ImageInfo(
            filename=filename,
            dimensions=(5, 5),
            format="PNG",
            colors=[color],
            dominant_color=rgb,
        )

    def test_newline_stripped_from_css_artifacts(self, analyzer, tmp_path):
        # A newline in the filename must not inject lines into generated
        # stylesheets or theme files
        info = self._info("x.png\ninjected: yes")
        analyzer.save_analysis(tmp_path, info, output_format="css")
        css_files = list(tmp_path.glob("x.png injected*_tokens.css"))
        theme_files = list(tmp_path.glob("x.png injected*_tailwind.css"))
        assert len(css_files) == 1 and len(theme_files) == 1
        for content in (css_files[0].read_text(), theme_files[0].read_text()):
            assert not any(line.strip() == "injected: yes" for line in content.split("\n"))

    def test_newline_stripped_from_txt_report(self, analyzer, tmp_path):
        # A newline in the filename must not forge extra report lines
        info = self._info("x\nDominant Color: RGB(9, 9, 9).png", rgb=(1, 2, 3))
        analyzer.save_analysis(tmp_path, info)
        reports = list(tmp_path.glob("x Dominant Color*_analysis.txt"))
        assert len(reports) == 1
        lines = reports[0].read_text().split("\n")
        assert not any(line.startswith("Dominant Color: RGB(9") for line in lines)
        assert any(line == "Dominant Color: RGB(1, 2, 3)" for line in lines)

    def test_comment_terminator_and_control_chars_stripped(self):
        # Filenames cannot contain '/', so */ is defense in depth; control
        # characters are reachable on POSIX filesystems
        from color_analysis_tool.exporters import _sanitize_display_name
        assert _sanitize_display_name("evil*/inject.png") == "evilinject.png"
        assert _sanitize_display_name("a\x07b\x1b.png") == "ab.png"
        assert _sanitize_display_name("plain.png") == "plain.png"

    def test_output_stem_unchanged_for_clean_names(self):
        # Normal filenames keep their familiar output names, no digest
        from color_analysis_tool.exporters import _safe_output_stem
        assert _safe_output_stem("photo.png") == "photo.png"

    def test_output_stem_collision_resistant(self, analyzer, tmp_path):
        # Regression: two files whose names sanitize identically must not
        # overwrite each other's reports
        for name in ("a\nb.png", "a b.png"):
            analyzer.save_analysis(tmp_path, self._info(name))
        reports = list(tmp_path.glob("a b.png*_analysis.txt"))
        assert len(reports) == 2
        assert reports[0].name != reports[1].name

    def test_output_stem_replaces_backslash(self, analyzer, tmp_path):
        # Backslash is legal in POSIX filenames but a separator on Windows
        analyzer.save_analysis(tmp_path, self._info("dir\\evil.png"))
        (produced,) = [p for p in tmp_path.glob("*_analysis.txt")]
        assert "\\" not in produced.name
        assert produced.name.startswith("dir-evil.png-")

    def test_output_stem_cannot_traverse(self, analyzer, tmp_path):
        # Synthetic ImageInfo filenames never touched a disk, so they can
        # carry separators; output paths must stay inside output_dir
        analyzer.save_analysis(tmp_path, self._info("../../outside.png"))
        analyzer.save_analysis(tmp_path, self._info("/abs/path.png"))
        produced = list(tmp_path.glob("*_analysis.txt"))
        assert len(produced) == 2
        for path in produced:
            assert path.parent == tmp_path
            assert "/" not in path.name and "\\" not in path.name

    def test_output_stem_replaces_windows_invalid_chars(self, analyzer, tmp_path):
        # A colon makes a name drive-relative on Windows and addresses NTFS
        # alternate data streams; it must not survive into the output name
        analyzer.save_analysis(tmp_path, self._info("C:escape.png"))
        analyzer.save_analysis(tmp_path, self._info("name:stream.png"))
        produced = list(tmp_path.glob("*_analysis.txt"))
        assert len(produced) == 2
        for path in produced:
            assert path.parent == tmp_path
            assert ":" not in path.name

    def test_non_utf8_filename_digest_does_not_raise(self):
        # Regression: POSIX filenames may carry non-UTF-8 bytes, surfaced as
        # surrogate escapes; os.fsencode round-trips them where strict UTF-8
        # encoding would raise UnicodeEncodeError and abort the batch
        from color_analysis_tool.exporters import _safe_output_stem
        name = os.fsdecode(b"bad-\xff.png")
        stem = _safe_output_stem(name)
        assert stem == _safe_output_stem(name)  # deterministic
        assert stem.startswith("bad-.png-")


# ── safety guard ──────────────────────────────────────────────────────────────

class TestDecompressionBombGuard:
    def test_max_image_pixels_is_set(self):
        # Importing the analyzer module must configure the Pillow limit
        import color_analysis_tool.analyzer  # noqa: F401
        assert Image.MAX_IMAGE_PIXELS == 178_956_970

    def test_oversized_image_returns_none(self, analyzer, red_image, monkeypatch):
        # DecompressionBombError is not an OSError subclass; without an
        # explicit catch it would abort batch processing on the first
        # oversized image instead of skipping it
        monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 10)
        assert analyzer.analyze_image(red_image) is None


# ── automatic palette sizing (max_colors="auto") ─────────────────────────────

class TestAutoPalette:
    def test_auto_bounds_high_color_image(self, analyzer, high_color_image):
        # 1024 unique colors exceeds the 256 threshold: auto must bound it
        result = analyzer.analyze_image(high_color_image)
        assert result is not None
        assert len(result.colors) <= 32
        assert result.dominant_color is not None

    def test_auto_preserves_low_color_image(self, analyzer, two_color_image):
        # Under the threshold, auto analyzes every unique color faithfully
        result = analyzer.analyze_image(two_color_image)
        assert len(result.colors) == 2
        assert abs(sum(c.weight for c in result.colors) - 100.0) < 0.1

    def test_zero_disables_palette_reduction(self, analyzer, high_color_image):
        # 0 is the explicit opt-out: unbounded palette
        result = analyzer.analyze_image(high_color_image, max_colors=0)
        assert len(result.colors) == 1024

    def test_invalid_string_raises(self, analyzer, red_image):
        with pytest.raises(ValueError, match="max_colors"):
            analyzer.analyze_image(red_image, max_colors="lots")

    def test_auto_threshold_boundary(self, analyzer, tmp_path):
        # Exactly 256 unique colors are kept faithful; 257 triggers the bound
        img = Image.new("RGB", (16, 16))
        for i in range(256):
            img.putpixel((i % 16, i // 16), (i, 0, 0))
        path = tmp_path / "exactly_256.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert len(result.colors) == 256

        img_over = Image.new("RGB", (16, 17))
        for i in range(256):
            img_over.putpixel((i % 16, i // 16), (i, 0, 0))
        for x in range(16):
            img_over.putpixel((x, 16), (255, 255, 255))
        path_over = tmp_path / "over_256.png"
        img_over.save(path_over)
        result_over = analyzer.analyze_image(path_over)
        assert len(result_over.colors) <= 32


# ── exporter output cap ──────────────────────────────────────────────────────

def _multi_color_info(n, filename="multi.png"):
    """Build a synthetic ImageInfo with n distinct colors."""
    # Encode the index across all three channels so every component
    # stays within 0-255 even for n above 256
    rgbs = [(i % 256, (i // 256) % 256, (i // 65536) % 256) for i in range(n)]
    cmyk_values = ColorConverter.rgb_to_cmyk_batch(rgbs)
    colors = [
        ColorInfo(
            rgb=rgb,
            hex=ColorConverter.rgb_to_hex(rgb),
            cmyk=cmyk,
            weight=round(100 / n, 2),
            oklch=ColorConverter.rgb_to_oklch(rgb),
            harmonies={},
        )
        for rgb, cmyk in zip(rgbs, cmyk_values)
    ]
    return ImageInfo(
        filename=filename,
        dimensions=(10, 10),
        format="PNG",
        colors=colors,
        dominant_color=(0, 0, 0),
    )


class TestOutputTruncation:
    def test_txt_note_and_cap(self, analyzer, tmp_path, monkeypatch):
        monkeypatch.setattr("color_analysis_tool.exporters.MAX_OUTPUT_COLORS", 2)
        analyzer.save_analysis(tmp_path, _multi_color_info(5))
        content = (tmp_path / "multi.png_analysis.txt").read_text()
        assert "truncated to the first 2 of 5 colors" in content
        assert content.count("Color #") == 2

    def test_json_truncated_from_key(self, analyzer, tmp_path, monkeypatch):
        monkeypatch.setattr("color_analysis_tool.exporters.MAX_OUTPUT_COLORS", 2)
        analyzer.save_analysis(tmp_path, _multi_color_info(5), output_format="json")
        data = json.loads((tmp_path / "multi.png_analysis.json").read_text())
        assert data["truncated_from"] == 5
        assert len(data["colors"]) == 2

    def test_json_no_key_when_under_cap(self, analyzer, tmp_path, monkeypatch):
        monkeypatch.setattr("color_analysis_tool.exporters.MAX_OUTPUT_COLORS", 10)
        analyzer.save_analysis(tmp_path, _multi_color_info(5), output_format="json")
        data = json.loads((tmp_path / "multi.png_analysis.json").read_text())
        assert "truncated_from" not in data
        assert len(data["colors"]) == 5

    def test_css_notes_and_cap(self, analyzer, tmp_path, monkeypatch):
        monkeypatch.setattr("color_analysis_tool.exporters.MAX_OUTPUT_COLORS", 2)
        analyzer.save_analysis(tmp_path, _multi_color_info(5), output_format="css")
        css = (tmp_path / "multi.png_tokens.css").read_text()
        theme = (tmp_path / "multi.png_tailwind.css").read_text()
        tokens = json.loads((tmp_path / "multi.png_tokens.json").read_text())
        assert "truncated to the first 2 of 5 colors" in css
        assert "truncated to the first 2 of 5 colors" in theme
        assert tokens["$metadata"]["truncated_from"] == 5
        # 2 capped colors (hex + oklch each) + dominant (hex + oklch)
        assert css.count("--color-") == 6

    def test_default_cap_applies_at_1000(self, analyzer, tmp_path):
        # The built-in 1000-color cap guards output without any patching
        analyzer.save_analysis(tmp_path, _multi_color_info(1200), output_format="json")
        data = json.loads((tmp_path / "multi.png_analysis.json").read_text())
        assert data["truncated_from"] == 1200
        assert len(data["colors"]) == 1000


# ── palette extractors (v2) ────────────────────────────────────────────────────

class TestExtractors:
    def test_default_extractor_is_perceptual(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        assert result.colors[0].rgb == (255, 0, 0)
        assert result.colors[0].weight == 100.0

    def test_perceptual_matches_legacy_on_low_color_image(self, analyzer, two_color_image):
        # Under the auto threshold both engines report the same exact weights
        perceptual = analyzer.analyze_image(two_color_image)
        legacy = analyzer.analyze_image(two_color_image, extractor="legacy")
        assert {c.rgb: c.weight for c in perceptual.colors} == {
            c.rgb: c.weight for c in legacy.colors
        }

    def test_perceptual_bounds_high_color_image(self, analyzer, high_color_image):
        # 1024 unique colors: the perceptual engine returns a bounded palette
        result = analyzer.analyze_image(high_color_image)
        assert result is not None
        assert 1 <= len(result.colors) <= 32
        assert result.dominant_color is not None

    def test_perceptual_is_deterministic(self, analyzer, high_color_image):
        first = analyzer.analyze_image(high_color_image)
        second = analyzer.analyze_image(high_color_image)
        assert [c.rgb for c in first.colors] == [c.rgb for c in second.colors]
        assert [c.weight for c in first.colors] == [c.weight for c in second.colors]

    def test_perceptual_weights_sum_to_100(self, analyzer, high_color_image):
        result = analyzer.analyze_image(high_color_image)
        assert abs(sum(c.weight for c in result.colors) - 100.0) < 0.5

    def test_dominant_is_heaviest_cluster(self, analyzer, tmp_path):
        # 80% green, 20% red: green must win regardless of clustering
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        for y in range(10):
            for x in range(2, 10):
                img.putpixel((x, y), (0, 255, 0))
        path = tmp_path / "dominant.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (0, 255, 0)

    def test_perceptual_max_colors_respected(self, analyzer, high_color_image):
        result = analyzer.analyze_image(high_color_image, max_colors=8)
        assert 1 <= len(result.colors) <= 8

    def test_legacy_extractor_keeps_v1_palette(self, analyzer, high_color_image):
        # v1 auto behavior: median-cut quantization to 32 colors
        result = analyzer.analyze_image(high_color_image, extractor="legacy")
        assert result is not None
        assert len(result.colors) <= 32

    def test_legacy_zero_disables_quantization(self, analyzer, high_color_image):
        result = analyzer.analyze_image(high_color_image, extractor="legacy", max_colors=0)
        assert len(result.colors) == 1024

    def test_invalid_extractor_raises(self, analyzer, red_image):
        with pytest.raises(ValueError, match="extractor"):
            analyzer.analyze_image(red_image, extractor="magic")

    def test_invalid_harmony_engine_raises(self, analyzer, red_image):
        with pytest.raises(ValueError, match="harmony_engine"):
            analyzer.analyze_image(red_image, harmony_engine="magic")

    def test_harmony_engine_oklch_default(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image)
        harmonies = result.colors[0].harmonies
        assert set(harmonies.keys()) == {"complementary", "analogous", "triadic", "tetradic"}
        comp = harmonies["complementary"][0]
        assert all(0 <= v <= 255 for v in comp)

    def test_harmony_engine_hsv_legacy(self, analyzer, red_image):
        result = analyzer.analyze_image(red_image, harmony_engine="hsv_legacy")
        assert result.colors[0].harmonies["complementary"] == [(0, 255, 255)]

    def test_custom_cmyk_profile_is_recorded(self, analyzer, red_image):
        result = analyzer.analyze_image(
            red_image,
            cmyk_profile="color_analysis_tool/profiles/ISOcoated_v2_eci.icc",
        )
        assert result.cmyk_profile == "ISOcoated_v2_eci.icc"


# ── v2 output labels ───────────────────────────────────────────────────────────

class TestOutputLabels:
    def test_txt_uses_weight_label(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "red.png_analysis.txt").read_text()
        assert "Weight: 100.0%" in content
        assert "Frequency" not in content

    def test_txt_labels_cmyk_profile(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "red.png_analysis.txt").read_text()
        assert "CMYK (FOGRA39 (ISO Coated v2))" in content

    def test_txt_contains_oklch(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "red.png_analysis.txt").read_text()
        assert "OKLCH: oklch(0.628 0.2577 29.2339)" in content

    def test_txt_contains_wcag_and_apca(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "red.png_analysis.txt").read_text()
        assert "Contrast on white: 4.0:1 (AA: no, AAA: no)" in content
        assert "Contrast on black: 5.25:1 (AA: yes, AAA: no)" in content
        assert "APCA Lc (experimental)" in content

    def test_css_contains_oklch_and_contrast_properties(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tokens.css").read_text()
        assert "--color-1-oklch: oklch(" in content
        assert "--color-1-contrast-on-white: 4.0;" in content
        assert "--color-1-contrast-on-black: 5.25;" in content
        assert "--color-dominant-oklch: oklch(" in content

    def test_tokens_json_extensions(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        data = json.loads((tmp_path / "red.png_tokens.json").read_text())
        entry = data["palette"]["color-1"]
        extensions = entry["$extensions"]["com.color-analysis-tool"]
        assert extensions["oklch"].startswith("oklch(")
        assert extensions["wcag"]["on_white"]["ratio"] == pytest.approx(4.0, abs=0.01)
        assert extensions["apca"]["status"] == "experimental"


# ── contrast data flow through outputs ─────────────────────────────────────────

class TestContrastFlowThroughOutputs:
    """The non-dominant color's vs_dominant comparison must reach every format."""

    def test_vs_dominant_in_txt(self, analyzer, two_color_image, tmp_path):
        info = analyzer.analyze_image(two_color_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "two_color.png_analysis.txt").read_text()
        assert "Contrast vs dominant: 2.15:1" in content

    def test_vs_dominant_in_json(self, analyzer, two_color_image, tmp_path):
        info = analyzer.analyze_image(two_color_image)
        analyzer.save_analysis(tmp_path, info, output_format="json")
        colors = json.loads((tmp_path / "two_color.png_analysis.json").read_text())["colors"]
        non_dominant = next(c for c in colors if c["rgb"] != list(info.dominant_color))
        vs_dominant = non_dominant["wcag"]["vs_dominant"]
        assert vs_dominant["ratio"] == pytest.approx(2.15, abs=0.01)
        assert set(vs_dominant.keys()) == {"ratio", "aa", "aaa"}

    def test_vs_dominant_in_tokens(self, analyzer, two_color_image, tmp_path):
        info = analyzer.analyze_image(two_color_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        data = json.loads((tmp_path / "two_color.png_tokens.json").read_text())
        entries = [
            t["$extensions"]["com.color-analysis-tool"]
            for k, t in data["palette"].items()
            if k != "color-dominant"
        ]
        assert any(e["wcag"]["vs_dominant"] is not None for e in entries)


class TestContrastNoneGuard:
    """A ColorInfo built without a contrast report (v1-style construction)
    must still render in every output format."""

    def test_txt_renders_without_contrast(self, analyzer, tmp_path):
        analyzer.save_analysis(tmp_path, _multi_color_info(3))
        content = (tmp_path / "multi.png_analysis.txt").read_text()
        assert "Contrast" not in content
        assert "Weight:" in content

    def test_json_renders_null_contrast(self, analyzer, tmp_path):
        analyzer.save_analysis(tmp_path, _multi_color_info(3), output_format="json")
        data = json.loads((tmp_path / "multi.png_analysis.json").read_text())
        assert data["colors"][0]["wcag"] is None
        assert data["colors"][0]["apca"] is None

    def test_css_renders_without_contrast_properties(self, analyzer, tmp_path):
        analyzer.save_analysis(tmp_path, _multi_color_info(3), output_format="css")
        css = (tmp_path / "multi.png_tokens.css").read_text()
        assert "--color-1:" in css
        assert "contrast-on" not in css
        tokens = json.loads((tmp_path / "multi.png_tokens.json").read_text())
        # OKLCh data survives even without a contrast report
        extensions = tokens["palette"]["color-1"]["$extensions"]["com.color-analysis-tool"]
        assert "oklch" in extensions
        assert "wcag" not in extensions
        assert "apca" not in extensions


# ── error contracts and engine branches ────────────────────────────────────────

class TestErrorContracts:
    def test_bad_cmyk_profile_path_raises(self, analyzer, red_image):
        with pytest.raises(OSError, match="cannot open profile"):
            analyzer.analyze_image(red_image, cmyk_profile="/nonexistent/profile.icc")

    def test_imagecms_missing_raises_runtime(self, monkeypatch):
        monkeypatch.setattr("color_analysis_tool.analyzer._HAS_IMAGECMS", False)
        with pytest.raises(RuntimeError, match="LittleCMS"):
            ColorConverter.rgb_to_cmyk(1, 2, 3)

    def test_device_naive_works_without_imagecms(self, monkeypatch):
        # The naive formula must not depend on LittleCMS
        monkeypatch.setattr("color_analysis_tool.analyzer._HAS_IMAGECMS", False)
        assert ColorConverter.rgb_to_cmyk(255, 0, 0, method="device_naive") == (0, 100, 100, 0)

    def test_legacy_extractor_with_explicit_colors(self, analyzer, high_color_image):
        # Legacy pipeline with -c N: median-cut quantization branch
        result = analyzer.analyze_image(high_color_image, extractor="legacy", max_colors=16)
        assert result is not None
        assert 1 <= len(result.colors) <= 16
        assert abs(sum(c.weight for c in result.colors) - 100.0) < 0.5


# ── public-behavior regression locks ───────────────────────────────────────────

class TestBehaviorLocks:
    def test_dominant_tie_breaks_deterministically(self, analyzer, tmp_path):
        # Four equal quadrants: the dominant color is deterministic
        img = Image.new("RGB", (10, 10), (255, 255, 255))
        for y in range(5):
            for x in range(5, 10):
                img.putpixel((x, y), (230, 57, 70))
        for y in range(5, 10):
            for x in range(5):
                img.putpixel((x, y), (42, 157, 143))
            for x in range(5, 10):
                img.putpixel((x, y), (58, 123, 213))
        path = tmp_path / "quadrants.png"
        img.save(path)
        first = analyzer.analyze_image(path)
        second = analyzer.analyze_image(path)
        assert first.dominant_color == second.dominant_color
        assert first.dominant_color == (42, 157, 143)

    def test_dominant_tie_break_independent_of_sort(self, analyzer, tmp_path):
        # Regression: on a weight tie, max() used to scan the criterion-
        # sorted list, so the dominant color changed with sort_by. It is
        # now resolved on the deterministic weight order before re-sorting.
        path = _make_two_color_image(tmp_path / "tie.png", (255, 0, 0), (0, 0, 255))
        for criterion in ("frequency", "hue", "saturation", "brightness"):
            result = analyzer.analyze_image(path, sort_by=criterion)
            assert result.dominant_color == (0, 0, 255)

    def test_tiff_image(self, analyzer, tmp_path):
        img = Image.new("RGB", (10, 10), color=(18, 52, 86))
        path = tmp_path / "photo.tiff"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (18, 52, 86)
        assert result.format == "TIFF"

    def test_webp_image(self, analyzer, tmp_path):
        img = Image.new("RGB", (10, 10), color=(18, 52, 86))
        path = tmp_path / "photo.webp"
        img.save(path, lossless=True)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (18, 52, 86)
        assert result.format == "WEBP"

    def test_batch_forwards_engines_to_every_output(self, analyzer, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        Image.new("RGB", (5, 5), color=(255, 0, 0)).save(input_dir / "a.png")
        Image.new("RGB", (5, 5), color=(0, 255, 0)).save(input_dir / "b.png")

        output_dir = tmp_path / "output"
        analyzer.batch_process(
            input_dir,
            output_dir,
            output_format="json",
            extractor="legacy",
            harmony_engine="hsv_legacy",
            cmyk_profile="color_analysis_tool/profiles/ISOcoated_v2_eci.icc",
        )
        for name in ("a", "b"):
            data = json.loads((output_dir / f"{name}.png_analysis.json").read_text())
            assert data["cmyk_profile"] == "ISOcoated_v2_eci.icc"
            # hsv_legacy harmony for red: cyan; for green: magenta
            assert data["colors"][0]["harmonies"]["complementary"] in (
                [[0, 255, 255]],
                [[255, 0, 255]],
            )


# ── branch coverage gap closures ───────────────────────────────────────────────

class TestBranchCoverageGaps:
    """Each test below takes the previously untaken exit of a decision point."""

    def test_legacy_probe_skips_transparent_pixels(self, analyzer, mixed_alpha_image):
        # The legacy auto probe counts unique visible colors; its
        # alpha <= 0 branch only fires when the probe walks a transparent
        # pixel, which opaque test images never do
        result = analyzer.analyze_image(mixed_alpha_image, extractor="legacy")
        assert result.dominant_color == (255, 0, 0)
        assert len(result.colors) == 1

    def test_batch_skips_unanalyzable_file(self, analyzer, tmp_path):
        # A corrupt image returns None from analyze_image inside a batch;
        # the batch must skip it and still process the rest
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        Image.new("RGB", (5, 5), color=(255, 0, 0)).save(input_dir / "ok.png")
        (input_dir / "corrupt.png").write_bytes(b"not actually an image")

        output_dir = tmp_path / "output"
        analyzer.batch_process(input_dir, output_dir)
        assert (output_dir / "ok.png_analysis.txt").exists()
        assert not (output_dir / "corrupt.png_analysis.txt").exists()

    def test_txt_report_without_dominant_color(self, analyzer, fully_transparent_image, tmp_path):
        # A fully transparent image has no dominant color; the txt report
        # must omit the Dominant Color line rather than write garbage
        info = analyzer.analyze_image(fully_transparent_image)
        analyzer.save_analysis(tmp_path, info)
        content = (tmp_path / "transparent.png_analysis.txt").read_text()
        assert "Dominant Color" not in content
