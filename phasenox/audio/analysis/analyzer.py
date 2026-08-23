from __future__ import annotations

from phasenox.audio.io.models import AudioData

from .models import AnalysisResult

from .peak import PeakAnalyzer
from .rms import RMSAnalyzer
from .tempo import TempoAnalyzer
from .pitch import PitchAnalyzer
from .lufs import LUFSAnalyzer
from .mfcc import MFCCAnalyzer
from .chroma import ChromaAnalyzer

from .dynamic_range import DynamicRangeAnalysis
from .crest_factor import CrestFactorAnalysis

from .stereo import StereoWidthAnalysis
from .phase import PhaseCorrelationAnalysis

from .spectral_centroid import SpectralCentroidAnalysis
from .spectral_bandwidth import SpectralBandwidthAnalysis
from .spectral_rolloff import SpectralRolloffAnalysis
from .spectral_flatness import SpectralFlatnessAnalysis
from .spectral_contrast import SpectralContrastAnalysis
from .zero_crossing import ZeroCrossingRateAnalysis

from .key import KeyAnalysis
from .onset import OnsetAnalysis


class AudioAnalyzer:

    def __init__(
        self,
    ) -> None:

        self._peak = PeakAnalyzer()
        self._rms = RMSAnalyzer()
        self._tempo = TempoAnalyzer()
        self._pitch = PitchAnalyzer()
        self._lufs = LUFSAnalyzer()

        self._mfcc = MFCCAnalyzer()
        self._chroma = ChromaAnalyzer()

        self._dynamic = DynamicRangeAnalysis()
        self._crest = CrestFactorAnalysis()

        self._stereo = StereoWidthAnalysis()
        self._phase = PhaseCorrelationAnalysis()

        self._centroid = SpectralCentroidAnalysis()
        self._bandwidth = SpectralBandwidthAnalysis()
        self._rolloff = SpectralRolloffAnalysis()
        self._flatness = SpectralFlatnessAnalysis()
        self._contrast = SpectralContrastAnalysis()
        self._zcr = ZeroCrossingRateAnalysis()

        self._key = KeyAnalysis()
        self._onset = OnsetAnalysis()

    def analyze(
        self,
        audio: AudioData,
    ) -> AnalysisResult:

        mfcc = self._mfcc.analyze(audio).mean(axis=1)
        chroma = self._chroma.analyze(audio).mean(axis=1)
        onsets = self._onset.analyze(audio)

        return AnalysisResult(
            tempo=self._tempo.analyze(audio),
            pitch=self._pitch.analyze(audio),
            key=self._key.analyze(audio),
            lufs=self._lufs.analyze(audio),
            peak=self._peak.analyze(audio),
            rms=self._rms.analyze(audio),
            dynamic_range=self._dynamic.analyze(audio),
            crest_factor=self._crest.analyze(audio),
            stereo_width=self._stereo.analyze(audio),
            phase=self._phase.analyze(audio),
            spectral_centroid=self._centroid.analyze(audio),
            spectral_bandwidth=self._bandwidth.analyze(audio),
            spectral_rolloff=self._rolloff.analyze(audio),
            spectral_flatness=self._flatness.analyze(audio),
            spectral_contrast=self._contrast.analyze(audio),
            zero_crossing_rate=self._zcr.analyze(audio),
            mfcc=mfcc.tolist() if hasattr(mfcc, "tolist") else list(mfcc),
            chroma=chroma.tolist() if hasattr(chroma, "tolist") else list(chroma),
            onset_count=len(onsets),
        )