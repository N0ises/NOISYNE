from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from phasenox.application.audio_review_service import (
    AudioReviewResult,
    AudioReviewService,
)
from phasenox.application.phasenox_service import (
    AnalysisRequest,
    PhasenoxService,
)
from phasenox.reference.models import ReferenceComparison, ReferenceReport

AUDIO_PATH = Path("tests/assets/test.wav")


def _fake_review_result() -> AudioReviewResult:
    return AudioReviewResult(
        audio=MagicMock(),
        analysis=MagicMock(),
        context=MagicMock(),
        engineering=MagicMock(),
        report=MagicMock(),
    )


class FakeAudioReviewService(AudioReviewService):

    def review(self, request):
        return _fake_review_result()


def _fake_reference_report() -> ReferenceReport:
    return ReferenceReport(
        comparison=ReferenceComparison(
            similarity=88.0,
            confidence=0.95,
            frequency_score=88.0,
            dynamic_score=88.0,
            stereo_score=88.0,
            loudness_score=88.0,
            transient_score=88.0,
            phase_score=88.0,
            tonal_score=88.0,
            semantic_score=88.0,
            band_differences=[],
            engineer_decisions=[],
            metrics=[],
        ),
        summary="test",
        strengths=[],
        weaknesses=[],
        priorities=[],
        next_actions=[],
    )


class FakeReferencePipeline:

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def run(
        self,
        *,
        reference_audio,
        current_audio,
        output_directory=None,
        intent=None,
    ):
        self.calls.append(
            {
                "reference_audio": reference_audio,
                "current_audio": current_audio,
                "output_directory": output_directory,
                "intent": intent,
            }
        )
        return _fake_reference_report()


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_soundbrain_service_analyze():
    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        intent="test analysis",
        delivery_target="streaming",
    )

    service = PhasenoxService()
    response = service.analyze(request)

    assert response.audio is not None
    assert response.analysis is not None
    assert response.context is not None
    assert response.engineering is not None
    assert response.report is not None
    assert response.comparison is None


def test_soundbrain_service_analyze_missing_audio_gracefully():
    request = AnalysisRequest(
        audio_path="tests/does_not_exist.wav",
    )

    service = PhasenoxService()
    with pytest.raises(Exception):  # noqa: B017 — any failure for missing audio is acceptable
        service.analyze(request)


def test_soundbrain_service_module_import_does_not_load_torch():
    """Importing the service module must not load torch or transformers."""
    import subprocess
    import sys

    script = (
        "import sys\n"
        "from phasenox.application.phasenox_service import AnalysisRequest\n"
        "print('torch' in sys.modules, 'transformers' in sys.modules)\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout.strip()
    assert output == "False False", f"heavy modules loaded: {output}"


def test_soundbrain_service_analyze_with_single_reference():
    pipeline = FakeReferencePipeline()
    service = PhasenoxService(
        audio_review_service=FakeAudioReviewService(),
        reference_pipeline=pipeline,
    )

    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        reference_path=AUDIO_PATH,
        reference_genre="pop",
        reference_target="streaming",
        reference_focus=["loudness"],
    )

    response = service.analyze(request)

    assert response.comparison is not None
    assert len(pipeline.calls) == 1
    call = pipeline.calls[0]
    assert call["reference_audio"] == AUDIO_PATH
    assert call["current_audio"] == AUDIO_PATH
    assert call["intent"].genre == "pop"
    assert call["intent"].target == "streaming"
    assert call["intent"].focus_areas == ["loudness"]


def test_soundbrain_service_analyze_with_multiple_references():
    pipeline = FakeReferencePipeline()
    service = PhasenoxService(
        audio_review_service=FakeAudioReviewService(),
        reference_pipeline=pipeline,
    )

    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        reference_path=[AUDIO_PATH, AUDIO_PATH],
        reference_genre="electronic",
        reference_focus=["dynamics", "stereo"],
    )

    response = service.analyze(request)

    assert response.comparison is not None
    call = pipeline.calls[0]
    assert isinstance(call["reference_audio"], list)
    assert len(call["reference_audio"]) == 2
    assert call["intent"].genre == "electronic"
    assert call["intent"].focus_areas == ["dynamics", "stereo"]
