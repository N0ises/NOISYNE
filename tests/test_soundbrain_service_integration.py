from __future__ import annotations

from pathlib import Path

import pytest

from phasenox.application.phasenox_service import (
    AnalysisRequest,
    PhasenoxService,
)

AUDIO_PATH = Path("tests/assets/test.wav")


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_integration_deterministic():
    """End-to-end deterministic flow with default flags."""
    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        intent="integration test",
        delivery_target="streaming",
    )

    service = PhasenoxService()
    response = service.analyze(request)

    assert response.audio is not None
    assert response.analysis is not None
    assert response.context is not None
    assert response.engineering is not None
    assert response.report is not None

    report = response.report
    assert report.audio_type
    assert report.source_type
    assert isinstance(report.score, float)
    assert isinstance(report.issues, list)
    assert isinstance(report.recommendations, list)
    assert isinstance(report.strengths, list)
    assert response.comparison is None

    # Without reasoning, ai_summary should be the validated intent text.
    assert "integration test" in report.ai_summary or report.ai_summary == ""


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_integration_with_reference():
    """Deterministic flow with reference comparison."""
    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        reference_path=AUDIO_PATH,
    )

    service = PhasenoxService()
    response = service.analyze(request)

    assert response.comparison is not None


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_integration_with_mix_intelligence():
    """Deterministic flow with mix intelligence enabled."""
    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        include_mix_intelligence=True,
    )

    service = PhasenoxService()
    response = service.analyze(request)

    assert response.mix_intelligence is not None
    report = response.report
    assert report.root_causes
    assert report.prioritized_issues
    assert report.processing_chain
    assert report.explanations
    assert report.confidence_scores

    # Reasoning is disabled, so ai_summary should be the validated intent text or empty.
    assert report.ai_summary == "" or "integration" in report.ai_summary.lower()


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_integration_with_plugin_intelligence():
    """Deterministic flow with plugin intelligence enabled."""
    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        include_mix_intelligence=True,
        include_plugin_intelligence=True,
    )

    service = PhasenoxService()
    response = service.analyze(request)

    assert response.mix_intelligence is not None
    assert response.plugin_intelligence is not None
    report = response.report
    assert report.plugin_intelligence is not None
    assert report.plugin_intelligence.goals
    assert report.plugin_intelligence.steps
    assert report.plugin_intelligence.explanations
