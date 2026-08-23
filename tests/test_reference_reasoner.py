from __future__ import annotations

from phasenox.reference.models import (
    Category,
    EngineerDecision,
    ReferenceComparison,
    ReferenceIntent,
    Severity,
)
from phasenox.reference.reasoner import ReferenceReasoner


def _comparison() -> ReferenceComparison:
    return ReferenceComparison(
        similarity=100.0,
        confidence=0.94,
        frequency_score=100.0,
        dynamic_score=100.0,
        stereo_score=100.0,
        loudness_score=100.0,
        transient_score=100.0,
        phase_score=100.0,
        tonal_score=100.0,
        semantic_score=100.0,
        band_differences=[],
        engineer_decisions=[],
        metrics=[],
    )


def test_prompt_includes_intent_context():
    reasoner = ReferenceReasoner()
    comparison = _comparison()
    intent = ReferenceIntent(
        genre="pop",
        mood="bright",
        target="streaming",
        focus_areas=["loudness", "dynamics"],
    )

    prompt = reasoner.build_prompt(comparison, intent=intent)

    assert "pop" in prompt
    assert "bright" in prompt
    assert "streaming" in prompt
    assert "loudness" in prompt
    assert "dynamics" in prompt


def test_prompt_includes_comparison_metrics():
    reasoner = ReferenceReasoner()
    comparison = _comparison()

    comparison.reference_similarities = {
        "ref1.wav": 88.0,
        "ref2.wav": 82.0,
    }
    comparison.metric_variance = {"lufs": 1.23}

    prompt = reasoner.build_prompt(comparison)

    assert "88.00" in prompt or "88.0" in prompt
    assert "ref1.wav" in prompt
    assert "lufs" in prompt


def test_reason_uses_intent_to_categorize_decisions():
    reasoner = ReferenceReasoner()
    comparison = _comparison()
    comparison.engineer_decisions = [
        EngineerDecision(
            title="Loudness",
            description="Different.",
            category=Category.LOUDNESS,
            severity=Severity.MEDIUM,
            confidence=0.92,
            recommendation="Adjust limiter.",
        )
    ]

    intent = ReferenceIntent(focus_areas=["loudness"])
    result = reasoner.reason(comparison, intent=intent)

    assert len(result.engineer_decisions) == 1
    assert result.engineer_decisions[0].decision_type.value == "stylistic_difference"
