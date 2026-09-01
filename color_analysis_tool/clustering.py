"""Perceptual palette extraction: deterministic k-means++ in OKLab.

This is the v2 palette engine. Unique visible colors (weighted by pixel
count) are clustered with k-means++ in OKLab, the approximately uniform
perceptual space of Ottosson (2020). Three properties make the output
suitable for reproducible research:

- Deterministic: a fixed seed drives both the subsampling of high-color
  images and the k-means++ initialization, so repeated runs on the same
  image produce byte-identical palettes.
- Coverage-weighted: cluster weights are the exact share of visible
  pixels assigned to each cluster, computed over every unique color,
  not over the subsample used for fitting.
- Perceptually deduplicated: clusters closer than CIEDE2000
  MERGE_DELTA_E are merged, per the just-noticeable-difference
  literature (Mahy et al. 1994; CIE 142-2001).

Reference:
- Arthur, D., & Vassilvitskii, S. (2007). k-means++: The advantages of
  careful seeding. In *Proceedings of the Eighteenth Annual ACM-SIAM
  Symposium on Discrete Algorithms (SODA '07)* (pp. 1027-1035). Society
  for Industrial and Applied Mathematics.
"""

import logging
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .color_spaces import RGB, OKLab, delta_e_ciede2000, oklab_to_lab, oklab_to_rgb, rgb_to_oklab

logger = logging.getLogger(__name__)

# Fixed seed for reproducible subsampling and k-means++ initialization
KMEANS_SEED = 0

# Working-set cap: images with more unique visible colors are reduced to
# a weighted subsample before fitting (Efraimidis-Spirakis keys)
SAMPLE_CAP = 4096

# k-means iteration bound; convergence usually stops earlier
MAX_ITERATIONS = 20

# Centroid movement below which iteration stops
CONVERGENCE_TOLERANCE = 1e-6

# Near-duplicate merge threshold in CIEDE2000 units, roughly one
# just-noticeable difference for uniform patches (Mahy et al. 1994)
MERGE_DELTA_E = 2.2


@dataclass
class Cluster:
    """One palette entry produced by the perceptual engine.

    Attributes:
        rgb: Representative color of the cluster (centroid mapped to sRGB)
        weight: Percentage of visible pixels covered by the cluster (0-100)
    """

    rgb: RGB
    weight: float


def _subsample(items: List[Tuple[RGB, int]], cap: int, rng: random.Random) -> List[Tuple[RGB, int]]:
    """Weighted subsample without replacement via Efraimidis-Spirakis keys.

    Each unique color draws the key u ** (1 / w) from the seeded RNG, so
    frequent colors are likely to survive while rare colors still can.
    Deterministic for a fixed seed and input order.
    """
    if len(items) <= cap:
        return items
    keyed = sorted(
        items,
        key=lambda item: rng.random() ** (1.0 / item[1]),
        reverse=True,
    )
    return keyed[:cap]


def _squared_distance(a: OKLab, b: OKLab) -> float:
    """Squared Euclidean distance in OKLab."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def _init_kmeans_plus_plus(
    points: List[OKLab], weights: List[int], k: int, rng: random.Random
) -> List[OKLab]:
    """k-means++ seeding: first center weighted by count, the rest by D^2."""
    first = rng.choices(range(len(points)), weights=weights, k=1)[0]
    centroids = [points[first]]
    while len(centroids) < k:
        d2 = [w * min(_squared_distance(p, c) for c in centroids) for p, w in zip(points, weights)]
        if sum(d2) == 0:
            # Fewer distinct points than k; pad with the first point
            centroids.append(points[0])
        else:
            centroids.append(points[rng.choices(range(len(points)), weights=d2, k=1)[0]])
    return centroids


def _fit_kmeans(points: List[OKLab], weights: List[int], k: int, rng: random.Random) -> List[OKLab]:
    """Weighted k-means over OKLab points with a fixed iteration bound."""
    centroids = _init_kmeans_plus_plus(points, weights, k, rng)
    for _iteration in range(MAX_ITERATIONS):
        sums = [[0.0, 0.0, 0.0] for _ in range(k)]
        counts = [0] * k
        for point, weight in zip(points, weights):
            nearest = min(range(k), key=lambda c: _squared_distance(point, centroids[c]))
            sums[nearest][0] += point[0] * weight
            sums[nearest][1] += point[1] * weight
            sums[nearest][2] += point[2] * weight
            counts[nearest] += weight

        movement = 0.0
        new_centroids: List[OKLab] = []
        for idx in range(k):
            if counts[idx] == 0:
                # Empty cluster: reseed at the point farthest from its
                # nearest centroid (deterministic tie-break by index)
                farthest = max(
                    range(len(points)),
                    key=lambda i: (
                        min(_squared_distance(points[i], c) for c in centroids),
                        -i,
                    ),
                )
                new_centroids.append(points[farthest])
            else:
                new_centroids.append(
                    (
                        sums[idx][0] / counts[idx],
                        sums[idx][1] / counts[idx],
                        sums[idx][2] / counts[idx],
                    )
                )
            movement += _squared_distance(new_centroids[idx], centroids[idx])
        centroids = new_centroids
        if movement < CONVERGENCE_TOLERANCE:
            break
    return centroids


def _assign_all(
    items: List[Tuple[RGB, int]], centroids: List[OKLab]
) -> Tuple[List[OKLab], List[int]]:
    """Assign every unique color to its nearest centroid.

    Returns per-cluster pixel counts computed over the full input (not
    the fitting subsample) and centroids recomputed as weighted OKLab
    means of their assigned colors. Clusters left empty are dropped.
    """
    k = len(centroids)
    counts = [0] * k
    assignments: List[List[Tuple[OKLab, int]]] = [[] for _ in range(k)]
    for rgb, count in items:
        point = rgb_to_oklab(rgb)
        nearest = min(range(k), key=lambda c: _squared_distance(point, centroids[c]))
        counts[nearest] += count
        assignments[nearest].append((point, count))

    new_centroids: List[OKLab] = []
    new_counts: List[int] = []
    for cluster_points, count in zip(assignments, counts):
        if not cluster_points:
            continue
        total = sum(w for _, w in cluster_points)
        new_centroids.append(
            (
                sum(p[0] * w for p, w in cluster_points) / total,
                sum(p[1] * w for p, w in cluster_points) / total,
                sum(p[2] * w for p, w in cluster_points) / total,
            )
        )
        new_counts.append(count)
    return new_centroids, new_counts


def _merge_near_duplicates(
    centroids: List[OKLab], counts: List[int]
) -> Tuple[List[OKLab], List[int]]:
    """Greedily merge clusters closer than MERGE_DELTA_E in CIEDE2000.

    The heavier cluster absorbs the lighter one; the merged centroid is
    the count-weighted mean in OKLab. Repeats until no pair is below the
    threshold.
    """
    centroids = list(centroids)
    counts = list(counts)
    while True:
        labs = [oklab_to_lab(c) for c in centroids]
        merged = False
        for i in range(len(centroids)):
            for j in range(i + 1, len(centroids)):
                if delta_e_ciede2000(labs[i], labs[j]) < MERGE_DELTA_E:
                    keep, drop = (i, j) if counts[i] >= counts[j] else (j, i)
                    total = counts[keep] + counts[drop]
                    centroids[keep] = tuple(
                        (centroids[keep][ch] * counts[keep] + centroids[drop][ch] * counts[drop])
                        / total
                        for ch in range(3)
                    )  # type: ignore[assignment]
                    counts[keep] = total
                    del centroids[drop], counts[drop]
                    merged = True
                    break
            if merged:
                break
        if not merged:
            return centroids, counts


def extract_palette(counts: Dict[RGB, int], k: int, seed: int = KMEANS_SEED) -> List[Cluster]:
    """Cluster unique visible colors into a perceptual palette.

    Args:
        counts: Mapping of RGB color to visible-pixel count, as produced
            by _count_visible_rgb (transparent pixels already excluded)
        k: Maximum number of clusters; merging may yield fewer
        seed: Seed for the subsample draw and k-means++ initialization

    Returns:
        Clusters sorted by weight descending, heaviest first. Weights are
        percentages of the total visible-pixel count and sum to 100 (up
        to rounding). An empty counts mapping yields an empty list.

    Raises:
        ValueError: If k is less than 1.
    """
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k!r}")

    items = sorted(counts.items())
    total = sum(counts.values())
    if total == 0:
        return []

    if len(items) <= k:
        # Fewer unique colors than requested clusters: exact palette
        clusters = [Cluster(rgb=rgb, weight=round(100 * count / total, 2)) for rgb, count in items]
        clusters.sort(key=lambda c: (-c.weight, c.rgb))
        return clusters

    rng = random.Random(seed)
    working = _subsample(items, SAMPLE_CAP, rng)
    points = [rgb_to_oklab(rgb) for rgb, _ in working]
    weights = [count for _, count in working]

    logger.info(
        f"Fitting k-means++ (k={k}) on {len(working)} weighted colors " f"({len(items)} unique)"
    )
    centroids = _fit_kmeans(points, weights, k, rng)

    # Exact coverage: assign every unique color to its nearest centroid
    # and recompute centroids over the full assignment
    centroids, exact_counts = _assign_all(items, centroids)

    centroids, exact_counts = _merge_near_duplicates(centroids, exact_counts)

    clusters = [
        Cluster(rgb=oklab_to_rgb(centroid), weight=round(100 * count / total, 2))
        for centroid, count in zip(centroids, exact_counts)
    ]
    clusters.sort(key=lambda c: (-c.weight, c.rgb))
    return clusters
