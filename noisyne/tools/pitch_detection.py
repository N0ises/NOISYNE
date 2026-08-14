import librosa
import numpy as np


def detect_pitch(audio_path):

    y, sr = librosa.load(audio_path, sr=None)

    pitches, magnitudes = librosa.piptrack(
        y=y,
        sr=sr
    )

    detected = []

    for i in range(pitches.shape[1]):

        index = magnitudes[:, i].argmax()

        pitch = pitches[index, i]

        if pitch > 0:
            detected.append(float(pitch))

    if len(detected) == 0:

        return {
            "success": False,
            "tool": "pitch_detection",
            "summary": "No pitch detected.",
            "data": None
        }

    average_pitch = float(np.mean(detected))

    minimum_pitch = float(np.min(detected))

    maximum_pitch = float(np.max(detected))

    return {

        "success": True,

        "tool": "pitch_detection",

        "summary": f"Average pitch is {average_pitch:.2f} Hz.",

        "data": {

            "average_pitch": average_pitch,

            "min_pitch": minimum_pitch,

            "max_pitch": maximum_pitch,

            "samples": len(detected)

        }

    }