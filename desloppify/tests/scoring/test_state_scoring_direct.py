"""Direct coverage for the public state scoring facade."""

from __future__ import annotations

import desloppify.state_scoring as state_scoring_mod


def test_score_snapshot_loads_all_canonical_scores(monkeypatch) -> None:
    state = {"issues": {}}
    monkeypatch.setattr(state_scoring_mod, "get_overall_score", lambda _state: 81.0)
    monkeypatch.setattr(state_scoring_mod, "get_objective_score", lambda _state: 73.0)
    monkeypatch.setattr(state_scoring_mod, "get_strict_score", lambda _state: 69.0)
    monkeypatch.setattr(state_scoring_mod, "get_verified_strict_score", lambda _state: 64.0)

    snapshot = state_scoring_mod.score_snapshot(state)
    assert snapshot == state_scoring_mod.ScoreSnapshot(
        overall=81.0,
        objective=73.0,
        strict=69.0,
        verified=64.0,
    )
    assert "score_snapshot" in state_scoring_mod.__all__
    assert "suppression_metrics" in state_scoring_mod.__all__
