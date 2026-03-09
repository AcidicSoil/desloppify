"""Stage command entrypoints for triage flow."""

from __future__ import annotations

import argparse

from desloppify.base.output.terminal import colorize
from desloppify.base.output.user_message import print_user_message
from desloppify.state import utc_now

from ._stage_records import record_enrich_stage, resolve_reusable_report
from ._stage_validation import (
    _enrich_report_or_error,
    _require_organize_stage_for_enrich,
    _steps_missing_issue_refs,
    _steps_with_bad_paths,
    _steps_with_vague_detail,
    _steps_without_effort,
    _underspecified_steps,
)
from .helpers import (
    cascade_clear_later_confirmations,
    has_triage_in_queue,
    inject_triage_stages,
    print_cascade_clear_feedback,
)
from .services import TriageServices
from .stage_flow_enrich_sense import (
    record_sense_check_stage as _record_sense_check_stage_impl,
)
from .stage_flow_enrich_sense import (
    run_stage_enrich,
    run_stage_sense_check,
)
from .stage_flow_observe_reflect_organize import (
    _cmd_stage_observe as _cmd_stage_observe_impl,
)
from .stage_flow_observe_reflect_organize import (
    _cmd_stage_organize,
    _cmd_stage_reflect,
    cmd_stage_organize,
    cmd_stage_reflect,
)


def _cmd_stage_observe(
    args: argparse.Namespace,
    *,
    services: TriageServices | None = None,
) -> None:
    """Public wrapper for observe stage with patchable queue-start helpers."""
    _cmd_stage_observe_impl(
        args,
        services=services,
        has_triage_in_queue_fn=has_triage_in_queue,
        inject_triage_stages_fn=inject_triage_stages,
    )


def _cmd_stage_enrich(
    args: argparse.Namespace,
    *,
    services: TriageServices | None = None,
) -> None:
    """Public wrapper for enrich stage with patchable module dependencies."""
    run_stage_enrich(
        args,
        services=services,
        has_triage_in_queue_fn=has_triage_in_queue,
        require_organize_stage_for_enrich_fn=_require_organize_stage_for_enrich,
        underspecified_steps_fn=_underspecified_steps,
        steps_with_bad_paths_fn=_steps_with_bad_paths,
        steps_without_effort_fn=_steps_without_effort,
        enrich_report_or_error_fn=_enrich_report_or_error,
        resolve_reusable_report_fn=resolve_reusable_report,
        record_enrich_stage_fn=record_enrich_stage,
        colorize_fn=colorize,
        print_user_message_fn=print_user_message,
        print_cascade_clear_feedback_fn=print_cascade_clear_feedback,
    )


def _record_sense_check_stage(
    stages: dict,
    *,
    report: str,
    existing_stage: dict | None,
    is_reuse: bool,
) -> list[str]:
    return _record_sense_check_stage_impl(
        stages,
        report=report,
        existing_stage=existing_stage,
        is_reuse=is_reuse,
        utc_now_fn=utc_now,
        cascade_clear_later_confirmations_fn=cascade_clear_later_confirmations,
    )


def _cmd_stage_sense_check(
    args: argparse.Namespace,
    *,
    services: TriageServices | None = None,
) -> None:
    """Public wrapper for sense-check stage with patchable module dependencies."""
    run_stage_sense_check(
        args,
        services=services,
        has_triage_in_queue_fn=has_triage_in_queue,
        resolve_reusable_report_fn=resolve_reusable_report,
        record_sense_check_stage_fn=_record_sense_check_stage,
        colorize_fn=colorize,
        print_cascade_clear_feedback_fn=print_cascade_clear_feedback,
        underspecified_steps_fn=_underspecified_steps,
        steps_missing_issue_refs_fn=_steps_missing_issue_refs,
        steps_with_bad_paths_fn=_steps_with_bad_paths,
        steps_with_vague_detail_fn=_steps_with_vague_detail,
        steps_without_effort_fn=_steps_without_effort,
    )


def cmd_stage_enrich(
    args: argparse.Namespace,
    *,
    services: TriageServices | None = None,
) -> None:
    """Public entrypoint for enrich stage recording."""
    _cmd_stage_enrich(args, services=services)


def cmd_stage_sense_check(
    args: argparse.Namespace,
    *,
    services: TriageServices | None = None,
) -> None:
    """Public entrypoint for sense-check stage recording."""
    _cmd_stage_sense_check(args, services=services)


def cmd_stage_observe(
    args: argparse.Namespace,
    *,
    services: TriageServices | None = None,
) -> None:
    """Public entrypoint for observe stage recording."""
    _cmd_stage_observe(args, services=services)


__all__ = [
    "cmd_stage_enrich",
    "cmd_stage_observe",
    "cmd_stage_organize",
    "cmd_stage_reflect",
    "cmd_stage_sense_check",
    "_cmd_stage_enrich",
    "_cmd_stage_observe",
    "_cmd_stage_organize",
    "_cmd_stage_reflect",
    "_cmd_stage_sense_check",
]
