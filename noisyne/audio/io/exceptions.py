from __future__ import annotations


class AudioError(Exception):
    """
    Base exception for every audio domain error.
    """


class AudioLoadError(AudioError):
    """
    Raised when an audio file cannot be loaded.
    """


class AudioSaveError(AudioError):
    """
    Raised when an audio file cannot be saved.
    """


class AudioValidationError(AudioError):
    """
    Raised when audio validation fails.
    """


class UnsupportedAudioFormatError(AudioValidationError):
    """
    Raised when the audio format is not supported.
    """


class AudioInspectionError(AudioError):
    """
    Raised when metadata extraction fails.
    """


class AudioProcessingError(AudioError):
    """
    Raised when audio processing fails.
    """