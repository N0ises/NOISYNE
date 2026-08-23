from __future__ import annotations

import pytest

from phasenox.audio.engineer.models import EngineerResult, Issue
from phasenox.audio.mix.models import RootCause, RootCauseResult
from phasenox.audio.mix.priority import PriorityEngine


def _make_engineer(issues) -> EngineerResult:
    return EngineerResult(
        score=70.0,
        strengths=[],
        issues=issues,
        recommendations=[],
        confidence_scores={},
    )


def test_priority_engine_orders_critical_first():
    issues = [
        Issue("clipping", "critical", "peaks above 0 dB", "use a limiter"),
        Issue("harsh highs", "medium", "too bright", "reduce 3 kHz"),
    ]
    root_causes = RootCauseResult(
        causes=[
            RootCause("clipping", ["gain staging too hot"], "high", 0.9),
            RootCause("harsh highs", ["excess 3 kHz"], "medium", 0.8),
        ]
    )

    result = PriorityEngine().prioritize(_make_engineer(issues), root_causes)

    assert result[0].title == "clipping"
    assert result[0].user_action_order == 1
    assert result[0].category == "fix first"
    assert result[1].category == "fine tune"


def test_priority_engine_computes_scores():
    issues = [Issue("loudness mismatch", "high", "too quiet", "raise gain")]
    root_causes = RootCauseResult(causes=[])

    result = PriorityEngine().prioritize(_make_engineer(issues), root_causes)

    assert result[0].priority_score > 0.0
    assert result[0].confidence == 0.85
    assert result[0].user_action_order == 1


def test_priority_engine_includes_confidence_from_cause():
    issues = [Issue("harsh highs", "medium", "too bright", "reduce 3 kHz")]
    root_causes = RootCauseResult(
        causes=[RootCause("harsh highs", ["excess 3 kHz"], "medium", 0.95)]
    )

    result = PriorityEngine().prioritize(_make_engineer(issues), root_causes)

    assert result[0].confidence == pytest.approx(0.90, rel=0.01)
