"""Shared dependency bundle for triage command modules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable

from desloppify.app.commands.helpers.runtime import command_runtime
from desloppify.engine.plan import (
    append_log_entry,
    build_triage_prompt,
    collect_triage_input,
    detect_recurring_patterns,
    extract_issue_citations,
    load_plan,
    save_plan,
)


@dataclass(frozen=True)
class TriageServices:
    """Callables shared across triage handler modules."""

    command_runtime: Callable[[argparse.Namespace], Any]
    load_plan: Callable[..., dict]
    save_plan: Callable[..., None]
    collect_triage_input: Callable[[dict, dict], Any]
    detect_recurring_patterns: Callable[[dict, dict], dict]
    append_log_entry: Callable[..., Any]
    extract_issue_citations: Callable[[str, set[str]], set[str]]
    build_triage_prompt: Callable[[Any], str]


def default_triage_services() -> TriageServices:
    """Return the default runtime triage service bundle."""
    return TriageServices(
        command_runtime=command_runtime,
        load_plan=load_plan,
        save_plan=save_plan,
        collect_triage_input=collect_triage_input,
        detect_recurring_patterns=detect_recurring_patterns,
        append_log_entry=append_log_entry,
        extract_issue_citations=extract_issue_citations,
        build_triage_prompt=build_triage_prompt,
    )


__all__ = [
    "TriageServices",
    "default_triage_services",
]
