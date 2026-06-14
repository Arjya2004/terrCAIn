from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TerrainPreset:
    name: str
    grid_size: int
    iterations: int
    noise_level: float
    smoothing_factor: float
    peak_bias: float

    def to_dict(self) -> dict:
        return asdict(self)


TERRAIN_PRESETS: dict[str, TerrainPreset] = {
    "volcano": TerrainPreset(
        name="Volcano",
        grid_size=100,
        iterations=40,
        noise_level=0.22,
        smoothing_factor=0.52,
        peak_bias=1.35,
    ),
    "island": TerrainPreset(
        name="Island",
        grid_size=100,
        iterations=34,
        noise_level=0.18,
        smoothing_factor=0.62,
        peak_bias=0.95,
    ),
    "mountain": TerrainPreset(
        name="Mountain Range",
        grid_size=100,
        iterations=45,
        noise_level=0.28,
        smoothing_factor=0.48,
        peak_bias=1.2,
    ),
    "canyon": TerrainPreset(
        name="Canyon",
        grid_size=100,
        iterations=38,
        noise_level=0.2,
        smoothing_factor=0.45,
        peak_bias=-0.75,
    ),
    "hills": TerrainPreset(
        name="Rolling Hills",
        grid_size=100,
        iterations=30,
        noise_level=0.16,
        smoothing_factor=0.7,
        peak_bias=0.45,
    ),
}


DEFAULT_PRESET_KEY = "hills"


def get_preset(key: str) -> TerrainPreset:
    return TERRAIN_PRESETS.get(key, TERRAIN_PRESETS[DEFAULT_PRESET_KEY])
