"""Language registration API plus compatibility exports for legacy callers.

Runtime code should prefer ``desloppify.languages.framework`` for framework
access; this module focuses on registration and language lookup.

Compatibility owner: language-framework
Removal target (legacy module exports): 2026-06-30
"""

from __future__ import annotations

from importlib import import_module
from collections.abc import Callable
from typing import TypeVar

from desloppify.languages.framework import (
    LangConfig,
    auto_detect_lang,
    available_langs,
    get_lang,
    make_lang_config,
)
from desloppify.languages._framework.contract_validation import validate_lang_contract
from desloppify.languages._framework.policy import REQUIRED_DIRS, REQUIRED_FILES
from desloppify.languages._framework.registration import register_lang_class_with
from desloppify.languages._framework.structure_validation import validate_lang_structure

T = TypeVar("T")

_LEGACY_FRAMEWORK_EXPORTS = {
    "discovery": "desloppify.languages._framework.discovery",
    "registry_state": "desloppify.languages._framework.registry_state",
    "resolution": "desloppify.languages._framework.resolution",
    "runtime": "desloppify.languages._framework.runtime",
}


def _legacy_framework_export(name: str):
    """Resolve a legacy framework export lazily for compatibility callers."""
    module_path = _LEGACY_FRAMEWORK_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return import_module(module_path)


def register_lang(name: str) -> Callable[[T], T]:
    """Decorator to register a language config class.

    Validates structure, instantiates the class, validates the contract,
    and stores the *instance* in the registry.
    """

    def decorator(cls: T) -> T:
        register_lang_class_with(
            name,
            cls,
            validate_lang_structure_fn=validate_lang_structure,
        )
        return cls

    return decorator


def register_generic_lang(name: str, cfg: LangConfig) -> None:
    """Register a pre-built language plugin instance (no package structure required)."""
    validate_lang_contract(name, cfg)
    _legacy_framework_export("registry_state").register(name, cfg)


def reload_lang_plugins() -> list[str]:
    """Force plugin rediscovery and return refreshed language names."""
    _legacy_framework_export("discovery").load_all(force_reload=True)
    return sorted(_legacy_framework_export("registry_state").all_keys())


def __getattr__(name: str):
    """Expose legacy framework modules on demand without keeping them live-bound."""
    return _legacy_framework_export(name)


def __dir__() -> list[str]:
    """Report stable public names plus legacy compatibility exports."""
    return sorted(set(globals()) | set(_LEGACY_FRAMEWORK_EXPORTS))


__all__ = [
    "REQUIRED_FILES",
    "REQUIRED_DIRS",
    "register_lang",
    "register_generic_lang",
    "reload_lang_plugins",
    "get_lang",
    "available_langs",
    "auto_detect_lang",
    "make_lang_config",
    "validate_lang_structure",
    "validate_lang_contract",
]
