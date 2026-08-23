from __future__ import annotations

from phasenox.audio.context.models import AudioContext
from phasenox.audio.mix.chains import ProcessingChainRecommender
from phasenox.audio.mix.models import PrioritizedIssue, RootCause, RootCauseResult


def _make_prioritized(
    title: str,
    category: str,
    severity: str,
    order: int,
    recommendation: str = "",
) -> PrioritizedIssue:
    return PrioritizedIssue(
        title=title,
        severity=severity,
        priority_score=0.8,
        user_action_order=order,
        category=category,
        description="",
        recommendation=recommendation or f"address {title}",
        confidence=0.85,
    )


def test_chain_recommender_maps_harsh_to_eq():
    causes = RootCauseResult(causes=[RootCause("harsh high end", ["excess 3 kHz"], "medium", 0.82)])
    issues = [_make_prioritized("harsh high end", "fine tune", "medium", 1)]
    context = AudioContext("full_mix", "file")

    steps = ProcessingChainRecommender().recommend(causes, issues, context)

    assert len(steps) == 1
    assert steps[0].plugin_type == "EQ"
    assert steps[0].target == "frequency_balance"
    assert steps[0].order == 1


def test_chain_recommender_maps_loudness_to_limiter():
    causes = RootCauseResult(
        causes=[RootCause("mix is quieter than target", ["insufficient limiting"], "high", 0.8)]
    )
    issues = [_make_prioritized("loudness below target", "fix first", "high", 1)]
    context = AudioContext("full_mix", "file")

    steps = ProcessingChainRecommender().recommend(causes, issues, context)

    assert steps[0].plugin_type == "Limiter"
    assert steps[0].target == "loudness"


def test_chain_recommender_deduplicates_targets():
    causes = RootCauseResult(causes=[])
    issues = [
        _make_prioritized("harsh vocal highs", "fine tune", "medium", 1),
        _make_prioritized("harsh cymbals", "fine tune", "medium", 2),
    ]
    context = AudioContext("full_mix", "file")

    steps = ProcessingChainRecommender().recommend(causes, issues, context)

    assert len(steps) == 1
    assert steps[0].target == "frequency_balance"
