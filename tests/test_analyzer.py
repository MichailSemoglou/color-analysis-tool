"""Tests for ImageAnalyzer using synthetic in-memory images."""

import json
import pytest
from PIL import Image

from color_analysis_tool.analyzer import ImageAnalyzer, ImageInfo, ColorInfo


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
