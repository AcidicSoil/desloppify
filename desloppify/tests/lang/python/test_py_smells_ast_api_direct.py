"""Direct API surface tests for Python AST smell modules."""

from __future__ import annotations

import importlib

import pytest

from desloppify.languages.python.detectors.smells_ast._dispatch import (
    _detect_ast_smells,
)
from desloppify.languages.python.detectors.smells_ast._source_detectors import (
    _collect_module_constants,
    _detect_duplicate_constants,
    _detect_star_import_no_all,
    _detect_vestigial_parameter,
)

smells_ast_pkg = importlib.import_module("desloppify.languages.python.detectors.smells_ast")


def test_smells_ast_package_is_namespace_only():
    assert not hasattr(smells_ast_pkg, "__all__")
    assert not hasattr(smells_ast_pkg, "detect_ast_smells")


def test_smells_ast_source_modules_expose_detectors():
    assert callable(_detect_ast_smells)
    assert callable(_collect_module_constants)
    assert callable(_detect_duplicate_constants)
    assert callable(_detect_star_import_no_all)
    assert callable(_detect_vestigial_parameter)


def test_smells_ast_legacy_exports_are_unavailable_on_package():
    assert not hasattr(smells_ast_pkg, "_detect_dead_functions")
    with pytest.raises(AttributeError):
        _ = smells_ast_pkg._detect_dead_functions
