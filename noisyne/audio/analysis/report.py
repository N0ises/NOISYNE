from __future__ import annotations

from noisyne.audio.analysis.models import AnalysisResult


class AnalysisReport:

    def build(
        self,
        analysis: AnalysisResult,
    ) -> str:

        lines = [
            "",
            "========== SoundBrain Analysis ==========",
            "",
            f"Tempo               : {analysis.tempo:.2f} BPM",
            f"Pitch               : {analysis.pitch}",
            f"Key                 : {analysis.key}",
            "",
            f"LUFS                : {analysis.lufs:.2f}",
            f"Peak                : {analysis.peak:.4f}",
            f"RMS                 : {analysis.rms:.4f}",
            "",
            f"Dynamic Range       : {analysis.dynamic_range:.2f} dB",
            f"Crest Factor        : {analysis.crest_factor:.2f} dB",
            "",
            f"Stereo Width        : {analysis.stereo_width:.4f}",
            f"Phase Correlation   : {analysis.phase:.4f}",
            "",
            f"Spectral Centroid   : {analysis.spectral_centroid:.2f} Hz",
            f"Spectral Bandwidth  : {analysis.spectral_bandwidth:.2f} Hz",
            f"Spectral Rolloff    : {analysis.spectral_rolloff:.2f} Hz",
            f"Spectral Flatness   : {analysis.spectral_flatness:.6f}",
            f"Spectral Contrast   : {analysis.spectral_contrast:.2f}",
            f"Zero Crossing Rate  : {analysis.zero_crossing_rate:.6f}",
            "",
            f"MFCC Count          : {len(analysis.mfcc)}",
            f"Chroma Count        : {len(analysis.chroma)}",
            f"Onsets              : {analysis.onset_count}",
            "",
            "=========================================",
        ]

        return "\n".join(lines)