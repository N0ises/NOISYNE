from brain.pipeline import analyze_audio
from brain.diagnosis.diagnosis import diagnose
from brain.recommendation.recommendation import recommend

results = analyze_audio("tests/assets/test.wav")

diagnosis = diagnose(results)

recommendations = recommend(diagnosis)

print(recommendations)