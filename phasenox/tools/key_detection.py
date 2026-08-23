import numpy as np
import librosa


MAJOR_KEYS = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]


def detect_key(audio_path):
    """
    Detect musical key using chroma features.

    Compatible with librosa 0.11+
    """

    try:
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        chroma = librosa.feature.chroma_cqt(
            y=y,
            sr=sr,
        )

        chroma_mean = np.mean(chroma, axis=1)

        key_index = int(np.argmax(chroma_mean))

        key = MAJOR_KEYS[key_index]

        confidence = float(chroma_mean[key_index] / np.sum(chroma_mean))

        return {
            "success": True,
            "tool": "key_detection",
            "key": key,
            "confidence": round(confidence, 3),
        }

    except Exception as e:

        return {
            "success": False,
            "tool": "key_detection",
            "error": str(e),
        }