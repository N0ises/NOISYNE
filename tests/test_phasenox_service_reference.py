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
from phasenox.reference.models import (
    ReferenceComparison,
    ReferenceReport,
)

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


def _fake_comparison() -> ReferenceComparison:
    return ReferenceComparison(
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
        references=[],
        reference_similarities={},
        metric_variance={},
        segment_deviations=[],
    )


def _fake_reference_report() -> ReferenceReport:
    return ReferenceReport(
        comparison=_fake_comparison(),
        summary="test",
        strengths=[],
        weaknesses=[],
        priorities=[],
        next_actions=[],
    )


class FakeReferencePipeline:

    def __init__(self, *, multi: bool = False) -> None:
        self._multi = multi
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


def test_phasenox_service_single_reference():
    service = PhasenoxService(
        audio_review_service=FakeAudioReviewService(),
        reference_pipeline=FakeReferencePipeline(),
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
    assert response.comparison.similarity == 88.0
    assert len(service._reference_pipeline.calls) == 1
    call = service._reference_pipeline.calls[0]
    assert call["reference_audio"] == AUDIO_PATH
    assert call["current_audio"] == AUDIO_PATH
    assert call["intent"].genre == "pop"
    assert call["intent"].target == "streaming"
    assert call["intent"].focus_areas == ["loudness"]


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="No test audio file is available",
)
def test_phasenox_service_multiple_references():
    service = PhasenoxService(
        audio_review_service=FakeAudioReviewService(),
        reference_pipeline=FakeReferencePipeline(multi=True),
    )

    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        reference_path=[AUDIO_PATH, AUDIO_PATH],
        reference_genre="electronic",
        reference_focus=["dynamics", "stereo"],
    )

    response = service.analyze(request)

    assert response.comparison is not None
    call = service._reference_pipeline.calls[0]
    assert isinstance(call["reference_audio"], list)
    assert len(call["reference_audio"]) == 2
    assert call["intent"].genre == "electronic"
    assert call["intent"].focus_areas == ["dynamics", "stereo"]


def test_phasenox_service_reference_failure_is_graceful():
    class BrokenReferencePipeline:
        def run(self, **kwargs):
            raise RuntimeError("reference engine down")

    service = PhasenoxService(
        audio_review_service=FakeAudioReviewService(),
        reference_pipeline=BrokenReferencePipeline(),
    )

    request = AnalysisRequest(
        audio_path=AUDIO_PATH,
        reference_path=AUDIO_PATH,
    )

    response = service.analyze(request)

    assert response.comparison is None
    assert response.report is not None
