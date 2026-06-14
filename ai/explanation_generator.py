from __future__ import annotations

from ai.terrain_planner import TerrainPlannerResult
from core.terrain_presets import TerrainPreset


def _describe_smoothing(smoothing_factor: float) -> str:
    if smoothing_factor >= 0.65:
        return "high smoothing"
    if smoothing_factor >= 0.5:
        return "moderate smoothing"
    return "low smoothing"


def _describe_peak_bias(peak_bias: float) -> str:
    if peak_bias >= 1.1:
        return "a strong elevation bias"
    if peak_bias >= 0.4:
        return "a balanced elevation bias"
    if peak_bias >= 0.0:
        return "a gentle elevation bias"
    return "an erosive negative bias"


def _describe_center_bias(center_bias: float) -> str:
    if center_bias >= 0.75:
        return "a strong center bias"
    if center_bias >= 0.4:
        return "a moderate center bias"
    return "a low center bias"


def generate_explanation(
    prompt: str,
    planner_result: TerrainPlannerResult,
    preset: TerrainPreset,
) -> str:
    smoothing_text = _describe_smoothing(preset.smoothing_factor)
    peak_bias_text = _describe_peak_bias(preset.peak_bias)
    center_bias_text = _describe_center_bias(planner_result.center_bias)
    planning_text = (
        "Azure OpenAI interpreted the terrain description"
        if planner_result.source == "azure_openai"
        else "The app fell back to safe default planning logic"
    )

    return (
        f"{planning_text} for '{prompt}' and selected the {planner_result.terrain_label} terrain profile. "
        f"The simulation runs on a {preset.grid_size}x{preset.grid_size} cellular automata grid for {preset.iterations} iterations, "
        f"with noise level {preset.noise_level:.2f}, {smoothing_text}, and {peak_bias_text}. "
        f"The planner also introduced {center_bias_text}; in this MVP, that signal is folded into the effective elevation bias before CA evolution. "
        f"The final landscape emerges from local cell interactions and is rendered as voxel columns so each visible block column maps directly to one CA cell."
    )
