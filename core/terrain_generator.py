from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core.ca_engine import evolve_terrain
from core.terrain_presets import TerrainPreset


@dataclass
class TerrainResult:
    heightmap: np.ndarray
    metadata: dict


def _coordinate_grids(size: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axis = np.linspace(-1.0, 1.0, size)
    x_grid, y_grid = np.meshgrid(axis, axis)
    radial = np.sqrt(x_grid**2 + y_grid**2)
    return x_grid, y_grid, radial


def _build_base_heightmap(preset: TerrainPreset, random_state: np.random.Generator) -> np.ndarray:
    size = preset.grid_size
    x_grid, y_grid, radial = _coordinate_grids(size)
    noise = random_state.normal(0.0, preset.noise_level, size=(size, size))

    ridge_pattern = np.sin(x_grid * np.pi * 3.0) * 0.3
    layered_pattern = np.cos(y_grid * np.pi * 2.0) * 0.15
    base = noise + ridge_pattern + layered_pattern

    terrain_name = preset.name.lower()
    if "volcano" in terrain_name:
        cone = np.clip(1.25 - (radial * 1.6), 0.0, None)
        crater = np.exp(-(radial**2) / 0.02) * 0.95
        base += cone - crater
    elif "island" in terrain_name:
        dome = np.clip(1.15 - (radial * 1.25), 0.0, None)
        shoreline = -0.35 * np.maximum(radial - 0.7, 0.0)
        base += dome + shoreline
    elif "mountain" in terrain_name:
        ridge_band = np.exp(-(y_grid**2) / 0.08) * 0.8
        broken_ridges = np.sin(x_grid * np.pi * 5.0) * 0.25
        base += ridge_band + broken_ridges
    elif "canyon" in terrain_name:
        trench = -np.exp(-(x_grid**2) / 0.03) * 1.0
        plateau = 0.45 * np.abs(y_grid)
        base += trench + plateau
    else:
        rolling = np.sin(x_grid * np.pi * 2.0) * np.cos(y_grid * np.pi * 2.0) * 0.4
        base += rolling

    return base


def _build_bias_masks(preset: TerrainPreset) -> tuple[np.ndarray, np.ndarray]:
    size = preset.grid_size
    x_grid, y_grid, radial = _coordinate_grids(size)
    terrain_name = preset.name.lower()

    if "volcano" in terrain_name:
        peak_mask = np.exp(-(radial**2) / 0.16) * preset.peak_bias
        valley_mask = np.exp(-(radial**2) / 0.025) * 0.9
    elif "island" in terrain_name:
        peak_mask = np.clip(1.0 - radial, 0.0, None) * preset.peak_bias
        valley_mask = np.clip(radial - 0.65, 0.0, None)
    elif "mountain" in terrain_name:
        peak_mask = np.exp(-(y_grid**2) / 0.12) * preset.peak_bias
        valley_mask = np.clip(np.abs(y_grid) - 0.45, 0.0, None) * 0.5
    elif "canyon" in terrain_name:
        peak_mask = np.abs(y_grid) * max(preset.peak_bias, 0.1)
        valley_mask = np.exp(-(x_grid**2) / 0.04) * abs(preset.peak_bias)
    else:
        peak_mask = (np.sin(x_grid * np.pi) ** 2 + np.cos(y_grid * np.pi) ** 2) * 0.25
        peak_mask *= preset.peak_bias
        valley_mask = radial * 0.15

    return peak_mask, valley_mask


def _normalize_heightmap(heightmap: np.ndarray) -> np.ndarray:
    minimum = float(heightmap.min())
    maximum = float(heightmap.max())
    if maximum - minimum < 1e-8:
        return np.zeros_like(heightmap)
    return (heightmap - minimum) / (maximum - minimum)


def generate_terrain(preset: TerrainPreset) -> TerrainResult:
    random_state = np.random.default_rng(42)
    base_heightmap = _build_base_heightmap(preset, random_state)
    peak_mask, valley_mask = _build_bias_masks(preset)
    evolved_heightmap = evolve_terrain(
        grid=base_heightmap,
        iterations=preset.iterations,
        smoothing_factor=preset.smoothing_factor,
        peak_mask=peak_mask,
        valley_mask=valley_mask,
    )
    normalized_heightmap = _normalize_heightmap(evolved_heightmap)

    return TerrainResult(
        heightmap=normalized_heightmap,
        metadata=preset.to_dict(),
    )
