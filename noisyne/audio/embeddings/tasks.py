from __future__ import annotations

from enum import StrEnum


class EmbeddingTask(StrEnum):

    SEMANTIC_SEARCH = "semantic-search"

    AUDIO_TEXT = "audio-text"

    MUSIC_UNDERSTANDING = "music-understanding"

    SPEECH_UNDERSTANDING = "speech-understanding"

    CLASSIFICATION = "classification"

    TAGGING = "tagging"

    RETRIEVAL = "retrieval"

    GENERATION = "generation"