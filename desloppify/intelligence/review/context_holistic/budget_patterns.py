"""Pattern detectors for abstractions budget context."""

from __future__ import annotations

from .budget_patterns_enums import (
    _census_type_strategies,
    _collect_enum_defs,
    _find_enum_bypass,
)
from .budget_patterns_types import (
    _collect_typed_dict_defs,
    _find_dict_any_annotations,
    _find_typed_dict_usage_violations,
    _guess_alternative,
    _is_dict_str_any,
)
from .budget_patterns_wrappers import (
    _find_delegation_heavy_classes,
    _find_facade_modules,
    _find_python_passthrough_wrappers,
    _is_delegation_stmt,
    _python_passthrough_target,
)

__all__ = [
    "_census_type_strategies",
    "_collect_enum_defs",
    "_collect_typed_dict_defs",
    "_find_delegation_heavy_classes",
    "_find_dict_any_annotations",
    "_find_enum_bypass",
    "_find_facade_modules",
    "_find_python_passthrough_wrappers",
    "_find_typed_dict_usage_violations",
    "_guess_alternative",
    "_is_dict_str_any",
    "_is_delegation_stmt",
    "_python_passthrough_target",
]
