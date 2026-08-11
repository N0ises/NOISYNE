from __future__ import annotations

from pathlib import Path

import pytest

from brain.application.soundbrain_service import (
    AnalysisRequest,
    SoundBrainService,
)
from brain.infrastructure.config import settings


AUDIO_PATH = Path("tests/assets/test.wav")
CLAP_MODEL_DIR = Path(settings.runtime.model_root) / settings.models.clap.name


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
@pytest.mark.skipif(
    not CLAP_MODEL_DIR.exists(),
    reason="CLAP model is not available locally",
)
def test_soundbrain_service_semantic_analysis_enabled():
    """Semantic analysis with CLAP populates semantic_labels when model is present."""
    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        include_semantic_analysis=True,
    )

    service = SoundBrainService()
    response = service.analyze(request)

    assert response.report is not None
    assert isinstance(response.report.semantic_labels, list)
