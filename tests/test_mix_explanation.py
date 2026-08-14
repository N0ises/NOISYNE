from __future__ import annotations

from noisyne.audio.analysis.models import AnalysisResult
from noisyne.audio.context.models import AudioContext
from noisyne.audio.engineer.models import EngineerResult
from noisyne.audio.mix.explanation import ExplanationBuilder
from noisyne.audio.mix.models import ProcessingStep, RootCause


def _make_analysis(**kwargs) -> AnalysisResult:
    defaults = {
        "tempo": 120.0,
        "pitch": "C",
        "key": "C major",
        "lufs": -16.0,
        "peak": -1.0,
        "rms": -18.0,
        "dynamic_range": 7.0,
        "crest_factor": 10.0,
        "stereo_width": 0.5,
        "phase": 0.8,
        "spectral_centroid": 4500.0,
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


def test_explanation_builder_includes_score_and_chain():
    analysis = _make_analysis()
    context = AudioContext("full_mix", "file", is_full_mix=True, confidence=0.9)
    engineer = EngineerResult(score=72.0)
    causes = [RootCause("harsh high end", ["excess 3 kHz"], "medium", 0.82)]
    chain = [ProcessingStep(1, "frequency_balance", "EQ", "cut 3 kHz", "medium", 0.85)]

    explanations = ExplanationBuilder().build(analysis, context, engineer, causes, chain)

    assert any("72/100" in exp for exp in explanations)
    assert any("3 kHz" in exp for exp in explanations)
    assert any("Step 1" in exp for exp in explanations)


def test_explanation_builder_notes_loudness_and_dynamics():
    analysis = _make_analysis(lufs=-18.0, dynamic_range=4.0)
    context = AudioContext("full_mix", "file", is_full_mix=True, confidence=0.85)
    engineer = EngineerResult(score=65.0)

    explanations = ExplanationBuilder().build(analysis, context, engineer, [], [])

    assert any("below a typical streaming target" in exp for exp in explanations)
    assert any("Dynamic range" in exp for exp in explanations)


def test_explanation_builder_returns_score_explanation_when_no_issues():
    analysis = _make_analysis(lufs=-10.0, dynamic_range=10.0, spectral_centroid=2000.0)
    context = AudioContext("full_mix", "file", is_full_mix=True)
    engineer = EngineerResult(score=90.0)

    explanations = ExplanationBuilder().build(analysis, context, engineer, [], [])

    assert any("90/100" in exp for exp in explanations)
