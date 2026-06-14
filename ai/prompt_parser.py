from __future__ import annotations

from dataclasses import dataclass

from core.terrain_presets import DEFAULT_PRESET_KEY, TerrainPreset, get_preset


KEYWORD_TO_PRESET = {
    "volcano": "volcano",
    "volcanic": "volcano",
    "island": "island",
    "mountain": "mountain",
    "mountains": "mountain",
    "range": "mountain",
    "canyon": "canyon",
    "hills": "hills",
    "hill": "hills",
    "rolling": "hills",
}


@dataclass
class PromptParseResult:
    preset_name: str
    preset: TerrainPreset
    matched_keywords: list[str]


def parse_prompt(prompt: str) -> PromptParseResult:
    normalized_prompt = prompt.lower().strip()
    matched_keywords = [keyword for keyword in KEYWORD_TO_PRESET if keyword in normalized_prompt]

    chosen_key = DEFAULT_PRESET_KEY
    for keyword in matched_keywords:
        chosen_key = KEYWORD_TO_PRESET[keyword]
        if chosen_key in {"volcano", "island", "mountain", "canyon", "hills"}:
            break

    preset = get_preset(chosen_key)
    return PromptParseResult(
        preset_name=preset.name,
        preset=preset,
        matched_keywords=matched_keywords,
    )
