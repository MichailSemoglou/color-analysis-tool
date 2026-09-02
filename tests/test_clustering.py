"""Tests for the perceptual clustering engine."""

import random

import pytest

from color_analysis_tool.clustering import (
    SAMPLE_CAP,
    Cluster,
    _assign_all,
    _centroid_to_rgb,
    _fit_kmeans,
    _init_kmeans_plus_plus,
    _merge_near_duplicates,
    _subsample,
    extract_palette,
)
from color_analysis_tool.color_spaces import (
    oklab_to_oklch,
    oklab_to_rgb,
    oklch_to_oklab,
    rgb_to_oklab,
    rgb_to_oklch,
)


def _spread_colors(n):
    """n unique colors, deterministic."""
    return {(i % 256, (i // 256) % 256, (i * 7) % 256): (i % 50) + 1 for i in range(n)}


class TestExactPath:
    def test_fewer_unique_than_k_returns_exact_colors(self):
        counts = {(255, 0, 0): 50, (0, 0, 255): 50}
        clusters = extract_palette(counts, k=8)
        assert sorted(c.rgb for c in clusters) == [(0, 0, 255), (255, 0, 0)]
        assert all(c.weight == 50.0 for c in clusters)

    def test_single_color(self):
        clusters = extract_palette({(255, 0, 0): 100}, k=4)
        assert len(clusters) == 1
        assert clusters[0].rgb == (255, 0, 0)
        assert clusters[0].weight == 100.0

    def test_sorted_by_weight_descending(self):
        counts = {(255, 0, 0): 10, (0, 255, 0): 70, (0, 0, 255): 20}
        clusters = extract_palette(counts, k=3)
        assert [c.rgb for c in clusters] == [(0, 255, 0), (0, 0, 255), (255, 0, 0)]
        assert [c.weight for c in clusters] == [70.0, 20.0, 10.0]

    def test_empty_counts(self):
        assert extract_palette({}, k=4) == []

    def test_k_must_be_positive(self):
        with pytest.raises(ValueError, match="k must be at least 1"):
            extract_palette({(255, 0, 0): 1}, k=0)


class TestClusteringPath:
    def test_two_color_groups(self):
        # 300 red-dominant and 300 blue-dominant unique colors
        counts = {}
        for i in range(300):
            counts[(255, i % 30, i // 10)] = 10
            counts[(i % 30, i // 10, 255)] = 10
        clusters = extract_palette(counts, k=2)
        assert len(clusters) == 2
        assert clusters[0].weight == pytest.approx(50.0, abs=1.0)
        assert clusters[1].weight == pytest.approx(50.0, abs=1.0)
        reds = [c for c in clusters if c.rgb[0] > 200]
        blues = [c for c in clusters if c.rgb[2] > 200]
        assert len(reds) == 1 and len(blues) == 1

    def test_deterministic_same_seed(self):
        counts = _spread_colors(3000)
        first = extract_palette(counts, k=8)
        second = extract_palette(counts, k=8)
        assert first == second

    def test_weights_sum_to_100(self):
        counts = _spread_colors(3000)
        total = sum(c.weight for c in extract_palette(counts, k=8))
        assert total == pytest.approx(100.0, abs=0.5)

    def test_never_more_clusters_than_k(self):
        counts = _spread_colors(3000)
        assert len(extract_palette(counts, k=8)) <= 8

    def test_subsample_path_is_deterministic(self):
        counts = _spread_colors(5000)  # above SAMPLE_CAP
        assert len(counts) > SAMPLE_CAP
        first = extract_palette(counts, k=4)
        second = extract_palette(counts, k=4)
        assert first == second
        assert 1 <= len(first) <= 4

    def test_returns_cluster_dataclass(self):
        clusters = extract_palette(_spread_colors(3000), k=4)
        assert all(isinstance(c, Cluster) for c in clusters)


class TestSubsample:
    def test_deterministic(self):
        items = [((i % 256, i // 256, 0), i + 1) for i in range(5000)]
        first = _subsample(items, SAMPLE_CAP, random.Random(0))
        second = _subsample(items, SAMPLE_CAP, random.Random(0))
        assert first == second

    def test_capped(self):
        items = [((i % 256, i // 256, 0), 1) for i in range(5000)]
        assert len(_subsample(items, SAMPLE_CAP, random.Random(0))) == SAMPLE_CAP

    def test_below_cap_unchanged(self):
        items = [((i, 0, 0), 1) for i in range(10)]
        assert _subsample(items, SAMPLE_CAP, random.Random(0)) == items


class TestMergeNearDuplicates:
    def test_merges_close_colors(self):
        red = rgb_to_oklab((255, 0, 0))
        near_red = rgb_to_oklab((254, 2, 2))
        blue = rgb_to_oklab((0, 0, 255))
        centroids, counts = _merge_near_duplicates([red, near_red, blue], [100, 50, 100])
        assert len(centroids) == 2
        assert sorted(counts, reverse=True) == [150, 100]

    def test_heavier_cluster_absorbs(self):
        red = rgb_to_oklab((255, 0, 0))
        near_red = rgb_to_oklab((254, 2, 2))
        centroids, counts = _merge_near_duplicates([red, near_red], [100, 50])
        assert len(centroids) == 1
        expected = tuple((100 * red[i] + 50 * near_red[i]) / 150 for i in range(3))
        assert centroids[0] == pytest.approx(expected, abs=1e-9)
        assert counts == [150]

    def test_distant_colors_not_merged(self):
        red = rgb_to_oklab((255, 0, 0))
        blue = rgb_to_oklab((0, 0, 255))
        centroids, counts = _merge_near_duplicates([red, blue], [100, 100])
        assert len(centroids) == 2
        assert counts == [100, 100]

    def test_merge_chain_settles(self):
        # Three colors in a close chain: each pair within the threshold
        base = rgb_to_oklab((200, 100, 50))
        step1 = rgb_to_oklab((201, 101, 51))
        step2 = rgb_to_oklab((202, 102, 52))
        far = rgb_to_oklab((0, 0, 200))
        centroids, counts = _merge_near_duplicates([base, step1, step2, far], [10, 20, 30, 100])
        assert len(centroids) == 2
        assert sorted(counts, reverse=True) == [100, 60]


class TestDegenerateClusteringPaths:
    """Failure-mode branches that valid images almost never reach."""

    def test_init_pads_when_all_points_identical(self):
        # One distinct color with k > 1: D^2 weights are all zero, so the
        # seeding loop pads with the first point instead of choosing
        point = rgb_to_oklab((255, 0, 0))
        centroids = _init_kmeans_plus_plus(
            [point, point, point], [1, 1, 1], k=3, rng=random.Random(0)
        )
        assert centroids == [point, point, point]

    def test_empty_cluster_is_reseeded(self):
        # Two distinct points with k=3: the duplicate centroid gets no
        # assignments and must be reseeded at the farthest point
        red = rgb_to_oklab((255, 0, 0))
        blue = rgb_to_oklab((0, 0, 255))
        points, weights = [red, red, blue], [10, 10, 1]
        centroids = _fit_kmeans(points, weights, k=3, rng=random.Random(0))
        assert len(centroids) == 3
        # Reseeding is deterministic
        assert _fit_kmeans(points, weights, k=3, rng=random.Random(0)) == centroids

    def test_assign_all_drops_orphan_centroid(self):
        # A centroid nothing assigns to must not produce an empty cluster
        items = [((255, 0, 0), 10)]
        centroids = [rgb_to_oklab((255, 0, 0)), rgb_to_oklab((0, 0, 255))]
        new_centroids, counts = _assign_all(items, centroids)
        assert len(new_centroids) == 1
        assert counts == [10]

    def test_iteration_cap_exhausts_without_convergence(self, monkeypatch):
        # With the iteration cap forced to 1 and a point that still moves a
        # centroid, the loop exits by exhaustion instead of the convergence
        # break
        monkeypatch.setattr("color_analysis_tool.clustering.MAX_ITERATIONS", 1)
        points = [
            rgb_to_oklab((255, 0, 0)),
            rgb_to_oklab((0, 255, 0)),
            rgb_to_oklab((0, 0, 255)),
        ]
        centroids = _fit_kmeans(points, [1, 1, 1], k=2, rng=random.Random(0))
        assert len(centroids) == 2


class TestCentroidToRgb:
    def test_in_gamut_centroid_round_trips(self):
        centroid = rgb_to_oklab((42, 157, 143))
        assert _centroid_to_rgb(centroid) == (42, 157, 143)

    def test_out_of_gamut_centroid_preserves_hue_and_lightness(self):
        # oklch(0.65, 0.5, 140) is far outside sRGB; clipping would shift
        # the hue, chroma reduction keeps it
        centroid = oklch_to_oklab((0.65, 0.5, 140.0))
        lightness, _, hue = rgb_to_oklch(_centroid_to_rgb(centroid))
        assert lightness == pytest.approx(0.65, abs=0.02)
        assert hue == pytest.approx(140.0, abs=1.0)


class TestExtractPaletteGamutMapping:
    def test_out_of_gamut_centroid_is_mapped_not_clipped(self):
        # A 50/50 mix of white and a saturated red has an OKLab mean
        # outside the sRGB gamut; with k=1 that mean is the centroid
        counts = {(255, 255, 255): 50, (255, 0, 54): 50}
        clusters = extract_palette(counts, k=1)
        assert len(clusters) == 1
        lab_a = rgb_to_oklab((255, 255, 255))
        lab_b = rgb_to_oklab((255, 0, 54))
        centroid = tuple((x + y) / 2 for x, y in zip(lab_a, lab_b))
        assert oklab_to_rgb(centroid) != clusters[0].rgb  # clipping would differ
        want_lightness, _, want_hue = oklab_to_oklch(centroid)
        lightness, _, hue = rgb_to_oklch(clusters[0].rgb)
        assert lightness == pytest.approx(want_lightness, abs=0.02)
        assert hue == pytest.approx(want_hue, abs=1.0)
