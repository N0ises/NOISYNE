from __future__ import annotations

from enum import StrEnum


class AITask(StrEnum):

    SEMANTIC_AUDIO_SEARCH = "semantic-audio-search"

    MUSIC_UNDERSTANDING = "music-understanding"

    AUDIO_TAGGING = "audio-tagging"

    AUDIO_TRANSCRIPTION = "audio-transcription"

    STEM_SEPARATION = "stem-separation"

    MUSIC_GENERATION = "music-generation"

    MIX_ANALYSIS = "mix-analysis"

    MASTER_ANALYSIS = "master-analysis"

    RECOMMENDATION = "recommendation"