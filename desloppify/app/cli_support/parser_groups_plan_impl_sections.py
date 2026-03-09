"""Shared subparser builders for the plan command family."""

from __future__ import annotations

from .parser_groups_plan_impl_sections_annotations import (
    _add_annotation_subparsers,
    _add_resolve_subparser,
    _add_skip_subparsers,
)
from .parser_groups_plan_impl_sections_cluster import _add_cluster_subparser
from .parser_groups_plan_impl_sections_queue_reorder import (
    _add_queue_subparser,
    _add_reorder_subparser,
)
from .parser_groups_plan_impl_sections_triage_commit_scan import (
    _add_commit_log_subparser,
    _add_scan_gate_subparser,
    _add_triage_subparser,
)

__all__ = [
    "_add_annotation_subparsers",
    "_add_cluster_subparser",
    "_add_commit_log_subparser",
    "_add_queue_subparser",
    "_add_reorder_subparser",
    "_add_resolve_subparser",
    "_add_scan_gate_subparser",
    "_add_skip_subparsers",
    "_add_triage_subparser",
]
