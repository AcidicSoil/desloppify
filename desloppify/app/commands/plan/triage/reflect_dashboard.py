"""Reflect-stage dashboard rendering helpers."""

from __future__ import annotations

from desloppify.base.output.terminal import colorize
from desloppify.engine._plan.epic_triage import detect_recurring_patterns


def _print_reflect_dashboard(si: object, plan: dict) -> None:
    """Show completed clusters, resolved issues, and recurring patterns."""
    completed = getattr(si, "completed_clusters", [])
    resolved = getattr(si, "resolved_issues", {})
    open_issues = getattr(si, "open_issues", {})

    _print_completed_clusters(completed)
    _print_resolved_issues(resolved)
    recurring = _print_recurring_patterns(open_issues, resolved)
    if not recurring and not completed and not resolved:
        print(colorize("\n  First triage — no prior work to compare against.", "dim"))
        print(colorize("  Focus your reflect report on your strategy:", "yellow"))
        print(
            colorize(
                "  - How will you resolve contradictions you identified in observe?",
                "dim",
            )
        )
        print(colorize("  - Which issues will you cluster together vs defer?", "dim"))
        print(colorize("  - What's the overall arc of work and why?", "dim"))


def _print_completed_clusters(completed: list[dict]) -> None:
    """Print completed cluster context for reflect stage."""
    if not completed:
        return
    print(colorize("\n  Previously completed clusters:", "cyan"))
    for cluster in completed[:10]:
        name = cluster.get("name", "?")
        count = len(cluster.get("issue_ids", []))
        thesis = cluster.get("thesis", "")
        print(f"    {name}: {count} issues")
        if thesis:
            print(colorize(f"      {thesis}", "dim"))
        for step in cluster.get("action_steps", [])[:3]:
            print(colorize(f"      - {step}", "dim"))
    if len(completed) > 10:
        print(colorize(f"    ... and {len(completed) - 10} more", "dim"))


def _print_resolved_issues(resolved: dict[str, dict]) -> None:
    """Print resolved issues delta since last triage."""
    if not resolved:
        return
    print(colorize(f"\n  Resolved issues since last triage: {len(resolved)}", "cyan"))
    for issue_id, issue in sorted(resolved.items())[:10]:
        status = issue.get("status", "")
        summary = issue.get("summary", "")
        detail = issue.get("detail", {}) if isinstance(issue.get("detail"), dict) else {}
        dim = detail.get("dimension", "")
        print(f"    [{status}] [{dim}] {summary}")
        print(colorize(f"      {issue_id}", "dim"))
    if len(resolved) > 10:
        print(colorize(f"    ... and {len(resolved) - 10} more", "dim"))


def _print_recurring_patterns(open_issues: dict, resolved: dict[str, dict]) -> bool:
    """Print recurring pattern diagnostics for reflect stage."""
    recurring = detect_recurring_patterns(open_issues, resolved)
    if not recurring:
        return False
    print(colorize("\n  Recurring patterns detected:", "yellow"))
    for dim, info in sorted(recurring.items()):
        resolved_count = len(info["resolved"])
        open_count = len(info["open"])
        label = "potential loop" if open_count >= resolved_count else "root cause unaddressed"
        print(
            colorize(
                f"    {dim}: {resolved_count} resolved, {open_count} still open \u2014 {label}",
                "yellow",
            )
        )
    return True
