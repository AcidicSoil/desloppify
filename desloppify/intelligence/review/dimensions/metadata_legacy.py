"""Legacy subjective dimension defaults preserved for backward compatibility."""

from __future__ import annotations

from desloppify.engine._scoring.subjective.core import DISPLAY_NAMES

LEGACY_DISPLAY_NAMES: dict[str, str] = DISPLAY_NAMES

_LEGACY_SUBJECTIVE_WEIGHTS_BY_DISPLAY: dict[str, float] = {
    "high elegance": 22.0,
    "mid elegance": 22.0,
    "low elegance": 12.0,
    "contracts": 12.0,
    "type safety": 12.0,
    "abstraction fit": 8.0,
    "logic clarity": 6.0,
    "structure nav": 5.0,
    "error consistency": 3.0,
    "naming quality": 2.0,
    "ai generated debt": 1.0,
    "design coherence": 10.0,
}

LEGACY_RESET_ON_SCAN_DIMENSIONS: frozenset[str] = frozenset(
    {
        "naming_quality",
        "error_consistency",
        "abstraction_fitness",
        "logic_clarity",
        "ai_generated_debt",
        "type_safety",
        "contract_coherence",
        "package_organization",
        "high_level_elegance",
        "mid_level_elegance",
        "low_level_elegance",
    }
)


def _normalize_display_name_for_weight_lookup(display_name: str) -> str:
    return " ".join(display_name.strip().lower().split())


def _build_weight_by_dimension() -> dict[str, float]:
    out: dict[str, float] = {}
    for dimension_key, display_name in LEGACY_DISPLAY_NAMES.items():
        weight = _LEGACY_SUBJECTIVE_WEIGHTS_BY_DISPLAY.get(
            _normalize_display_name_for_weight_lookup(display_name)
        )
        if weight is not None:
            out[dimension_key] = weight
    return out


LEGACY_WEIGHT_BY_DIMENSION: dict[str, float] = _build_weight_by_dimension()

__all__ = [
    "LEGACY_DISPLAY_NAMES",
    "LEGACY_RESET_ON_SCAN_DIMENSIONS",
    "LEGACY_WEIGHT_BY_DIMENSION",
]
