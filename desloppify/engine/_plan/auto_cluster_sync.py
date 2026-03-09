"""Internal sync helpers for auto-cluster regeneration."""

from __future__ import annotations

from desloppify.engine._plan import stale_policy as stale_policy_mod
from desloppify.engine._plan._sync_context import (
    has_objective_backlog as _has_objective_backlog,
)
from desloppify.engine._plan.auto_cluster_sync_issue import (
    _sync_auto_cluster,
    sync_issue_clusters,
)
from desloppify.engine._plan.constants import SUBJECTIVE_PREFIX
from desloppify.engine._plan.subjective_policy import SubjectiveVisibility
from desloppify.engine._plan.sync_auto_prune import prune_stale_clusters
from desloppify.engine._plan.sync_dimensions import (
    current_under_target_ids,
    current_unscored_ids,
)
from desloppify.engine._state.schema import StateModel

_MIN_CLUSTER_SIZE = 2
_STALE_KEY = "subjective::stale"
_STALE_NAME = "auto/stale-review"
_UNSCORED_KEY = "subjective::unscored"
_UNSCORED_NAME = "auto/initial-review"
_UNDER_TARGET_KEY = "subjective::under-target"
_UNDER_TARGET_NAME = "auto/under-target-review"
_MIN_UNSCORED_CLUSTER_SIZE = 1


def _subjective_state_sets(
    state: StateModel,
    *,
    policy: SubjectiveVisibility | None,
    target_strict: float,
) -> tuple[set, set, set]:
    """Return (stale_ids, under_target_ids, unscored_ids) for subjective cluster logic."""
    if policy is not None:
        unscored_ids = policy.unscored_ids
        stale_ids = policy.stale_ids
        under_target_ids = policy.under_target_ids
    else:
        unscored_ids = current_unscored_ids(state)
        stale_ids = stale_policy_mod.current_stale_ids(
            state, subjective_prefix=SUBJECTIVE_PREFIX
        )
        under_target_ids = current_under_target_ids(state, target_strict=target_strict)
    return stale_ids, under_target_ids, unscored_ids


def sync_subjective_clusters(
    plan: dict,
    state: StateModel,
    issues: dict,
    clusters: dict,
    existing_by_key: dict[str, str],
    active_auto_keys: set[str],
    now: str,
    *,
    target_strict: float,
    policy: SubjectiveVisibility | None = None,
    cycle_just_completed: bool = False,
) -> int:
    """Sync unscored, stale, and under-target subjective dimension clusters."""
    changes = 0

    all_subjective_ids = sorted(
        fid
        for fid in plan.get("queue_order", [])
        if fid.startswith(SUBJECTIVE_PREFIX)
    )

    stale_state_ids, under_target_ids, unscored_state_ids = _subjective_state_sets(
        state, policy=policy, target_strict=target_strict
    )

    unscored_queue_ids = sorted(
        fid for fid in all_subjective_ids if fid in unscored_state_ids
    )
    stale_queue_ids = sorted(
        fid
        for fid in all_subjective_ids
        if fid in stale_state_ids and fid not in unscored_state_ids
    )

    if len(unscored_queue_ids) >= _MIN_UNSCORED_CLUSTER_SIZE:
        active_auto_keys.add(_UNSCORED_KEY)
        cli_keys = [fid.removeprefix(SUBJECTIVE_PREFIX) for fid in unscored_queue_ids]
        description = (
            f"Initial review of {len(unscored_queue_ids)} unscored subjective dimensions"
        )
        action = f"desloppify review --prepare --dimensions {','.join(cli_keys)}"
        changes += _sync_auto_cluster(
            plan,
            clusters,
            existing_by_key,
            cluster_key=_UNSCORED_KEY,
            cluster_name=_UNSCORED_NAME,
            member_ids=unscored_queue_ids,
            description=description,
            action=action,
            now=now,
        )

    if len(stale_queue_ids) >= _MIN_CLUSTER_SIZE:
        active_auto_keys.add(_STALE_KEY)
        cli_keys = [fid.removeprefix(SUBJECTIVE_PREFIX) for fid in stale_queue_ids]
        description = f"Re-review {len(stale_queue_ids)} stale subjective dimensions"
        action = "desloppify review --prepare --dimensions " + ",".join(cli_keys)
        changes += _sync_auto_cluster(
            plan,
            clusters,
            existing_by_key,
            cluster_key=_STALE_KEY,
            cluster_name=_STALE_NAME,
            member_ids=stale_queue_ids,
            description=description,
            action=action,
            now=now,
        )

    under_target_queue_ids = sorted(under_target_ids)

    prev_ut_cluster = clusters.get(_UNDER_TARGET_NAME, {})
    prev_ut_ids = set(prev_ut_cluster.get("issue_ids", []))
    order = plan.get("queue_order", [])
    ut_prune = [
        fid
        for fid in prev_ut_ids
        if fid not in under_target_ids
        and fid not in stale_state_ids
        and fid not in unscored_state_ids
        and fid in order
    ]
    for fid in ut_prune:
        order.remove(fid)
        changes += 1

    has_objective_items = _has_objective_backlog(issues, policy)

    if not has_objective_items and len(under_target_queue_ids) >= _MIN_CLUSTER_SIZE:
        active_auto_keys.add(_UNDER_TARGET_KEY)
        cli_keys = [fid.removeprefix(SUBJECTIVE_PREFIX) for fid in under_target_queue_ids]
        description = (
            f"Consider re-reviewing {len(under_target_queue_ids)} "
            f"dimensions under target score"
        )
        action = "desloppify review --prepare --dimensions " + ",".join(cli_keys)
        changes += _sync_auto_cluster(
            plan,
            clusters,
            existing_by_key,
            cluster_key=_UNDER_TARGET_KEY,
            cluster_name=_UNDER_TARGET_NAME,
            member_ids=under_target_queue_ids,
            description=description,
            action=action,
            now=now,
            optional=True,
        )

        existing_order = set(order)
        for fid in under_target_queue_ids:
            if fid not in existing_order:
                order.append(fid)

    if has_objective_items and not cycle_just_completed:
        objective_evict = [
            fid for fid in order if fid in under_target_ids or fid in stale_state_ids
        ]
        for fid in objective_evict:
            order.remove(fid)
            changes += 1

    return changes


__all__ = ["prune_stale_clusters", "sync_issue_clusters", "sync_subjective_clusters"]
