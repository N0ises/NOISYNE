from __future__ import annotations

# Category names used by decision logic. These are abstract identifiers, not brands.
CATEGORY_EQ = "eq"
CATEGORY_COMPRESSOR = "compressor"
CATEGORY_LIMITER = "limiter"
CATEGORY_GAIN = "gain"
CATEGORY_CLIP = "clip"
CATEGORY_IMAGER = "imager"
CATEGORY_TRANSIENT_SHAPER = "transient_shaper"
CATEGORY_SATURATION = "saturation"
CATEGORY_UTILITY = "utility"

CATEGORY_TO_TYPE = {
    CATEGORY_EQ: "EQ",
    CATEGORY_COMPRESSOR: "Compressor",
    CATEGORY_LIMITER: "Limiter",
    CATEGORY_GAIN: "Gain Utility",
    CATEGORY_CLIP: "Gain Utility",
    CATEGORY_IMAGER: "Imager",
    CATEGORY_TRANSIENT_SHAPER: "Transient Shaper",
    CATEGORY_SATURATION: "Saturation",
    CATEGORY_UTILITY: "Utility",
}

PARAMETER_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    CATEGORY_EQ: {
        "frequency": (20.0, 20000.0),
        "gain": (-24.0, 24.0),
        "q": (0.1, 10.0),
    },
    CATEGORY_COMPRESSOR: {
        "threshold": (-60.0, 0.0),
        "ratio": (1.0, 20.0),
        "attack": (0.01, 1000.0),
        "release": (1.0, 5000.0),
        "makeup_gain": (0.0, 24.0),
    },
    CATEGORY_LIMITER: {
        "ceiling": (-3.0, -0.1),
        "release": (1.0, 5000.0),
        "lookahead": (0.0, 20.0),
    },
    CATEGORY_GAIN: {
        "output_gain": (-24.0, 6.0),
    },
    CATEGORY_CLIP: {
        "output_gain": (-24.0, 6.0),
        "ceiling": (-3.0, -0.1),
    },
    CATEGORY_IMAGER: {
        "width": (0.0, 200.0),
        "mono_below_hz": (20.0, 500.0),
    },
    CATEGORY_TRANSIENT_SHAPER: {
        "attack": (-100.0, 100.0),
        "sustain": (-100.0, 100.0),
    },
    CATEGORY_SATURATION: {
        "drive": (0.0, 100.0),
        "mix": (0.0, 100.0),
    },
}
