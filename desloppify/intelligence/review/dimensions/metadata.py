"""Compatibility layer for subjective-dimension metadata helpers.

Historically this module maintained its own metadata-building logic. The
canonical implementation now lives in ``desloppify.base.subjective_dimensions``.
Keep this module as a stable import surface for existing callers.
"""

from __future__ import annotations

from typing import Any

from desloppify.base.subjective_dimensions import (
    default_dimension_keys_for_lang,
    configure_subjective_dimension_providers,
    default_display_names_map,
    dimension_display_name,
    dimension_weight,
    get_dimension_metadata,
    load_subjective_dimension_metadata,
    load_subjective_dimension_metadata_for_lang,
    resettable_default_dimensions,
)
from desloppify.base.subjective_dimensions_merge import extract_prompt_meta
from desloppify.intelligence.review.dimensions.data import (
    load_dimensions as _default_load_dimensions,
)
from desloppify.intelligence.review.dimensions.data import (
    load_dimensions_for_lang as _default_load_dimensions_for_lang,
)
from desloppify.languages import available_langs as _available_langs

# Kept as module-level names for backward-compatible monkeypatching in tests and
# downstream callers.
load_dimensions = _default_load_dimensions
load_dimensions_for_lang = _default_load_dimensions_for_lang


def _load_dimensions_payload() -> tuple[list[str], dict[str, dict[str, Any]], str]:
    return load_dimensions()


def _load_dimensions_payload_for_lang(
    lang_name: str,
) -> tuple[list[str], dict[str, dict[str, Any]], str]:
    return load_dimensions_for_lang(lang_name)


def _available_languages() -> list[str]:
    try:
        return list(_available_langs())
    except (ImportError, ValueError, TypeError, RuntimeError):
        return []


configure_subjective_dimension_providers(
    available_languages_provider=_available_languages,
    load_dimensions_payload_provider=_load_dimensions_payload,
    load_dimensions_payload_for_lang_provider=_load_dimensions_payload_for_lang,
)


__all__ = [
    "default_dimension_keys_for_lang",
    "default_display_names_map",
    "dimension_display_name",
    "dimension_weight",
    "extract_prompt_meta",
    "get_dimension_metadata",
    "load_dimensions",
    "load_dimensions_for_lang",
    "load_subjective_dimension_metadata",
    "load_subjective_dimension_metadata_for_lang",
    "resettable_default_dimensions",
]
