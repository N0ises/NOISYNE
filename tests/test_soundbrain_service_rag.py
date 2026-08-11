from __future__ import annotations

from pathlib import Path

import pytest

from brain.application.soundbrain_service import (
    AnalysisRequest,
    SoundBrainService,
)


AUDIO_PATH = Path("tests/assets/test.wav")


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_rag_does_not_crash_when_empty():
    """RAG retrieval enabled with an empty/missing collection must not break the flow."""
    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        intent="mastering check",
        include_rag=True,
    )

    service = SoundBrainService()
    response = service.analyze(request)

    assert response.report is not None
    assert response.analysis is not None
