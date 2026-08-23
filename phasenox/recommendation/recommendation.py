def recommend(diagnosis):

    recommendations = []

    for item in diagnosis:

        text = item.lower()

        if "low average vocal pitch" in text:
            recommendations.append(
                "Consider recording closer to the microphone and avoid excessive pitch correction."
            )

        elif "high average vocal pitch" in text:
            recommendations.append(
                "Check for vocal strain and reduce aggressive EQ boosts in the upper mids."
            )

        elif "loudness" in text:
            recommendations.append(
                "Measure integrated LUFS before mastering and compare with your delivery target."
            )

        elif "spectrum" in text:
            recommendations.append(
                "Inspect low, mid and high frequency balance before applying EQ."
            )

    return recommendations