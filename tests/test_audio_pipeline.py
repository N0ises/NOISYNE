from __future__ import annotations

from pathlib import Path

import pytest

from noisyne.audio.pipeline import AudioPipeline


AUDIO_PATH = Path("tests/assets/test.wav")


@pytest.mark.skipif(
    not AUDIO_PATH.exists(),
    reason="Committed fixture tests/assets/test.wav is not available",
)
def test_audio_pipeline_index_and_search():
    pipeline = AudioPipeline()

    pipeline.index(
        AUDIO_PATH,
        audio_id="song_001",
        metadata={
            "title": "Test Song",
            "artist": "SoundBrain",
        },
        document="First indexed audio",
    )

    result = pipeline.search(AUDIO_PATH)

    assert len(result.ids) >= 1, "Search should return at least one indexed audio"
    assert "song_001" in result.ids, "Indexed audio should be found by identity search"
