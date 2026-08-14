def diagnose(results):

    diagnosis = []

    # ------------------------
    # LUFS
    # ------------------------

    lufs = results.get("lufs")

    if lufs:

        value = lufs.get("integrated_lufs")

        if value is not None:
            diagnosis.append(f"Integrated LUFS: {value} LUFS")

    # ------------------------
    # Spectrum
    # ------------------------

    spectrum = results.get("spectrum")

    if spectrum:

        brightness = spectrum.get("brightness")

        if brightness:
            diagnosis.append(
                f"Spectrum indicates a {brightness} tonal balance."
            )

    # ------------------------
    # Pitch
    # ------------------------

    pitch = results.get("pitch")

    if pitch:

        avg = pitch.get("average_pitch")

        if avg:
            diagnosis.append(
                f"Average vocal pitch: {round(avg)} Hz."
            )

    return diagnosis