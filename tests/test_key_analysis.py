from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from phasenox.audio.analysis.key import KeyAnalysis
from phasenox.audio.io.models import AudioData, AudioMetadata


def _audio(chroma: np.ndarray | None = None) -> AudioData:
    samples = np.zeros(1000, dtype=np.float32)
    if chroma is not None and chroma.size:
        # Embed the desired chroma into the sample envelope so the mocked
        # chroma_stft returns exactly it.
        samples = chroma.astype(np.float32).ravel()[:1000]
    return AudioData(
        samples=samples,
        metadata=AudioMetadata(
            path=Path("x.wav"),
            filename="x.wav",
            extension="wav",
            format="wav",
            codec=None,
            sample_rate=48000,
            channels=2,
            duration=1.0,
            bit_depth=16,
            file_size=1000,
        ),
    )


def _chroma_vector(tonic: int, mode: str) -> np.ndarray:
    """Return a clean 12x1 chroma vector for the given tonic + mode.

    Librosa chroma rows are ordered: C, C#, D, D#, E, F, F#, G, G#, A, A#, B.
    """
    chroma = np.zeros((12, 1), dtype=np.float32)
    offsets = [0, 4, 7] if mode == "major" else [0, 3, 7]
    for off in offsets:
        chroma[(tonic + off) % 12, 0] = 1.0
    return chroma


@pytest.fixture
def analyzer() -> KeyAnalysis:
    return KeyAnalysis()


@pytest.mark.parametrize(
    ("tonic", "name", "mode"),
    [
        (0, "C", "major"),
        (0, "C", "minor"),
        (1, "C#", "major"),
        (1, "C#", "minor"),
        (2, "D", "major"),
        (2, "D", "minor"),
        (3, "D#", "major"),
        (3, "D#", "minor"),
        (4, "E", "major"),
        (4, "E", "minor"),
        (5, "F", "major"),
        (5, "F", "minor"),
        (6, "F#", "major"),
        (6, "F#", "minor"),
        (7, "G", "major"),
        (7, "G", "minor"),
        (8, "G#", "major"),
        (8, "G#", "minor"),
        (9, "A", "major"),
        (9, "A", "minor"),
        (10, "A#", "major"),
        (10, "A#", "minor"),
        (11, "B", "major"),
        (11, "B", "minor"),
    ],
)
def test_detects_all_tonics_and_modes(
    analyzer: KeyAnalysis,
    tonic: int,
    name: str,
    mode: str,
    monkeypatch,
):
    expected = f"{name} {mode}"

    def fake_chroma(*, y, sr, **kwargs):
        return _chroma_vector(tonic, mode)

    monkeypatch.setattr("librosa.feature.chroma_stft", fake_chroma)

    result = analyzer.analyze(_audio())
    assert result == expected


def test_silence_or_zero_chroma_returns_unknown(analyzer: KeyAnalysis):
    audio = _audio()
    result = analyzer.analyze(audio)
    assert result == "unknown"
