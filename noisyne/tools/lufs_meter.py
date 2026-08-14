import soundfile as sf
import pyloudnorm as pyln
import numpy as np


def detect(audio_path):

    # Read audio
    data, rate = sf.read(audio_path)

    # Convert integer audio to float
    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float32)
        data /= np.iinfo(np.int16).max

    # Create LUFS meter
    meter = pyln.Meter(rate)

    # Measure loudness
    loudness = meter.integrated_loudness(data)

    # Measure peak
    peak = np.max(np.abs(data))

    return {
        "success": True,
        "tool": "lufs_meter",
        "integrated_lufs": round(float(loudness), 2),
        "peak": round(float(peak), 4)
    }


# Backward compatibility
def measure_lufs(audio_path):
    return detect(audio_path)