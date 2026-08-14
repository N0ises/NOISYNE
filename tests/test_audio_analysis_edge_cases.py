from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from noisyne.audio.analysis.crest_factor import CrestFactorAnalysis
from noisyne.audio.analysis.dynamic_range import DynamicRangeAnalysis
from noisyne.audio.analysis.key import KeyAnalysis
from noisyne.audio.analysis.lufs import LUFSAnalyzer
from noisyne.audio.analysis.mfcc import MFCCAnalyzer
from noisyne.audio.analysis.models import AnalysisResult
from noisyne.audio.analysis.peak import PeakAnalyzer
from noisyne.audio.analysis.phase import PhaseCorrelationAnalysis
from noisyne.audio.analysis.stereo import StereoWidthAnalysis
from noisyne.audio.analysis.tempo import TempoAnalyzer
from noisyne.audio.context.models import AudioContext
from noisyne.audio.context.rules import ContextRuleEngine
from noisyne.audio.engineer.models import Issue
from noisyne.audio.engineer.rules import RuleEngine
from noisyne.audio.io.models import AudioData, AudioMetadata


def _audio(samples: np.ndarray, sample_rate: int = 44100, channels: int | None = None) -> AudioData:
    if channels is not None and samples.ndim == 1:
        samples = np.column_stack([samples] * channels)
    return AudioData(
        samples=samples,
        metadata=AudioMetadata(
            path=Path("test.wav"),
            filename="test.wav",
            extension=".wav",
            format="wav",
            codec=None,
            sample_rate=sample_rate,
            channels=samples.shape[1] if samples.ndim == 2 else 1,
            duration=len(samples) / sample_rate,
            bit_depth=16,
            file_size=len(samples) * 2,
        ),
    )


def _make_analysis(**kwargs) -> AnalysisResult:
    defaults = {
        "tempo": 120.0,
        "pitch": 440.0,
        "key": "C major",
        "lufs": -14.0,
        "peak": 0.8,
        "rms": 0.2,
        "dynamic_range": 12.0,
        "crest_factor": 6.0,
        "stereo_width": 0.5,
        "phase": 0.9,
        "spectral_centroid": 2000.0,
        "spectral_bandwidth": 2500.0,
        "spectral_rolloff": 4000.0,
        "spectral_flatness": 0.01,
        "spectral_contrast": 20.0,
        "zero_crossing_rate": 0.1,
        "mfcc": [0.0] * 13,
        "chroma": [0.0] * 12,
        "onset_count": 100,
    }
    defaults.update(kwargs)
    return AnalysisResult(**defaults)


class TestTempoNormalization:

    def test_tempo_extracts_scalar_from_ndarray(self, monkeypatch):
        import librosa

        def fake_beat_track(*, y, sr):
            return np.array([128.5]), np.array([])

        monkeypatch.setattr(librosa.beat, "beat_track", fake_beat_track)

        audio = _audio(np.zeros(44100))
        result = TempoAnalyzer().analyze(audio)

        assert isinstance(result, float)
        assert result == pytest.approx(128.5)

    def test_tempo_returns_zero_when_no_beat(self, monkeypatch):
        import librosa

        def fake_beat_track(*, y, sr):
            return 0.0, np.array([])

        monkeypatch.setattr(librosa.beat, "beat_track", fake_beat_track)

        audio = _audio(np.zeros(44100))
        result = TempoAnalyzer().analyze(audio)

        assert result == 0.0


class TestLUFSShortAudio:

    def test_short_audio_returns_nan(self):
        # 100 samples at 48 kHz is far shorter than a BS.1770 block.
        samples = np.random.randn(100).astype(np.float32) * 0.1
        audio = _audio(samples, sample_rate=48000)

        result = LUFSAnalyzer().analyze(audio)

        assert math.isnan(result)


class TestClippingThreshold:

    def test_mix_clipping_uses_pcm_full_scale_threshold(self):
        analysis = _make_analysis(peak=0.99997)

        strengths, issues, _, score = RuleEngine()._evaluate_mix(analysis)

        assert any(i.title == "Clipping" for i in issues)
        assert score == pytest.approx(90.0)

    def test_stem_clipping_uses_pcm_full_scale_threshold(self):
        analysis = _make_analysis(peak=1.0)

        strengths, issues, _, score = RuleEngine()._evaluate_stem(analysis)

        assert any(i.title == "Clipping" for i in issues)
        assert score == pytest.approx(90.0)


class TestSilenceGuard:

    def test_silent_mix_returns_silence_issue(self):
        analysis = _make_analysis(rms=1e-7, lufs=-70.0)

        strengths, issues, _, score = RuleEngine().evaluate(analysis=analysis)

        assert score == pytest.approx(5.0)
        assert any(i.title == "Silence" for i in issues)

    def test_nan_lufs_returns_silence_issue(self):
        analysis = _make_analysis(lufs=float("nan"))

        strengths, issues, _, score = RuleEngine().evaluate(analysis=analysis)

        assert score == pytest.approx(5.0)
        assert any(i.title == "Silence" for i in issues)

    def test_silent_stem_returns_silence_issue(self):
        analysis = _make_analysis(rms=0.0, lufs=-70.0)
        context = AudioContext(audio_type="stem", source_type="isolated_audio", is_full_mix=False)

        strengths, issues, _, score = RuleEngine().evaluate(analysis=analysis, context=context)

        assert score == pytest.approx(5.0)
        assert any(i.title == "Silence" for i in issues)


class TestLoudnessDirection:

    def test_quiet_mix_issues_too_quiet(self):
        analysis = _make_analysis(lufs=-16.0)

        strengths, issues, _, _ = RuleEngine()._evaluate_mix(analysis)

        issue = next(i for i in issues if i.title.startswith("Loudness"))
        assert issue.title == "Loudness too quiet"
        assert "Increase gain" in issue.recommendation

    def test_loud_mix_issues_too_loud(self):
        analysis = _make_analysis(lufs=-8.0)

        strengths, issues, _, _ = RuleEngine()._evaluate_mix(analysis)

        issue = next(i for i in issues if i.title.startswith("Loudness"))
        assert issue.title == "Loudness too loud"
        assert "Reduce output gain" in issue.recommendation

    def test_nan_lufs_skips_loudness_issue(self):
        analysis = _make_analysis(lufs=float("nan"))

        strengths, issues, _, _ = RuleEngine()._evaluate_mix(analysis)

        assert not any(i.title.startswith("Loudness") for i in issues)
        assert any("Loudness could not be measured" in s for s in strengths)


class TestMonoStereoMetrics:

    def test_mono_stereo_width_is_nan(self):
        audio = _audio(np.zeros(44100), channels=1)

        result = StereoWidthAnalysis().analyze(audio)

        assert math.isnan(result)

    def test_mono_phase_is_nan(self):
        audio = _audio(np.zeros(44100), channels=1)

        result = PhaseCorrelationAnalysis().analyze(audio)

        assert math.isnan(result)

    def test_mix_skips_phase_and_width_when_nan(self):
        analysis = _make_analysis(stereo_width=float("nan"), phase=float("nan"))

        strengths, issues, _, score = RuleEngine()._evaluate_mix(analysis)

        assert not any(i.title == "Stereo Width" for i in issues)
        assert not any(i.title == "Phase Correlation" for i in issues)
        assert any("Mono/stereo metrics not applicable" in s for s in strengths)

    def test_nan_stereo_width_does_not_force_stem(self):
        analysis = _make_analysis(
            onset_count=10,
            spectral_centroid=800.0,
            stereo_width=float("nan"),
        )

        context = ContextRuleEngine().detect(analysis)

        assert context.is_full_mix is True
        assert context.audio_type == "mix"


class TestFullMixClassification:

    @pytest.mark.skipif(
        not Path("tests/assets/test.wav").exists(),
        reason="Fixture tests/assets/test.wav is not available",
    )
    def test_real_fixture_classified_as_full_mix(self):
        from noisyne.audio.io import AudioIOService
        from noisyne.audio.analysis.analyzer import AudioAnalyzer

        audio = AudioIOService().load("tests/assets/test.wav")
        analysis = AudioAnalyzer().analyze(audio)
        context = ContextRuleEngine().detect(analysis)

        assert context.is_full_mix is True
        assert context.audio_type == "mix"

    def test_stem_indicators_classify_as_stem(self):
        analysis = _make_analysis(
            onset_count=20,
            spectral_centroid=800.0,
            stereo_width=0.01,
        )

        context = ContextRuleEngine().detect(analysis)

        assert context.is_full_mix is False
        assert context.audio_type == "stem"

    def test_full_mix_with_many_onsets_is_not_stem(self):
        analysis = _make_analysis(
            onset_count=120,
            spectral_centroid=800.0,
            stereo_width=0.01,
        )

        context = ContextRuleEngine().detect(analysis)

        assert context.is_full_mix is True
        assert context.audio_type == "mix"


class TestDynamicRangeVsCrestFactor:

    def test_crest_factor_matches_peak_to_rms(self):
        samples = np.array([0.0, 1.0, 0.0, -1.0, 0.0], dtype=np.float32)
        audio = _audio(samples)

        crest = CrestFactorAnalysis().analyze(audio)

        # crest = peak/rms, peak=1, rms=sqrt(4/5)=~0.894, crest_db ~0.969 dB
        assert crest > 0.0

    def test_dynamic_range_uses_block_envelope(self):
        # Build a signal with clear loud/quiet blocks.
        sr = 44100
        quiet = np.sin(2 * np.pi * 440 * np.arange(sr // 10)) * 0.01
        loud = np.sin(2 * np.pi * 440 * np.arange(sr // 10)) * 0.5
        samples = np.concatenate([quiet, loud]).astype(np.float32)
        audio = _audio(samples, sample_rate=sr)

        dr = DynamicRangeAnalysis().analyze(audio)
        crest = CrestFactorAnalysis().analyze(audio)

        # Block-based DR should be larger than crest factor for this envelope.
        assert dr > crest

    def test_dynamic_range_falls_back_for_short_signal(self):
        samples = np.array([0.5, -0.5, 0.5, -0.5], dtype=np.float32)
        audio = _audio(samples)

        dr = DynamicRangeAnalysis().analyze(audio)
        crest = CrestFactorAnalysis().analyze(audio)

        assert dr == pytest.approx(crest)


class TestKeyDetection:

    def test_key_returns_major_or_minor_string(self, monkeypatch):
        import librosa

        # Force a C-major chroma distribution.
        def fake_chroma_stft(*, y, sr):
            chroma = np.zeros((12, 1), dtype=np.float32)
            chroma[[0, 4, 7], 0] = 1.0
            return chroma

        monkeypatch.setattr(librosa.feature, "chroma_stft", fake_chroma_stft)

        audio = _audio(np.zeros(44100))
        result = KeyAnalysis().analyze(audio)

        assert "major" in result or "minor" in result

    def test_empty_or_zero_chroma_returns_unknown(self, monkeypatch):
        import librosa

        def fake_chroma_stft(*, y, sr):
            return np.zeros((12, 1), dtype=np.float32)

        monkeypatch.setattr(librosa.feature, "chroma_stft", fake_chroma_stft)

        audio = _audio(np.zeros(44100))
        result = KeyAnalysis().analyze(audio)

        assert result == "unknown"


class TestCLAPDownmix:

    def test_encode_audio_downmixes_stereo_before_processing(self):
        from noisyne.audio.embeddings.clap import CLAPEmbedding

        sr = 44100
        left = np.ones(sr, dtype=np.float32) * 0.5
        right = np.ones(sr, dtype=np.float32) * -0.5
        samples = np.column_stack([left, right])
        audio = _audio(samples, sample_rate=sr)

        fake_processor = MagicMock()
        fake_model = MagicMock()
        fake_model.dtype = torch.float32
        fake_assets = MagicMock()
        fake_assets.processor = fake_processor
        fake_assets.model = fake_model
        fake_assets.device = "cpu"

        embed = CLAPEmbedding()
        embed._runtime = MagicMock()
        embed._runtime.load.return_value = fake_assets

        with patch("torchaudio.transforms.Resample") as mock_resample:
            mock_resample.return_value = lambda tensor: tensor

            embed.encode_audio(audio)

        call_kwargs = fake_processor.call_args.kwargs
        audio_arg = call_kwargs["audio"]

        # After downmixing left + right should cancel to ~0.
        assert np.allclose(audio_arg, 0.0, atol=1e-5)
        assert call_kwargs["sampling_rate"] == 48000


class TestMFCCConfig:

    def test_mfcc_defaults_to_config_n_mfcc(self, monkeypatch):
        import librosa

        captured = {}

        def fake_mfcc(*, y, sr, n_mfcc, n_fft, hop_length, **kwargs):
            captured["n_mfcc"] = n_mfcc
            return np.zeros((n_mfcc, 1), dtype=np.float32)

        monkeypatch.setattr(librosa.feature, "mfcc", fake_mfcc)

        audio = _audio(np.zeros(44100))
        MFCCAnalyzer().analyze(audio)

        assert captured["n_mfcc"] == 13
