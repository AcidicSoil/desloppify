"""Tests for plan-tracked objective ID selection."""

from __future__ import annotations

from desloppify.engine._plan.schema import planned_objective_ids


def test_planned_objective_ids_returns_all_when_plan_tracks_nothing() -> None:
    all_ids = {"issue-1", "issue-2"}

    assert planned_objective_ids(all_ids, {"queue_order": [], "clusters": {}}) == all_ids


def test_planned_objective_ids_returns_overlap_when_live_tracked_ids_exist() -> None:
    all_ids = {"issue-1", "issue-2", "issue-3"}
    plan = {
        "queue_order": ["issue-2"],
        "clusters": {"c1": {"issue_ids": ["issue-3"], "action_steps": []}},
        "skipped": {},
        "overrides": {},
    }

    assert planned_objective_ids(all_ids, plan) == {"issue-2", "issue-3"}


def test_planned_objective_ids_returns_empty_when_tracked_ids_are_stale() -> None:
    all_ids = {"issue-1", "issue-2"}
    plan = {
        "queue_order": ["missing-issue"],
        "clusters": {"c1": {"issue_ids": ["missing-cluster-issue"], "action_steps": []}},
        "skipped": {},
        "overrides": {},
    }

    assert planned_objective_ids(all_ids, plan) == set()


def test_planned_objective_ids_ignores_synthetic_and_skipped_tracking() -> None:
    all_ids = {"issue-1", "issue-2"}
    plan = {
        "queue_order": ["workflow::create-plan"],
        "clusters": {},
        "skipped": {"issue-1": {"kind": "temporary"}},
        "overrides": {},
    }

    assert planned_objective_ids(all_ids, plan) == all_ids
