from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ._serialization import JsonContract
from .common import _require_identifier

BRIGHTNESS_CORRELATE_METHOD_ID = "noisyne.brightness_power_spectral_centroid_correlate"
BRIGHTNESS_CORRELATE_METHOD_VERSION = "1.0.0"


class DescriptorClass(str, Enum):
    """Scientific status of a descriptor name, independent of implementation state."""

    STANDARDIZED = "standardized"
    RESEARCH_CORRELATE = "research_correlate"
    INFORMAL_ENGINEERING_TERM = "informal_engineering_term"


class DescriptorImplementationState(str, Enum):
    """Why a descriptor is executable or deliberately unavailable in Sprint 5."""

    IMPLEMENTED = "implemented"
    UNAVAILABLE_STANDARD_MATERIAL = "unavailable_standard_material"
    UNAVAILABLE_PREREQUISITE = "unavailable_prerequisite"
    UNAVAILABLE_NO_VALIDATED_MODEL = "unavailable_no_validated_model"


@dataclass(frozen=True, slots=True)
class DescriptorDefinition(JsonContract):
    """Auditable taxonomy entry; it never implies that a numerical result exists."""

    descriptor_id: str
    descriptor_class: DescriptorClass
    authoritative_references: list[str]
    physical_acoustic_correlates: list[str]
    psychoacoustic_model_dependency: str
    standardized_unit: str | None
    calibration_requirement: str
    valid_input_conditions: list[str]
    implementation_state: DescriptorImplementationState
    limitations: list[str]
    prohibited_claims: list[str]

    def __post_init__(self) -> None:
        _require_identifier(self.descriptor_id, "descriptor_id")
        for field_name in (
            "authoritative_references",
            "physical_acoustic_correlates",
            "valid_input_conditions",
            "limitations",
            "prohibited_claims",
        ):
            values = getattr(self, field_name)
            if not values:
                raise ValueError(f"{field_name} must not be empty")
            for value in values:
                _require_identifier(value, field_name)
        _require_identifier(self.psychoacoustic_model_dependency, "psychoacoustic_model_dependency")
        _require_identifier(self.calibration_requirement, "calibration_requirement")
        if self.standardized_unit is not None:
            _require_identifier(self.standardized_unit, "standardized_unit")
        if (
            self.descriptor_class is not DescriptorClass.STANDARDIZED
            and self.standardized_unit is not None
        ):
            raise ValueError("only standardized descriptors may declare a standardized unit")


def descriptor_taxonomy() -> tuple[DescriptorDefinition, ...]:
    """Return the frozen Sprint 5 descriptor classification in stable order."""

    return (
        DescriptorDefinition(
            descriptor_id="sharpness",
            descriptor_class=DescriptorClass.STANDARDIZED,
            authoritative_references=["DIN 45692:2009-08"],
            physical_acoustic_correlates=[
                "First moment of a weighted specific-loudness distribution on the critical-band-rate scale."
            ],
            psychoacoustic_model_dependency=(
                "Complete DIN 45692 method and validated DIN 45631 / ISO 532-1-style "
                "Zwicker specific loudness."
            ),
            standardized_unit="acum",
            calibration_requirement=(
                "Standard-defined listening/input conditions and validated specific loudness are required."
            ),
            valid_input_conditions=[
                "Inputs meeting the complete DIN 45692 requirements and its referenced loudness method."
            ],
            implementation_state=DescriptorImplementationState.UNAVAILABLE_PREREQUISITE,
            limitations=[
                "The complete paid German standard and WAV material are not available locally.",
                "PHASENOX has no validated ISO 532-1 specific-loudness engine.",
            ],
            prohibited_claims=[
                "Do not label spectral centroid, high-frequency energy, or ERB centroid as sharpness.",
                "Do not report acum without the complete validated DIN method.",
            ],
        ),
        DescriptorDefinition(
            descriptor_id="roughness",
            descriptor_class=DescriptorClass.STANDARDIZED,
            authoritative_references=[
                "DIN 38455:2024-11",
                "ECMA-418-2, 4th edition, June 2025, Clause 7",
            ],
            physical_acoustic_correlates=[
                "Rapid within-critical-band envelope modulation, method-dependent weighting and specific loudness."
            ],
            psychoacoustic_model_dependency=(
                "DIN 38455 model and supplements, or the complete ECMA-418-2 Sottek Hearing Model."
            ),
            standardized_unit="asper",
            calibration_requirement=(
                "Calibrated sound pressure and the selected standard's full measurement/model conditions."
            ),
            valid_input_conditions=[
                "Keep DIN 38455 and ECMA-418-2 algorithm identity and input compliance separate."
            ],
            implementation_state=DescriptorImplementationState.UNAVAILABLE_PREREQUISITE,
            limitations=[
                "DIN 38455 and its executable supplements are not available locally.",
                "The 53-band Sottek Hearing Model and independent ECMA validation fixtures are not implemented.",
            ],
            prohibited_claims=[
                "Do not call an envelope FFT with a 70 Hz weighting standardized roughness.",
                "Do not conflate DIN 38455 and ECMA-418-2 roughness.",
            ],
        ),
        DescriptorDefinition(
            descriptor_id="fluctuation_strength",
            descriptor_class=DescriptorClass.STANDARDIZED,
            authoritative_references=["ECMA-418-2, 4th edition, June 2025, Clause 9"],
            physical_acoustic_correlates=[
                "Slow within-critical-band envelope modulation evaluated by high-resolution spectral analysis."
            ],
            psychoacoustic_model_dependency="Complete ECMA-418-2 Sottek Hearing Model and Clause 9 HSA procedure.",
            standardized_unit="vacilHMS",
            calibration_requirement="Calibrated pressure, 48 kHz processing, and declared ECMA-74 input compliance.",
            valid_input_conditions=[
                "ECMA-418-2 uses modulation rates from approximately 0.25 Hz to 20 Hz."
            ],
            implementation_state=DescriptorImplementationState.UNAVAILABLE_PREREQUISITE,
            limitations=[
                "The prerequisite hearing model and Clause 9 validation implementation are absent."
            ],
            prohibited_claims=[
                "Do not report vacilHMS from a standalone 4 Hz modulation detector.",
                "Do not claim ECMA conformance for ordinary music files.",
            ],
        ),
        DescriptorDefinition(
            descriptor_id="tonality",
            descriptor_class=DescriptorClass.STANDARDIZED,
            authoritative_references=["ECMA-418-2, 4th edition, June 2025, Clause 6"],
            physical_acoustic_correlates=[
                "Autocorrelation-derived tonal partial loudness relative to noise partial loudness."
            ],
            psychoacoustic_model_dependency="Complete ECMA-418-2 Sottek Hearing Model and Clause 6 procedure.",
            standardized_unit="tuHMS",
            calibration_requirement="Calibrated pressure, 48 kHz processing, and declared ECMA-74 input compliance.",
            valid_input_conditions=[
                "Use the ECMA psychoacoustic method distinctly from TNR, prominence ratio, and ISO/TS 20065."
            ],
            implementation_state=DescriptorImplementationState.UNAVAILABLE_PREREQUISITE,
            limitations=[
                "The prerequisite specific-loudness and tonality stages are not implemented."
            ],
            prohibited_claims=[
                "Do not merge unrelated tone-audibility methods into a generic tonality score.",
                "Do not report tuHMS from spectral peak prominence alone.",
            ],
        ),
        DescriptorDefinition(
            descriptor_id="brightness",
            descriptor_class=DescriptorClass.RESEARCH_CORRELATE,
            authoritative_references=[
                "Saitis and Siedenburg, JASA 148(4), 2020, DOI 10.1121/10.0002275",
                "Marozeau and de Cheveigne, JASA 121(1), 2007, DOI 10.1121/1.2384910",
            ],
            physical_acoustic_correlates=[
                "Linear-frequency power spectral centroid of the signal's spectral distribution."
            ],
            psychoacoustic_model_dependency=(
                "No universal brightness model; spectral centroid is an evidence-backed correlate only."
            ),
            standardized_unit=None,
            calibration_requirement=(
                "No SPL calibration is required for this relative spectral-distribution measurement."
            ),
            valid_input_conditions=[
                "Finite digital audio with positive analyzed spectral power and known sample rate/bandwidth."
            ],
            implementation_state=DescriptorImplementationState.IMPLEMENTED,
            limitations=[
                "Brightness perception also depends on F0, attack/time behavior, stimulus, and context.",
                "The measurement is bandwidth- and sample-rate-dependent.",
            ],
            prohibited_claims=[
                "Do not call the centroid a universal perceived-brightness scale or normalize it to a score.",
                "Do not infer a source within a full mix.",
            ],
        ),
        *(
            DescriptorDefinition(
                descriptor_id=descriptor_id,
                descriptor_class=DescriptorClass.INFORMAL_ENGINEERING_TERM,
                authoritative_references=[
                    "No generally validated, standardized operational definition selected for Sprint 5."
                ],
                physical_acoustic_correlates=list(correlates),
                psychoacoustic_model_dependency=(
                    "A future descriptor-specific validated perceptual model and listening context are required."
                ),
                standardized_unit=None,
                calibration_requirement="Model-dependent; not established in Sprint 5.",
                valid_input_conditions=["No valid numerical input domain is claimed in Sprint 5."],
                implementation_state=DescriptorImplementationState.UNAVAILABLE_NO_VALIDATED_MODEL,
                limitations=[
                    "Meaning varies with programme material, task, listener, and production context."
                ],
                prohibited_claims=[prohibited],
            )
            for descriptor_id, correlates, prohibited in (
                (
                    "warmth",
                    ("Low/mid spectral balance may be supporting evidence, not a warmth metric.",),
                    "Do not label a low-mid/high-energy ratio perceptual warmth.",
                ),
                (
                    "harshness",
                    (
                        "Sharpness, roughness, spectral distribution, distortion, level, and context may interact.",
                    ),
                    "Do not equate harshness with sharpness or a fixed 2-5 kHz band.",
                ),
                (
                    "punch",
                    ("Transient, envelope, low-frequency, and dynamic evidence may interact.",),
                    "Do not equate punch with crest factor, peak level, attack time, or bass energy.",
                ),
                (
                    "density",
                    (
                        "Spectral occupancy, event rate, masking, polyphony, and compression may interact.",
                    ),
                    "Do not equate density with RMS, occupancy, masking, polyphony, or compression.",
                ),
                (
                    "width",
                    (
                        "Inter-channel measurements and spatial hearing cues may be supporting evidence.",
                    ),
                    "Do not equate stereo correlation or side/mid energy with perceived width.",
                ),
            )
        ),
    )


__all__ = [
    "BRIGHTNESS_CORRELATE_METHOD_ID",
    "BRIGHTNESS_CORRELATE_METHOD_VERSION",
    "DescriptorClass",
    "DescriptorDefinition",
    "DescriptorImplementationState",
    "descriptor_taxonomy",
]
