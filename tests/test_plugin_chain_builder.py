from __future__ import annotations

from brain.audio.context.models import AudioContext
from brain.audio.mix.models import (
    MixIntelligenceResult,
    PrioritizedIssue,
    RootCause,
)
from brain.audio.plugin.chain_builder import PluginChainBuilder


def _make_mix_result() -> MixIntelligenceResult:
    issue = PrioritizedIssue(
        title="harsh high end",
        severity="medium",
        priority_score=0.8,
        user_action_order=1,
        category="fine tune",
        description="harsh high end detected",
        recommendation="reduce 3 kHz",
        confidence=0.85,
    )
    cause = RootCause(
        symptom="harsh high end",
        likely_causes=["excess 3 kHz"],
        priority="medium",
        confidence=0.82,
    )
    return MixIntelligenceResult(
        root_causes=[cause],
        prioritized_issues=[issue],
        processing_chain=[],
        explanations=[],
        confidence_scores={"rule_confidence": 0.85},
    )


def test_chain_builder_creates_eq_step():
    context = AudioContext("full_mix", "file")

    result = PluginChainBuilder().build(_make_mix_result(), context)

    assert len(result.goals) == 1
    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.plugin_category == "eq"
    assert step.plugin_type == "EQ"
    assert step.goal.target == "harsh high end"
    assert any(p.name == "frequency" for p in step.parameter_recommendations)
    assert step.plugin_options
    assert result.explanations


def test_chain_builder_deduplicates_categories():
    issue1 = PrioritizedIssue(
        title="harsh highs",
        severity="medium",
        priority_score=0.8,
        user_action_order=1,
        category="fine tune",
        description="harsh highs",
        recommendation="eq",
        confidence=0.85,
    )
    issue2 = PrioritizedIssue(
        title="sibilance",
        severity="medium",
        priority_score=0.7,
        user_action_order=2,
        category="fine tune",
        description="sibilance",
        recommendation="eq",
        confidence=0.80,
    )
    mix = MixIntelligenceResult(
        root_causes=[],
        prioritized_issues=[issue1, issue2],
        processing_chain=[],
        explanations=[],
        confidence_scores={},
    )
    context = AudioContext("full_mix", "file")

    result = PluginChainBuilder().build(mix, context)

    # Distinct EQ targets are preserved; only identical (category, target)
    # duplicates are collapsed.
    assert len(result.steps) == 2
    assert all(step.plugin_category == "eq" for step in result.steps)


def test_chain_builder_limits_to_six_steps():
    issues = [
        PrioritizedIssue(
            title=f"issue {i}",
            severity="medium",
            priority_score=0.8 - i * 0.01,
            user_action_order=i,
            category="fine tune",
            description=f"issue {i}",
            recommendation="fix",
            confidence=0.85,
        )
        for i in range(1, 10)
    ]
    mix = MixIntelligenceResult(
        root_causes=[],
        prioritized_issues=issues,
        processing_chain=[],
        explanations=[],
        confidence_scores={},
    )
    context = AudioContext("full_mix", "file")

    result = PluginChainBuilder().build(mix, context)

    assert len(result.steps) <= 6
