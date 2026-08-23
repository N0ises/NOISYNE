import numpy as np
import librosa


def detect_bpm(audio_path):
    """
    Detect BPM using librosa.

    Compatible with librosa 0.11+
    """

    try:
        y, sr = librosa.load(audio_path, sr=None, mono=True)

        tempo, beats = librosa.beat.beat_track(
            y=y,
            sr=sr,
        )

        # librosa >=0.11 may return ndarray
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo.squeeze())

        result = {
            "success": True,
            "tool": "bpm_detection",
            "bpm": round(float(tempo), 2),
            "beat_count": int(len(beats)),
        }

        return result

    except Exception as e:

        return {
            "success": False,
            "tool": "bpm_detection",
            "error": str(e),
        }