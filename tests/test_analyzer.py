"""Tests for ImageAnalyzer using synthetic in-memory images."""

import json

import pytest
from PIL import Image

from color_analysis_tool.analyzer import ColorInfo, ImageAnalyzer, ImageInfo


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
        assert color.frequency == 100.0

    def test_two_colors_detected(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image)
        rgbs = [c.rgb for c in result.colors]
        assert (255, 0, 0) in rgbs
        assert (0, 0, 255) in rgbs

    def test_frequencies_sum_to_100(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image)
        total = sum(c.frequency for c in result.colors)
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

    def test_missing_file_returns_none(self, analyzer, tmp_path):
        result = analyzer.analyze_image(tmp_path / "nonexistent.png")
        assert result is None

    def test_max_colors_quantization(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image, max_colors=2)
        assert result is not None
        assert len(result.colors) <= 2

    def test_sort_by_frequency(self, analyzer, two_color_image):
        result = analyzer.analyze_image(two_color_image, sort_by="frequency")
        freqs = [c.frequency for c in result.colors]
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
        assert "frequency" in color
        assert "harmonies" in color


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
        assert (tmp_path / "red.png_tailwind.js").exists()

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

    def test_tailwind_contains_module_exports(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tailwind.js").read_text()
        assert "module.exports" in content
        assert "#ff0000" in content

    def test_tailwind_contains_extend_colors(self, analyzer, red_image, tmp_path):
        info = analyzer.analyze_image(red_image)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "red.png_tailwind.js").read_text()
        assert "colors" in content
        assert "extend" in content

    def test_batch_css_output(self, analyzer, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        img = Image.new("RGB", (5, 5), color=(0, 128, 255))
        img.save(input_dir / "img.png")

        output_dir = tmp_path / "output"
        analyzer.batch_process(input_dir, output_dir, output_format="css")

        assert (output_dir / "img.png_tokens.css").exists()
        assert (output_dir / "img.png_tokens.json").exists()
        assert (output_dir / "img.png_tailwind.js").exists()

    def test_tailwind_key_sanitized(self, analyzer, tmp_path):
        img = Image.new("RGB", (5, 5), color=(255, 0, 0))
        path = tmp_path / "my image 01.png"
        img.save(path)
        info = analyzer.analyze_image(path)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        content = (tmp_path / "my image 01.png_tailwind.js").read_text()
        assert "'my-image-01-png':" in content


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
        assert result.colors[0].frequency == 100.0

    def test_partially_transparent_pixels_are_visible(self, analyzer, tmp_path):
        # Any pixel with alpha > 0 counts as visible
        img = Image.new("RGBA", (10, 10), color=(0, 0, 255, 1))
        path = tmp_path / "barely_visible.png"
        img.save(path)
        result = analyzer.analyze_image(path)
        assert result.dominant_color == (0, 0, 255)
        assert result.colors[0].frequency == 100.0

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

    def test_quantization_preserves_alpha(self, analyzer, mixed_alpha_image):
        # Regression: --colors N must not turn transparent pixels opaque black
        result = analyzer.analyze_image(mixed_alpha_image, max_colors=4)
        assert result.dominant_color == (255, 0, 0)
        assert len(result.colors) == 1
        assert result.colors[0].frequency == 100.0

    def test_quantized_fully_transparent_image(self, analyzer, fully_transparent_image):
        result = analyzer.analyze_image(fully_transparent_image, max_colors=4)
        assert result is not None
        assert result.colors == []
        assert result.dominant_color is None

    def test_transparent_payload_does_not_shift_palette(self, analyzer, tmp_path):
        # Regression: noisy RGB payloads under fully transparent pixels must
        # not consume palette slots or blend visible colors during quantization
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
        result = analyzer.analyze_image(path, max_colors=5)
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
        assert result.colors[0].frequency == 100.0
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
    def test_newline_stripped_from_css_and_js(self, analyzer, tmp_path):
        # A newline in the filename must not inject lines into generated
        # stylesheets or config snippets
        path = tmp_path / "x.png\ninjected: yes"
        Image.new("RGB", (5, 5), color=(255, 0, 0)).save(path, format="PNG")
        info = analyzer.analyze_image(path)
        analyzer.save_analysis(tmp_path, info, output_format="css")
        css_files = list(tmp_path.glob("x.png injected*_tokens.css"))
        js_files = list(tmp_path.glob("x.png injected*_tailwind.js"))
        assert len(css_files) == 1 and len(js_files) == 1
        for content in (css_files[0].read_text(), js_files[0].read_text()):
            assert not any(line.strip() == "injected: yes" for line in content.split("\n"))

    def test_newline_stripped_from_txt_report(self, analyzer, tmp_path):
        # A newline in the filename must not forge extra report lines
        path = tmp_path / "x\nDominant Color: RGB(9, 9, 9).png"
        Image.new("RGB", (5, 5), color=(1, 2, 3)).save(path)
        info = analyzer.analyze_image(path)
        analyzer.save_analysis(tmp_path, info)
        reports = list(tmp_path.glob("x Dominant Color*_analysis.txt"))
        assert len(reports) == 1
        lines = reports[0].read_text().split("\n")
        assert not any(line.startswith("Dominant Color: RGB(9") for line in lines)
        assert any(line == "Dominant Color: RGB(1, 2, 3)" for line in lines)

    def test_comment_terminator_and_control_chars_stripped(self):
        # Filenames cannot contain '/', so */ is defense in depth; control
        # characters are reachable on POSIX filesystems
        from color_analysis_tool.analyzer import _sanitize_display_name
        assert _sanitize_display_name("evil*/inject.png") == "evilinject.png"
        assert _sanitize_display_name("a\x07b\x1b.png") == "ab.png"
        assert _sanitize_display_name("plain.png") == "plain.png"

    def test_output_stem_unchanged_for_clean_names(self):
        # Normal filenames keep their familiar output names, no digest
        from color_analysis_tool.analyzer import _safe_output_stem
        assert _safe_output_stem("photo.png") == "photo.png"

    def test_output_stem_collision_resistant(self, analyzer, tmp_path):
        # Regression: two files whose names sanitize identically must not
        # overwrite each other's reports
        for name, color in [("a\nb.png", (255, 0, 0)), ("a b.png", (0, 0, 255))]:
            Image.new("RGB", (5, 5), color=color).save(tmp_path / name, format="PNG")
        out = tmp_path / "out"
        for name in ("a\nb.png", "a b.png"):
            info = analyzer.analyze_image(tmp_path / name)
            analyzer.save_analysis(out, info)
        reports = list(out.glob("a b.png*_analysis.txt"))
        assert len(reports) == 2
        assert reports[0].name != reports[1].name

    def test_output_stem_replaces_backslash(self, analyzer, tmp_path):
        # Backslash is legal in POSIX filenames but a separator on Windows
        path = tmp_path / "dir\\evil.png"
        Image.new("RGB", (5, 5), color=(1, 2, 3)).save(path, format="PNG")
        info = analyzer.analyze_image(path)
        analyzer.save_analysis(tmp_path, info)
        (produced,) = [p for p in tmp_path.glob("*_analysis.txt")]
        assert "\\" not in produced.name
        assert produced.name.startswith("dir-evil.png-")


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
