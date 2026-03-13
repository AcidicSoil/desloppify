"""Shared boundary-triggered plan reconciliation pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from desloppify.state_scoring import score_snapshot
from desloppify.engine._plan.auto_cluster import auto_cluster_issues
from desloppify.engine._plan.constants import QueueSyncResult, is_synthetic_id
from desloppify.engine._plan.operations.meta import append_log_entry
from desloppify.engine._plan.policy.subjective import compute_subjective_visibility
from desloppify.engine._plan.refresh_lifecycle import set_lifecycle_phase
from desloppify.engine._plan.sync.dimensions import sync_subjective_dimensions
from desloppify.engine._plan.sync.triage import sync_triage_needed
from desloppify.engine._plan.sync.workflow import (
    ScoreSnapshot,
    sync_communicate_score_needed,
    sync_create_plan_needed,
)


@dataclass
class ReconcileResult:
    """Mutation summary for one boundary-triggered reconcile pass."""

    subjective: QueueSyncResult | None = None
    auto_cluster_changes: int = 0
    communicate_score: QueueSyncResult | None = None
    create_plan: QueueSyncResult | None = None
    triage: QueueSyncResult | None = None
    lifecycle_phase: str = ""
    lifecycle_phase_changed: bool = False

    @property
    def dirty(self) -> bool:
        return any(
            (
                self.subjective is not None and bool(self.subjective.changes),
                self.auto_cluster_changes > 0,
                self.communicate_score is not None
                and bool(self.communicate_score.changes),
                self.create_plan is not None
                and bool(self.create_plan.changes),
                self.triage is not None
                and bool(
                    self.triage.changes
                    or getattr(self.triage, "deferred", False)
                ),
                self.lifecycle_phase_changed,
            )
        )

    @property
    def workflow_injected_ids(self) -> list[str]:
        injected: list[str] = []
        for result in (self.communicate_score, self.create_plan):
            if result is None:
                continue
            injected.extend(list(result.injected))
        return injected


def _current_scores(state: dict) -> ScoreSnapshot:
    snapshot = score_snapshot(state)
    return ScoreSnapshot(
        strict=snapshot.strict,
        overall=snapshot.overall,
        objective=snapshot.objective,
        verified=snapshot.verified,
    )


def _log_gate_changes(plan: dict, action: str, detail: dict[str, object]) -> None:
    append_log_entry(plan, action, actor="system", detail=detail)


def _persist_lifecycle(
    plan: dict, state: dict, *, target_strict: float,
) -> tuple[str, bool]:
    from desloppify.engine._work_queue.context import queue_context
    from desloppify.engine._work_queue.snapshot import coarse_phase_name

    phase = coarse_phase_name(
        queue_context(state, plan=plan, target_strict=target_strict).snapshot.phase
    )
    return phase, set_lifecycle_phase(plan, phase)


def live_planned_queue_empty(plan: dict) -> bool:
    """Return True when queue_order has no remaining substantive items."""
    order = plan.get("queue_order", [])
    skipped = plan.get("skipped", {})
    return not any(
        isinstance(item_id, str)
        and item_id not in skipped
        and not is_synthetic_id(item_id)
        for item_id in order
    )


def reconcile_plan(plan: dict, state: dict, *, target_strict: float) -> ReconcileResult:
    """Run the shared boundary reconciliation pipeline."""
    result = ReconcileResult()
    if not live_planned_queue_empty(plan):
        return result

    policy = compute_subjective_visibility(
        state,
        target_strict=target_strict,
        plan=plan,
    )
    cycle_just_completed = not plan.get("plan_start_scores")

    result.subjective = sync_subjective_dimensions(
        plan,
        state,
        policy=policy,
        cycle_just_completed=cycle_just_completed,
    )
    if result.subjective.changes:
        _log_gate_changes(plan, "sync_subjective", {"changes": True})

    result.auto_cluster_changes = int(
        auto_cluster_issues(
            plan,
            state,
            target_strict=target_strict,
            policy=policy,
        )
    )
    if result.auto_cluster_changes:
        _log_gate_changes(plan, "auto_cluster", {"changes": True})

    result.communicate_score = sync_communicate_score_needed(
        plan,
        state,
        policy=policy,
        current_scores=_current_scores(state),
    )
    if result.communicate_score.changes:
        _log_gate_changes(plan, "sync_communicate_score", {"injected": True})

    result.create_plan = sync_create_plan_needed(
        plan,
        state,
        policy=policy,
    )
    if result.create_plan.changes:
        _log_gate_changes(plan, "sync_create_plan", {"injected": True})

    result.triage = sync_triage_needed(
        plan,
        state,
        policy=policy,
    )
    if result.triage.injected:
        _log_gate_changes(plan, "sync_triage", {"injected": True})

    result.lifecycle_phase, result.lifecycle_phase_changed = _persist_lifecycle(
        plan,
        state,
        target_strict=target_strict,
    )
    if result.lifecycle_phase_changed:
        _log_gate_changes(
            plan,
            "sync_lifecycle_phase",
            {"phase": result.lifecycle_phase},
        )

    return result


__all__ = ["ReconcileResult", "live_planned_queue_empty", "reconcile_plan"]
