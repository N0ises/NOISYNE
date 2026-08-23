def engineer_report(results):

    report = []

    # ------------------------
    # LUFS
    # ------------------------

    lufs = results.get("lufs")

    if lufs:

        value = lufs.get("integrated_lufs")

        if value is not None:

            report.append("Loudness")
            report.append(f"• Integrated LUFS: {value} LUFS")
            report.append("")

    # ------------------------
    # Spectrum
    # ------------------------

    spectrum = results.get("spectrum")

    if spectrum:

        brightness = spectrum.get("brightness")

        if brightness:

            report.append("Spectrum")
            report.append(f"• Tonal Balance: {brightness.capitalize()}")
            report.append("")

    # ------------------------
    # Pitch
    # ------------------------

    pitch = results.get("pitch")

    if pitch:

        avg = pitch.get("average_pitch")

        if avg:

            report.append("Pitch")
            report.append(f"• Average Pitch: {round(avg)} Hz")
            report.append("")

    return "\n".join(report)