"""Tests for the command-line interface (cli.py).

CLI tests invoke main() with monkeypatched sys.argv and assert on
SystemExit codes and produced files, covering argument parsing, output
format selection, batch mode, and error paths.
"""

import json

import pytest
from PIL import Image

from color_analysis_tool.analyzer import ImageAnalyzer
from color_analysis_tool.cli import main

from .helpers import bundled_profile_path


@pytest.fixture
def red_image(tmp_path):
    """A 5x5 solid red PNG."""
    img = Image.new("RGB", (5, 5), color=(255, 0, 0))
    path = tmp_path / "red.png"
    img.save(path)
    return path


@pytest.fixture
def image_dir(tmp_path):
    """A directory with two images and one non-image file."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    Image.new("RGB", (5, 5), color=(255, 0, 0)).save(input_dir / "a.png")
    Image.new("RGB", (5, 5), color=(0, 255, 0)).save(input_dir / "b.png")
    (input_dir / "notes.txt").write_text("not an image")
    return input_dir


def run_cli(monkeypatch, *args):
    """Invoke main() with the given command-line arguments."""
    monkeypatch.setattr("sys.argv", ["color-analysis", *(str(a) for a in args)])
    main()


# --- basic invocation ------------------------------------------------------


class TestBasicInvocation:
    def test_version_flag(self, monkeypatch, capsys):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, "--version")
        assert exc_info.value.code == 0
        assert "color-analysis" in capsys.readouterr().out

    def test_single_file_txt(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out)
        assert (out / "red.png_analysis.txt").exists()

    def test_single_file_json(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "-f", "json")
        data = json.loads((out / "red.png_analysis.json").read_text())
        assert data["dominant_color"] == [255, 0, 0]

    def test_single_file_css(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "-f", "css")
        assert (out / "red.png_tokens.css").exists()
        assert (out / "red.png_tokens.json").exists()
        assert (out / "red.png_tailwind.css").exists()

    def test_sort_option_recorded(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "-s", "hue")
        content = (out / "red.png_analysis.txt").read_text()
        assert "sorted by hue" in content

    def test_colors_flag(self, monkeypatch, tmp_path):
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        for y in range(5, 10):
            for x in range(10):
                img.putpixel((x, y), (0, 0, 255))
        path = tmp_path / "two.png"
        img.save(path)
        out = tmp_path / "out"
        run_cli(monkeypatch, path, out, "-c", "2", "-f", "json")
        data = json.loads((out / "two.png_analysis.json").read_text())
        assert len(data["colors"]) <= 2

    def test_colors_auto_accepted(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "-c", "auto")
        assert (out / "red.png_analysis.txt").exists()

    def test_colors_invalid_string_rejected(self, monkeypatch, red_image, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out", "-c", "many")
        assert exc_info.value.code == 2  # argparse parser.error

    def test_default_is_auto_and_bounded(self, monkeypatch, tmp_path):
        # No -c flag on a 1024-color image: auto must bound the palette
        img = Image.new("RGB", (32, 32))
        for i in range(1024):
            img.putpixel((i % 32, i // 32), (i % 256, i // 256, (i * 7) % 256))
        path = tmp_path / "colorful.png"
        img.save(path)
        out = tmp_path / "out"
        run_cli(monkeypatch, path, out, "-f", "json")
        data = json.loads((out / "colorful.png_analysis.json").read_text())
        assert len(data["colors"]) <= 32

    def test_verbose_flag(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "-v")
        assert (out / "red.png_analysis.txt").exists()


# --- batch mode ------------------------------------------------------------


class TestBatchMode:
    def test_directory_batch(self, monkeypatch, image_dir, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, image_dir, out)
        assert (out / "a.png_analysis.txt").exists()
        assert (out / "b.png_analysis.txt").exists()

    def test_non_image_files_are_skipped(self, monkeypatch, image_dir, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, image_dir, out)
        assert not (out / "notes.txt_analysis.txt").exists()

    def test_batch_json(self, monkeypatch, image_dir, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, image_dir, out, "-f", "json")
        assert (out / "a.png_analysis.json").exists()
        assert (out / "b.png_analysis.json").exists()


# --- error paths and exit codes --------------------------------------------


class TestErrorPaths:
    def test_invalid_input_path_exits_1(self, monkeypatch, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, tmp_path / "missing.png", tmp_path / "out")
        assert exc_info.value.code == 1

    def test_unanalyzable_file_exits_1(self, monkeypatch, tmp_path):
        bad = tmp_path / "broken.png"
        bad.write_bytes(b"this is not an image")
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, bad, tmp_path / "out")
        assert exc_info.value.code == 1

    def test_negative_colors_rejected(self, monkeypatch, red_image, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out", "-c", "-1")
        assert exc_info.value.code == 2  # argparse parser.error

    def test_invalid_format_rejected(self, monkeypatch, red_image, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out", "-f", "xml")
        assert exc_info.value.code == 2  # argparse choices validation

    def test_colors_above_256_rejected(self, monkeypatch, red_image, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out", "-c", "300")
        assert exc_info.value.code == 2  # argparse parser.error

    def test_keyboard_interrupt_exits_0(self, monkeypatch, red_image, tmp_path):
        def raise_interrupt(*args, **kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(ImageAnalyzer, "analyze_image", raise_interrupt)
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out")
        assert exc_info.value.code == 0

    def test_unexpected_exception_exits_1(self, monkeypatch, red_image, tmp_path):
        def raise_error(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(ImageAnalyzer, "analyze_image", raise_error)
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out")
        assert exc_info.value.code == 1

    def test_nonexistent_input_exits_1(self, monkeypatch, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, tmp_path / "does-not-exist.png", tmp_path / "out")
        assert exc_info.value.code == 1

    def test_get_version_fallback(self, monkeypatch):
        import color_analysis_tool
        from color_analysis_tool.cli import _get_version

        monkeypatch.delattr(color_analysis_tool, "__version__")
        assert _get_version() == "unknown"

    def test_module_invocation(self, monkeypatch, capsys):
        # Running the module as __main__ exercises the __main__ guard;
        # drop the cached module first so runpy executes it fresh
        import runpy
        import sys

        monkeypatch.delitem(sys.modules, "color_analysis_tool.cli", raising=False)
        monkeypatch.setattr("sys.argv", ["color-analysis", "--version"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("color_analysis_tool.cli", run_name="__main__")
        assert exc_info.value.code == 0
        assert "color-analysis" in capsys.readouterr().out

    def test_deterministic_json_on_high_color_image(self, monkeypatch, tmp_path):
        # 1024 unique colors exercise the clustering path through the CLI;
        # two runs must produce byte-identical JSON (reproducibility claim)
        img = Image.new("RGB", (32, 32))
        for i in range(1024):
            img.putpixel((i % 32, i // 32), (i % 256, i // 256, (i * 7) % 256))
        path = tmp_path / "high_color.png"
        img.save(path)

        out_a, out_b = tmp_path / "out_a", tmp_path / "out_b"
        run_cli(monkeypatch, path, out_a, "-f", "json")
        run_cli(monkeypatch, path, out_b, "-f", "json")
        assert (out_a / "high_color.png_analysis.json").read_bytes() == (
            out_b / "high_color.png_analysis.json"
        ).read_bytes()


# --- v2 engine flags ----------------------------------------------------------


class TestEngineFlags:
    def test_legacy_extractor_flag(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "--extractor", "legacy")
        assert (out / "red.png_analysis.txt").exists()

    def test_invalid_extractor_rejected(self, monkeypatch, red_image, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out", "--extractor", "magic")
        assert exc_info.value.code == 2  # argparse choices validation

    def test_harmony_engine_flag(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "-f", "json", "--harmony-engine", "hsv_legacy")
        data = json.loads((out / "red.png_analysis.json").read_text())
        assert data["colors"][0]["harmonies"]["complementary"] == [[0, 255, 255]]

    def test_invalid_harmony_engine_rejected(self, monkeypatch, red_image, tmp_path):
        with pytest.raises(SystemExit) as exc_info:
            run_cli(monkeypatch, red_image, tmp_path / "out", "--harmony-engine", "magic")
        assert exc_info.value.code == 2

    def test_default_harmonies_are_oklch(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(monkeypatch, red_image, out, "-f", "json")
        data = json.loads((out / "red.png_analysis.json").read_text())
        # The OKLCh complement of red is not the HSV cyan
        assert data["colors"][0]["harmonies"]["complementary"] != [[0, 255, 255]]

    def test_cmyk_profile_flag(self, monkeypatch, red_image, tmp_path):
        out = tmp_path / "out"
        run_cli(
            monkeypatch,
            red_image,
            out,
            "-f",
            "json",
            "--cmyk-profile",
            bundled_profile_path(),
        )
        data = json.loads((out / "red.png_analysis.json").read_text())
        assert data["cmyk_profile"] == "ISOcoated_v2_eci.icc"

    def test_batch_with_engine_flags(self, monkeypatch, image_dir, tmp_path):
        out = tmp_path / "out"
        run_cli(
            monkeypatch,
            image_dir,
            out,
            "--extractor",
            "legacy",
            "--harmony-engine",
            "hsv_legacy",
        )
        assert (out / "a.png_analysis.txt").exists()
        assert (out / "b.png_analysis.txt").exists()
