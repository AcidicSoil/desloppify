"""Direct tests for the shared reconcile pipeline and queue ownership rules."""

from __future__ import annotations

from desloppify.engine._plan.auto_cluster import auto_cluster_issues
from desloppify.engine._plan.schema import empty_plan
from desloppify.engine._plan.sync import live_planned_queue_empty, reconcile_plan
from desloppify.engine._work_queue.snapshot import (
    PHASE_EXECUTE,
    PHASE_REVIEW_POSTFLIGHT,
    build_queue_snapshot,
)


def _issue(issue_id: str, detector: str = "unused") -> dict:
    return {
        "id": issue_id,
        "detector": detector,
        "status": "open",
        "file": "src/app.py",
        "tier": 1,
        "confidence": "high",
        "summary": issue_id,
        "detail": {},
    }


def test_live_planned_queue_empty_uses_queue_order_only() -> None:
    plan = empty_plan()
    plan["clusters"] = {
        "manual/review": {
            "name": "manual/review",
            "issue_ids": ["unused::a"],
            "execution_status": "active",
        }
    }
    plan["overrides"] = {
        "unused::a": {
            "issue_id": "unused::a",
            "cluster": "manual/review",
        }
    }

    assert live_planned_queue_empty(plan) is True


def test_reconcile_plan_noops_when_live_queue_not_empty() -> None:
    state = {"issues": {"unused::a": _issue("unused::a")}}
    plan = empty_plan()
    plan["queue_order"] = ["unused::a"]
    plan["plan_start_scores"] = {"strict": 80.0}

    result = reconcile_plan(plan, state, target_strict=95.0)

    assert result.dirty is False
    assert result.workflow_injected_ids == []
    assert plan["queue_order"] == ["unused::a"]


def test_auto_cluster_issues_is_noop_mid_cycle() -> None:
    state = {
        "issues": {
            "unused::a": _issue("unused::a"),
            "unused::b": _issue("unused::b"),
        }
    }
    plan = empty_plan()
    plan["queue_order"] = ["unused::a"]
    plan["plan_start_scores"] = {"strict": 80.0}

    changes = auto_cluster_issues(plan, state)

    assert changes == 0
    assert plan["clusters"] == {}


def test_queue_snapshot_executes_review_items_promoted_into_active_cluster() -> None:
    state = {
        "issues": {
            "review::a": _issue("review::a", detector="review"),
        }
    }
    plan = empty_plan()
    plan["queue_order"] = ["review::a"]
    plan["plan_start_scores"] = {"strict": 80.0}
    plan["epic_triage_meta"] = {
        "triaged_ids": ["review::a"],
        "issue_snapshot_hash": "stable",
    }
    plan["clusters"] = {
        "epic/review": {
            "name": "epic/review",
            "issue_ids": ["review::a"],
            "execution_status": "active",
        }
    }

    snapshot = build_queue_snapshot(state, plan=plan)

    assert snapshot.phase == PHASE_EXECUTE
    assert [item["id"] for item in snapshot.execution_items] == ["review::a"]


def test_queue_snapshot_keeps_unpromoted_review_cluster_in_postflight() -> None:
    state = {
        "issues": {
            "review::a": _issue("review::a", detector="review"),
        }
    }
    plan = empty_plan()
    plan["epic_triage_meta"] = {
        "triaged_ids": ["review::a"],
        "issue_snapshot_hash": "stable",
    }
    plan["refresh_state"] = {"postflight_scan_completed_at_scan_count": 1}
    plan["clusters"] = {
        "manual/review": {
            "name": "manual/review",
            "issue_ids": ["review::a"],
            "execution_status": "review",
        }
    }

    snapshot = build_queue_snapshot(state, plan=plan)

    assert live_planned_queue_empty(plan) is True
    assert snapshot.phase == PHASE_REVIEW_POSTFLIGHT
    assert [item["id"] for item in snapshot.execution_items] == ["review::a"]
