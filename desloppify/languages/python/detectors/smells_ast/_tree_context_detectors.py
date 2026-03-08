"""Context-oriented tree-level smell detectors (callbacks, path handling)."""

from __future__ import annotations

import ast

from desloppify.languages.python.detectors.smells_ast._helpers import (
    _iter_nodes,
    _looks_like_path_var,
)

_CALLBACK_LOG_NAMES = {
    "dprint",
    "debug_print",
    "debug_func",
    "log_func",
    "print_fn",
    "logger_func",
    "log_callback",
    "print_func",
    "debug_log",
    "verbose_print",
    "trace_func",
}


def _path_like_name(obj: ast.AST) -> str:
    """Extract a variable-like name from Name/Attribute nodes."""
    if isinstance(obj, ast.Name):
        return obj.id
    if isinstance(obj, ast.Attribute):
        return obj.attr
    return ""


def _match_split_slash(filepath: str, node: ast.Call) -> dict | None:
    """Match ``path_var.split('/')`` style hardcoded separator usage."""
    if not (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "split"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "/"
    ):
        return None

    obj = node.func.value
    if (
        isinstance(obj, ast.Call)
        and isinstance(obj.func, ast.Attribute)
        and obj.func.attr in ("relpath", "relative_to")
    ):
        return {
            "file": filepath,
            "line": node.lineno,
            "content": f'{ast.dump(obj.func)[:40]}.split("/")',
        }

    var_name = _path_like_name(obj)
    if var_name and _looks_like_path_var(var_name):
        return {
            "file": filepath,
            "line": node.lineno,
            "content": f'{var_name}.split("/")',
        }
    return None


def _match_startswith_slash(filepath: str, node: ast.Call) -> dict | None:
    """Match ``path_var.startswith('x/y')`` patterns with hardcoded slashes."""
    if not (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "startswith"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and "/" in node.args[0].value
        and not node.args[0].value.startswith(("@", "http", "//"))
    ):
        return None

    var_name = _path_like_name(node.func.value)
    if var_name and _looks_like_path_var(var_name):
        return {
            "file": filepath,
            "line": node.lineno,
            "content": f'{var_name}.startswith("{node.args[0].value}")',
        }
    return None


def _detect_callback_logging(
    filepath: str,
    tree: ast.Module,
    *,
    all_nodes: tuple[ast.AST, ...] | None = None,
) -> list[dict]:
    """Flag functions that accept a logging callback parameter.

    Detects parameters matching common logging-callback names (dprint, log_func, etc.)
    that are actually called with string arguments in the function body.
    """
    results: list[dict] = []
    for node in _iter_nodes(tree, all_nodes, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # Check each parameter name
        for arg in node.args.args + node.args.kwonlyargs:
            name = arg.arg
            if name not in _CALLBACK_LOG_NAMES:
                continue

            # Verify it's actually called in the body (not just accepted)
            call_count = 0
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Name)
                    and child.func.id == name
                ):
                    call_count += 1

            if call_count >= 1:
                results.append(
                    {
                        "file": filepath,
                        "line": node.lineno,
                        "content": f"{node.name}({name}=...) — called {call_count} time(s)",
                    }
                )
    return results


def _detect_hardcoded_path_sep(
    filepath: str,
    tree: ast.Module,
    *,
    all_nodes: tuple[ast.AST, ...] | None = None,
) -> list[dict]:
    """Flag .split('/') on path-like variables, and os.path.join mixed with '/'.

    Detects two patterns:
    1. path_var.split('/') — should use os.sep or normalize with replace('\\\\', '/')
    2. f-strings or concatenation building paths with hardcoded '/' separators
       on variables with path-like names
    """
    results: list[dict] = []
    for node in _iter_nodes(tree, all_nodes, ast.Call):
        split_match = _match_split_slash(filepath, node)
        if split_match is not None:
            results.append(split_match)

        startswith_match = _match_startswith_slash(filepath, node)
        if startswith_match is not None:
            results.append(startswith_match)
    return results
