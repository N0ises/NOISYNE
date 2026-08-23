import librosa
import numpy as np


def analyze_spectrum(audio_path):

    y, sr = librosa.load(audio_path, sr=None, mono=True)

    spectrum = np.abs(np.fft.rfft(y))
    freqs = np.fft.rfftfreq(len(y), 1 / sr)

    low = spectrum[(freqs >= 20) & (freqs < 250)]
    mid = spectrum[(freqs >= 250) & (freqs < 4000)]
    high = spectrum[(freqs >= 4000) & (freqs < 20000)]

    low_energy = float(np.mean(low)) if len(low) else 0
    mid_energy = float(np.mean(mid)) if len(mid) else 0
    high_energy = float(np.mean(high)) if len(high) else 0

    dominant_frequency = float(freqs[np.argmax(spectrum)])

    centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())

    bandwidth = float(librosa.feature.spectral_bandwidth(y=y, sr=sr).mean())

    rolloff = float(librosa.feature.spectral_rolloff(y=y, sr=sr).mean())

    zcr = float(librosa.feature.zero_crossing_rate(y).mean())

    if centroid < 1500:
        brightness = "warm"

    elif centroid < 3000:
        brightness = "balanced"

    else:
        brightness = "bright"

    return {

        "success": True,

        "tool": "spectrum_analysis",

        "low_energy": round(low_energy, 2),

        "mid_energy": round(mid_energy, 2),

        "high_energy": round(high_energy, 2),

        "dominant_frequency": round(dominant_frequency, 2),

        "spectral_centroid": round(centroid, 2),

        "spectral_bandwidth": round(bandwidth, 2),

        "spectral_rolloff": round(rolloff, 2),

        "zero_crossing_rate": round(zcr, 4),

        "brightness": brightness

    }


# backward compatibility
def spectrum(audio_path):
    return analyze_spectrum(audio_path)