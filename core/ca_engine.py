from __future__ import annotations

import numpy as np


def moore_neighborhood_average(grid: np.ndarray) -> np.ndarray:
    total = np.zeros_like(grid, dtype=float)
    for row_shift in (-1, 0, 1):
        for col_shift in (-1, 0, 1):
            total += np.roll(np.roll(grid, row_shift, axis=0), col_shift, axis=1)
    return total / 9.0


def evolve_terrain(
    grid: np.ndarray,
    iterations: int,
    smoothing_factor: float,
    peak_mask: np.ndarray,
    valley_mask: np.ndarray,
) -> np.ndarray:
    terrain = grid.astype(float).copy()

    for _ in range(iterations):
        neighborhood = moore_neighborhood_average(terrain)
        growth = 0.08 * peak_mask
        erosion = 0.06 * valley_mask
        terrain = ((1.0 - smoothing_factor) * terrain) + (smoothing_factor * neighborhood)
        terrain += growth
        terrain -= erosion

    return terrain
