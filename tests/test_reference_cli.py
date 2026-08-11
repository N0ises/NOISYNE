from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import main
from brain.application.audio_review_service import AudioReviewService
from brain.reference.engine import ReferenceEngine
from brain.reference.models import ReferenceComparison, ReferenceReport


def _reference_report() -> ReferenceReport:
    return ReferenceReport(
        comparison=ReferenceComparison(
            similarity=87.5,
            confidence=0.95,
            frequency_score=88.0,
            dynamic_score=87.0,
            stereo_score=90.0,
            loudness_score=86.0,
            transient_score=87.0,
            phase_score=92.0,
            tonal_score=88.0,
            semantic_score=85.0,
            band_differences=[],
            engineer_decisions=[],
            metrics=[],
        ),
        summary="Reference comparison complete.",
        strengths=[],
        weaknesses=[],
        priorities=[],
        next_actions=[],
    )


def _compare_files_multiple(
    self,
    reference_audio,
    current_audio,
    *,
    intent=None,
) -> ReferenceReport:
    report = _reference_report()
    report.intent = intent
    return report


def test_reference_command_exports_reference_reports(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Exercise CLI -> service -> pipeline -> real report exporter."""
    monkeypatch.setattr(
        ReferenceEngine,
        "compare_files_multiple",
        _compare_files_multiple,
    )
    monkeypatch.setattr(
        AudioReviewService,
        "review",
        lambda self, request: SimpleNamespace(
            audio=MagicMock(),
            analysis=MagicMock(),
            context=MagicMock(),
            engineering=MagicMock(),
            report=MagicMock(),
        ),
    )
    output_directory = tmp_path / "reference-output"

    exit_code = main.main(
        [
            "reference",
            "tests/assets/test.wav",
            "tests/assets/test.wav",
            "--genre",
            "pop",
            "--target",
            "streaming",
            "--output",
            str(output_directory),
        ]
    )

    assert exit_code == 0

    json_path = output_directory / "reference_report.json"
    markdown_path = output_directory / "reference_report.md"
    assert json_path.is_file()
    assert markdown_path.is_file()

    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert "comparison" in report
    assert "similarity" in report["comparison"]
    assert report["intent"]["genre"] == "pop"
    assert report["intent"]["target"] == "streaming"
    assert markdown_path.read_text(encoding="utf-8")
