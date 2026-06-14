from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from core.terrain_presets import DEFAULT_PRESET_KEY, TerrainPreset, get_preset


ALLOWED_TERRAIN_TYPES = {"volcano", "island", "mountain", "canyon", "hills"}
DEFAULT_CENTER_BIAS = {
    "volcano": 0.9,
    "island": 0.85,
    "mountain": 0.45,
    "canyon": 0.2,
    "hills": 0.35,
}


@dataclass(frozen=True)
class TerrainPlannerResult:
    prompt: str
    terrain_type: str
    iterations: int
    noise_level: float
    smoothing_factor: float
    peak_bias: float
    center_bias: float
    reasoning: list[str]
    source: str
    status_message: str
    validation_issues: list[str]
    raw_response: str | None = None

    @property
    def terrain_label(self) -> str:
        return get_preset(self.terrain_type).name

    @property
    def source_label(self) -> str:
        if self.source == "azure_openai":
            return "Azure OpenAI"
        return "Fallback Defaults"

    def generated_parameters(self) -> dict[str, Any]:
        return {
            "terrain_type": self.terrain_type,
            "iterations": self.iterations,
            "noise_level": self.noise_level,
            "smoothing_factor": self.smoothing_factor,
            "peak_bias": self.peak_bias,
            "center_bias": self.center_bias,
        }

    def effective_peak_bias(self) -> float:
        center_multiplier_by_type = {
            "volcano": 0.7 + (0.6 * self.center_bias),
            "island": 0.72 + (0.55 * self.center_bias),
            "mountain": 0.88 + (0.25 * self.center_bias),
            "canyon": 0.95 + (0.1 * self.center_bias),
            "hills": 0.8 + (0.35 * self.center_bias),
        }
        multiplier = center_multiplier_by_type.get(self.terrain_type, 1.0)
        return round(self.peak_bias * multiplier, 4)

    def build_runtime_preset(self) -> TerrainPreset:
        base_preset = get_preset(self.terrain_type)
        return TerrainPreset(
            name=base_preset.name,
            grid_size=base_preset.grid_size,
            iterations=self.iterations,
            noise_level=self.noise_level,
            smoothing_factor=self.smoothing_factor,
            peak_bias=self.effective_peak_bias(),
        )

    def runtime_parameters(self) -> dict[str, Any]:
        runtime_preset = self.build_runtime_preset()
        return {
            **runtime_preset.to_dict(),
            "terrain_type": self.terrain_type,
            "center_bias": self.center_bias,
            "effective_peak_bias": runtime_preset.peak_bias,
        }


SYSTEM_PROMPT = """
You are the terrain planning module for terrCAIn.

Convert the user's terrain description into Cellular Automata planning parameters.
Return ONLY a JSON object with these exact keys:
- terrain_type
- iterations
- noise_level
- smoothing_factor
- peak_bias
- center_bias
- reasoning

Rules:
- Allowed terrain_type values: volcano, island, mountain, canyon, hills
- iterations must be an integer between 20 and 70
- noise_level must be a float between 0.05 and 0.40
- smoothing_factor must be a float between 0.10 and 0.85
- peak_bias must be a float between -1.20 and 1.50
- center_bias must be a float between 0.00 and 1.00
- reasoning must be an array of 3 to 5 short bullet-style strings
- Do not include markdown, comments, prose, or code fences
""".strip()


def _normalize_endpoint(endpoint: str) -> str:
    normalized = endpoint.strip().rstrip("/")
    if normalized.endswith("/openai/v1"):
        return f"{normalized}/"
    if normalized.endswith("/openai"):
        return f"{normalized}/v1/"
    return f"{normalized}/openai/v1/"


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_index = cleaned.find("{")
        end_index = cleaned.rfind("}")
        if start_index == -1 or end_index == -1 or end_index <= start_index:
            raise
        return json.loads(cleaned[start_index : end_index + 1])


def _coerce_int(
    value: Any,
    default: int,
    minimum: int,
    maximum: int,
    field_name: str,
    issues: list[str],
) -> int:
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        issues.append(f"{field_name} was invalid and fell back to {default}.")
        return default
    return max(minimum, min(maximum, coerced))


def _coerce_float(
    value: Any,
    default: float,
    minimum: float,
    maximum: float,
    field_name: str,
    issues: list[str],
) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        issues.append(f"{field_name} was invalid and fell back to {default}.")
        return default
    return round(max(minimum, min(maximum, coerced)), 4)


def _build_reasoning(
    terrain_type: str,
    iterations: int,
    noise_level: float,
    smoothing_factor: float,
    peak_bias: float,
    center_bias: float,
) -> list[str]:
    terrain_label = get_preset(terrain_type).name.lower()
    smoothing_description = "reduced smoothing for sharper local variation" if smoothing_factor < 0.45 else (
        "balanced smoothing to preserve terrain structure" if smoothing_factor < 0.65 else "increased smoothing for softer terrain transitions"
    )
    peak_description = (
        "increased peak bias to emphasize elevation gain"
        if peak_bias > 0.7
        else "used a balanced peak bias for moderate relief"
        if peak_bias >= 0.0
        else "used a negative elevation bias to deepen cuts and valleys"
    )
    center_description = (
        "pushed elevation toward the center of the map"
        if center_bias >= 0.7
        else "kept central shaping moderate"
        if center_bias >= 0.35
        else "kept the terrain spread broadly across the grid"
    )
    return [
        f"Detected a {terrain_label} terrain profile.",
        f"Set the automata to {iterations} iterations for visible terrain evolution.",
        f"Used noise level {noise_level:.2f} to seed local variation.",
        smoothing_description.capitalize() + ".",
        f"{peak_description.capitalize()} and {center_description}.",
    ]


def _fallback_plan(prompt: str, message: str) -> TerrainPlannerResult:
    default_preset = get_preset(DEFAULT_PRESET_KEY)
    center_bias = DEFAULT_CENTER_BIAS[DEFAULT_PRESET_KEY]
    reasoning = _build_reasoning(
        terrain_type=DEFAULT_PRESET_KEY,
        iterations=default_preset.iterations,
        noise_level=default_preset.noise_level,
        smoothing_factor=default_preset.smoothing_factor,
        peak_bias=default_preset.peak_bias,
        center_bias=center_bias,
    )
    return TerrainPlannerResult(
        prompt=prompt,
        terrain_type=DEFAULT_PRESET_KEY,
        iterations=default_preset.iterations,
        noise_level=default_preset.noise_level,
        smoothing_factor=default_preset.smoothing_factor,
        peak_bias=default_preset.peak_bias,
        center_bias=center_bias,
        reasoning=reasoning,
        source="fallback",
        status_message=message,
        validation_issues=[message],
        raw_response=None,
    )


def _validate_plan(prompt: str, payload: dict[str, Any], raw_response: str) -> TerrainPlannerResult:
    issues: list[str] = []

    terrain_type = str(payload.get("terrain_type", DEFAULT_PRESET_KEY)).strip().lower()
    if terrain_type not in ALLOWED_TERRAIN_TYPES:
        issues.append(f"terrain_type '{terrain_type}' is unsupported and fell back to {DEFAULT_PRESET_KEY}.")
        terrain_type = DEFAULT_PRESET_KEY

    base_preset = get_preset(terrain_type)
    iterations = _coerce_int(payload.get("iterations"), base_preset.iterations, 20, 70, "iterations", issues)
    noise_level = _coerce_float(payload.get("noise_level"), base_preset.noise_level, 0.05, 0.40, "noise_level", issues)
    smoothing_factor = _coerce_float(
        payload.get("smoothing_factor"),
        base_preset.smoothing_factor,
        0.10,
        0.85,
        "smoothing_factor",
        issues,
    )
    peak_bias = _coerce_float(payload.get("peak_bias"), base_preset.peak_bias, -1.20, 1.50, "peak_bias", issues)
    center_bias = _coerce_float(
        payload.get("center_bias"),
        DEFAULT_CENTER_BIAS[terrain_type],
        0.0,
        1.0,
        "center_bias",
        issues,
    )

    raw_reasoning = payload.get("reasoning")
    if isinstance(raw_reasoning, list):
        reasoning = [str(item).strip() for item in raw_reasoning if str(item).strip()]
    else:
        reasoning = []

    if not reasoning:
        issues.append("reasoning was missing or invalid and was synthesized locally.")
        reasoning = _build_reasoning(
            terrain_type=terrain_type,
            iterations=iterations,
            noise_level=noise_level,
            smoothing_factor=smoothing_factor,
            peak_bias=peak_bias,
            center_bias=center_bias,
        )

    status_message = "Azure OpenAI planner generated and validated terrain parameters."
    if issues:
        status_message = "Azure OpenAI planner responded, and invalid fields were repaired with safe defaults."

    return TerrainPlannerResult(
        prompt=prompt,
        terrain_type=terrain_type,
        iterations=iterations,
        noise_level=noise_level,
        smoothing_factor=smoothing_factor,
        peak_bias=peak_bias,
        center_bias=center_bias,
        reasoning=reasoning[:5],
        source="azure_openai",
        status_message=status_message,
        validation_issues=issues,
        raw_response=raw_response,
    )


def _request_plan_json(client: OpenAI, deployment: str, prompt: str) -> str:
    request_kwargs = {
        "model": deployment,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    try:
        response = client.chat.completions.create(
            **request_kwargs,
            response_format={"type": "json_object"},
        )
    except Exception:
        response = client.chat.completions.create(**request_kwargs)

    message_content = response.choices[0].message.content
    if isinstance(message_content, str):
        return message_content
    return json.dumps(message_content)


def plan_terrain(prompt: str) -> TerrainPlannerResult:
    normalized_prompt = prompt.strip() or "Generate rolling hills"

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    if not endpoint or not api_key or not deployment:
        return _fallback_plan(
            normalized_prompt,
            "Azure OpenAI environment variables are missing. Using safe default terrain parameters.",
        )

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=_normalize_endpoint(endpoint),
        )
        raw_response = _request_plan_json(client, deployment, normalized_prompt)
        payload = _extract_json_object(raw_response)
        return _validate_plan(normalized_prompt, payload, raw_response)
    except Exception as exc:
        return _fallback_plan(
            normalized_prompt,
            f"Azure OpenAI planning failed ({exc}). Using safe default terrain parameters.",
        )
