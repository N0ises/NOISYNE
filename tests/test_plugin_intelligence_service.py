from __future__ import annotations

from noisyne.audio.context.models import AudioContext
from noisyne.audio.mix.models import (
    MixIntelligenceResult,
    PrioritizedIssue,
    RootCause,
)
from noisyne.audio.plugin.service import PluginIntelligenceService


def test_service_analyze_returns_steps():
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
    mix = MixIntelligenceResult(
        root_causes=[cause],
        prioritized_issues=[issue],
        processing_chain=[],
        explanations=[],
        confidence_scores={},
    )
    context = AudioContext("full_mix", "file")

    result = PluginIntelligenceService().analyze(mix, context)

    assert result.goals
    assert result.steps
    assert result.steps[0].plugin_options
    assert result.explanations
