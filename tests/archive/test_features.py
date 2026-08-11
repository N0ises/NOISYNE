from brain.tools.pitch_detection import detect_pitch
from brain.audio.features import extract_features

pitch = detect_pitch("tests/assets/test.wav")

features = extract_features(pitch)

print(features)