from __future__ import annotations

from phasenox.audio.analysis.models import AnalysisResult
from phasenox.audio.context.models import AudioContext
from phasenox.audio.engineer.models import EngineerResult, Issue
from phasenox.audio.mix.models import RootCauseResult
from phasenox.audio.mix.root_cause import RootCauseAnalyzer


def _make_analysis(**kwargs) -> AnalysisResult:
    defaults = {
        "tempo": 120.0,
        "pitch": "C",
        "key": "C major",
        "lufs": -14.0,
        "peak": -1.0,
        "rms": -18.0,
        "dynamic_range": 8.0,
        "crest_factor": 10.0,
        "stereo_width": 0.5,
        "phase": 0.8,
        "spectral_centroid": 4000.0,
        "spectral_bandwidth": 2000.0,
        "spectral_rolloff": 8000.0,
        "spectral_flatness": 0.1,
        "spectral_contrast": 0.5,
        "zero_crossing_rate": 0.05,
        "mfcc": [0.0] * 13,
        "chroma": [0.0] * 12,
        "onset_count": 100,
    }
    defaults.update(kwargs)
    return AnalysisResult(**defaults)


def _make_context(**kwargs) -> AudioContext:
    defaults = {
        "audio_type": "full_mix",
        "source_type": "file",
        "detected_elements": [],
        "instrument": None,
        "semantic_labels": [],
        "is_full_mix": True,
        "confidence": 0.9,
        "notes": [],
    }
    defaults.update(kwargs)
    return AudioContext(**defaults)


def _make_engineer(issues=None) -> EngineerResult:
    return EngineerResult(
        score=75.0,
        strengths=[],
        issues=issues or [],
        recommendations=[],
        confidence_scores={},
    )


def test_root_cause_detects_harsh_highs():
    issue = Issue(
        title="harsh high end",
        severity="medium",
        description="test",
        recommendation="test",
        confidence=0.85,
    )
    engineer = _make_engineer([issue])
    analysis = _make_analysis(spectral_centroid=6000.0)
    context = _make_context(notes=["harsh"])

    result = RootCauseAnalyzer().analyze(analysis, context, engineer)

    assert isinstance(result, RootCauseResult)
    assert any("harsh" in cause.symptom.lower() for cause in result.causes)
    assert result.confidence_scores
    assert "final_confidence" in result.confidence_scores


def test_root_cause_detects_over_compression():
    issue = Issue(
        title="flat dynamics",
        severity="high",
        description="test",
        recommendation="test",
        confidence=0.85,
    )
    engineer = _make_engineer([issue])
    analysis = _make_analysis(dynamic_range=4.0, lufs=-10.0)
    context = _make_context()

    result = RootCauseAnalyzer().analyze(analysis, context, engineer)

    assert any("dynamic" in cause.symptom.lower() for cause in result.causes)


def test_root_cause_detects_loudness_shortfall():
    issue = Issue(
        title="loudness below target",
        severity="high",
        description="test",
        recommendation="test",
        confidence=0.85,
    )
    engineer = _make_engineer([issue])
    analysis = _make_analysis(lufs=-18.0)
    context = _make_context(is_full_mix=True)

    result = RootCauseAnalyzer().analyze(analysis, context, engineer)

    assert any("quiet" in cause.symptom.lower() for cause in result.causes)


def test_root_cause_detects_narrow_stereo():
    issue = Issue(
        title="mono compatibility issue",
        severity="medium",
        description="test",
        recommendation="test",
        confidence=0.85,
    )
    engineer = _make_engineer([issue])
    analysis = _make_analysis(stereo_width=0.2, phase=0.4)
    context = _make_context()

    result = RootCauseAnalyzer().analyze(analysis, context, engineer)

    assert any("stereo" in cause.symptom.lower() for cause in result.causes)


def test_root_cause_returns_default_for_clean_mix():
    engineer = _make_engineer([])
    analysis = _make_analysis()
    context = _make_context()

    result = RootCauseAnalyzer().analyze(analysis, context, engineer)

    assert result.causes
    assert "no strong root-cause indicators" in result.causes[0].symptom.lower()
