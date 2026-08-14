from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from noisyne.perception import (
    PERCEPTUAL_SCHEMA_VERSION,
    AnalysisMetadata,
    AuditoryBand,
    ComponentStatus,
    Confidence,
    ConfidenceBasis,
    EvidenceSource,
    FrequencyMaskingResult,
    FrequencyRange,
    ListeningLevel,
    MaskingEvent,
    Measurement,
    MethodMetadata,
    MonoCompatibility,
    ObservationCategory,
    PerceivedLoudnessResult,
    PerceptualAnalysisResult,
    PerceptualContext,
    PerceptualDescriptorResult,
    PerceptualEvidence,
    PerceptualObservation,
    PlaybackProfile,
    PlaybackProfileReference,
    ResultState,
    ResultStatus,
    ScalarValue,
    TimeRange,
    TranslationResult,
    TranslationRiskDimension,
    UnitBasis,
)

ROOT = Path(__file__).resolve().parents[1]
COMPUTED = ResultState(ResultStatus.COMPUTED)


def _normalized(value: float, scale: str = "normalized_risk") -> ScalarValue:
    return ScalarValue(
        value=value,
        unit_basis=UnitBasis.NAMED_SCALE,
        scale=scale,
        normalized=True,
    )


def _measurement(identifier: str = "lufs") -> Measurement:
    return Measurement(
        measurement_id=identifier,
        name="programme loudness",
        value=ScalarValue(
            value=-14.0,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="LUFS",
        ),
        source="v1_dsp_analysis",
        method=MethodMetadata(method_id="itu_loudness_meter", version="v1"),
        time_range=TimeRange(0.0, 30.0),
    )


def _evidence(identifier: str = "evidence-lufs") -> PerceptualEvidence:
    return PerceptualEvidence(
        evidence_id=identifier,
        source=EvidenceSource.MEASUREMENT,
        origin="noisyne.audio.analysis",
        measurement=_measurement(identifier),
        note="Objective source measurement; not a perceptual estimate.",
    )


def _confidence(score: float = 0.8) -> Confidence:
    return Confidence(
        score=score,
        basis=ConfidenceBasis.COMBINED,
        reason="Supported by source measurements and method checks.",
        limitations=["Not a probability."],
    )


def _band(lower: float, upper: float, index: int) -> AuditoryBand:
    return AuditoryBand(
        frequency_range=FrequencyRange(lower, upper),
        center_hz=(lower + upper) / 2,
        band_index=index,
        scale_id="research_pending",
    )


def _masking_event(identifier: str, attribution: str | None = None) -> MaskingEvent:
    return MaskingEvent(
        event_id=identifier,
        masker_region=_band(100.0, 200.0, 1),
        masked_region=_band(150.0, 300.0, 2),
        strength=_normalized(0.6, "method_defined_masking_strength"),
        evidence=[_evidence(f"{identifier}-evidence")],
        confidence=_confidence(),
        time_range=TimeRange(2.0, 4.0),
        source_attribution=attribution,
        assumptions=["Attribution is omitted unless independently supported."],
    )


def _descriptor(identifier: str, value: float) -> PerceptualDescriptorResult:
    return PerceptualDescriptorResult(
        descriptor_id=identifier,
        display_name=identifier.replace("_", " ").title(),
        state=COMPUTED,
        estimate=_normalized(value, f"{identifier}_research_scale"),
        evidence=[_evidence(f"{identifier}-evidence")],
        confidence=_confidence(),
    )


def _translation(target: str, risk: float) -> TranslationResult:
    dimension = TranslationRiskDimension(
        dimension_id="stereo_collapse",
        display_name="Stereo collapse",
        state=COMPUTED,
        risk=_normalized(risk),
        evidence=[_evidence(f"{target}-evidence")],
        confidence=_confidence(),
    )
    return TranslationResult(
        target_profile=PlaybackProfileReference(target, "1.0.0"),
        state=COMPUTED,
        dimensions=[dimension],
        evidence=dimension.evidence,
        confidence=dimension.confidence,
    )


def test_valid_contract_construction_distinguishes_measurement_and_estimate() -> None:
    measurement = _measurement()
    estimate = _normalized(0.7, "future_perceived_loudness_scale")
    result = PerceivedLoudnessResult(
        state=COMPUTED,
        estimate=estimate,
        programme_loudness_measurement=measurement,
        evidence=[_evidence()],
        confidence=_confidence(),
    )

    assert result.estimate is estimate
    assert result.programme_loudness_measurement is measurement
    assert result.programme_loudness_measurement.value.unit == "LUFS"
    assert PerceivedLoudnessResult.from_dict(result.to_dict()) == result


def test_nested_serialization_and_round_trip_are_json_compatible() -> None:
    result = PerceptualAnalysisResult(
        state=COMPUTED,
        analysis_id="analysis-1",
        metadata=AnalysisMetadata(
            source_id="fixture.wav",
            duration_seconds=30.0,
            sample_rate_hz=48_000,
            channel_count=2,
        ),
        context=PerceptualContext(
            genre="electronic",
            delivery_target="streaming",
            listening_level=ListeningLevel.MODERATE,
            mono_compatibility=MonoCompatibility.REQUIRED,
        ),
        descriptors=[_descriptor("brightness", 0.4)],
        translations=[_translation("phone_like", 0.6)],
        evidence=[_evidence()],
        component_statuses=[ComponentStatus("descriptors", COMPUTED)],
    )

    encoded = result.to_dict()
    payload = json.loads(json.dumps(encoded))
    reconstructed = PerceptualAnalysisResult.from_dict(payload)

    assert reconstructed == result
    assert payload["state"]["status"] == "computed"
    assert payload["context"]["listening_level"] == "moderate"
    json.dumps(payload, allow_nan=False)


def test_top_level_optional_components_and_unknown_context() -> None:
    result = PerceptualAnalysisResult(
        state=ResultState(
            ResultStatus.INSUFFICIENT_EVIDENCE,
            "No perceptual components have run.",
        ),
        context=PerceptualContext(),
    )

    assert result.perceived_loudness is None
    assert result.frequency_masking is None
    assert result.context.genre is None
    assert result.context.listening_level is None
    assert PerceptualAnalysisResult.from_dict(result.to_dict()) == result


@pytest.mark.parametrize("status", [ResultStatus.UNAVAILABLE, ResultStatus.SKIPPED])
def test_unavailable_and_skipped_result_states(status: ResultStatus) -> None:
    state = ResultState(status, "Component was not runnable in this request.")
    result = PerceptualAnalysisResult(state=state)

    assert result.state.status is status
    assert result.to_dict()["state"]["reason"]


def test_insufficient_evidence_is_distinct_from_unavailable() -> None:
    state = ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "Evidence threshold not met.")
    descriptor = PerceptualDescriptorResult(descriptor_id="warmth", state=state)

    assert descriptor.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert descriptor.estimate is None


def test_insufficient_evidence_masking_rejects_event() -> None:
    state = ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "Masking evidence is incomplete.")

    with pytest.raises(ValueError, match="must not contain events"):
        FrequencyMaskingResult(state=state, events=[_masking_event("unsupported-mask")])


def test_insufficient_evidence_translation_rejects_dimension_and_aggregate_risk() -> None:
    state = ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "Translation evidence is incomplete.")
    dimension = TranslationRiskDimension(dimension_id="stereo_collapse", state=state)
    target = PlaybackProfileReference("mono", "1.0.0")

    with pytest.raises(ValueError, match="must not carry risks"):
        TranslationResult(target_profile=target, state=state, dimensions=[dimension])
    with pytest.raises(ValueError, match="must not carry risks"):
        TranslationResult(target_profile=target, state=state, aggregate_risk=_normalized(0.4))


def test_insufficient_evidence_top_level_rejects_computed_component() -> None:
    state = ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "Analysis evidence is incomplete.")

    with pytest.raises(ValueError, match="must not contain computed components"):
        PerceptualAnalysisResult(state=state, descriptors=[_descriptor("brightness", 0.4)])


def test_insufficient_evidence_retains_supporting_information() -> None:
    state = ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "Evidence threshold not met.")
    result = PerceivedLoudnessResult(
        state=state,
        evidence=[_evidence()],
        confidence=Confidence(
            basis=ConfidenceBasis.MEASUREMENT_QUALITY,
            reason="Available measurements do not support a final estimate.",
            limitations=["Perceptual method has not run."],
        ),
        limitations=["No final perceived-loudness estimate is available."],
    )

    assert result.estimate is None
    assert result.evidence
    assert result.confidence.reason
    assert result.limitations


def test_insufficient_evidence_loudness_rejects_computed_observation() -> None:
    state = ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "Evidence threshold not met.")
    observation = PerceptualObservation(
        observation_id="loudness-observation",
        category=ObservationCategory.LOUDNESS,
        kind="perceived_loudness",
        state=COMPUTED,
        value=_normalized(0.4, "future_perceived_loudness_scale"),
    )

    with pytest.raises(ValueError, match="has computed observation"):
        PerceivedLoudnessResult(state=state, observations=[observation])


def test_computed_partial_top_level_uses_component_statuses() -> None:
    insufficient = ResultState(
        ResultStatus.INSUFFICIENT_EVIDENCE,
        "Translation evidence threshold not met.",
    )
    result = PerceptualAnalysisResult(
        state=COMPUTED,
        descriptors=[_descriptor("brightness", 0.4)],
        component_statuses=[
            ComponentStatus("descriptors", COMPUTED),
            ComponentStatus("translation", insufficient),
        ],
    )

    assert result.state.status is ResultStatus.COMPUTED
    assert result.component_statuses[1].state.status is ResultStatus.INSUFFICIENT_EVIDENCE


@pytest.mark.parametrize("score", [0.0, 1.0, 0.25, None])
def test_confidence_boundaries(score: float | None) -> None:
    assert Confidence(score=score).score == score


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_invalid_confidence(score: float) -> None:
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        Confidence(score=score)


def test_valid_time_range() -> None:
    assert TimeRange(0.0, 0.0).end_seconds == 0.0
    assert TimeRange(1.25, 2.5).start_seconds == 1.25


@pytest.mark.parametrize("start,end", [(-1.0, 1.0), (0.0, -1.0), (2.0, 1.0)])
def test_invalid_time_range(start: float, end: float) -> None:
    with pytest.raises(ValueError):
        TimeRange(start, end)


def test_valid_frequency_range_and_auditory_band() -> None:
    band = AuditoryBand(FrequencyRange(0.0, 96_000.0), center_hz=48_000.0)

    assert band.frequency_range.upper_hz == 96_000.0


@pytest.mark.parametrize("lower,upper", [(-1.0, 100.0), (0.0, -1.0), (200.0, 100.0)])
def test_invalid_frequency_range(lower: float, upper: float) -> None:
    with pytest.raises(ValueError):
        FrequencyRange(lower, upper)


def test_multiple_evidence_items_serialize() -> None:
    observation = PerceptualObservation(
        observation_id="brightness-1",
        category=ObservationCategory.DESCRIPTOR,
        kind="brightness",
        state=COMPUTED,
        value=_normalized(0.5, "brightness_research_scale"),
        evidence=[_evidence("first"), _evidence("second")],
        confidence=_confidence(),
    )

    assert len(observation.to_dict()["evidence"]) == 2


def test_zero_masking_events_is_valid() -> None:
    result = FrequencyMaskingResult(state=COMPUTED)

    assert result.events == []
    assert FrequencyMaskingResult.from_dict(result.to_dict()) == result


def test_multiple_masking_events_and_optional_attribution() -> None:
    result = FrequencyMaskingResult(
        state=COMPUTED,
        events=[_masking_event("mask-1"), _masking_event("mask-2", "supported source")],
    )

    assert result.events[0].source_attribution is None
    assert result.events[1].source_attribution == "supported source"
    assert FrequencyMaskingResult.from_dict(result.to_dict()) == result


def test_multiple_descriptor_results_are_independent() -> None:
    result = PerceptualAnalysisResult(
        state=COMPUTED,
        descriptors=[_descriptor("brightness", 0.4), _descriptor("punch", 0.8)],
    )

    assert [item.descriptor_id for item in result.descriptors] == ["brightness", "punch"]


def test_multiple_translation_targets_and_dimensions() -> None:
    result = PerceptualAnalysisResult(
        state=COMPUTED,
        translations=[_translation("phone_like", 0.7), _translation("mono", 0.3)],
    )

    assert [item.target_profile.profile_id for item in result.translations] == [
        "phone_like",
        "mono",
    ]
    assert all(len(item.dimensions) == 1 for item in result.translations)


def test_playback_profile_is_description_only_and_versioned() -> None:
    profile = PlaybackProfile(
        profile_id="small_speaker_like",
        display_name="Small-speaker-like research context",
        version="0.1.0",
        description="Descriptive placeholder; no hardware emulation claim.",
        assumptions=["Transformation design remains Sprint 6 work."],
    )

    assert profile.reference == PlaybackProfileReference("small_speaker_like", "0.1.0")
    assert profile.to_dict()["version"] == "0.1.0"
    assert PlaybackProfile.from_dict(profile.to_dict()) == profile


def test_top_level_schema_version_is_locked() -> None:
    result = PerceptualAnalysisResult(
        state=ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "No components have run.")
    )

    assert PERCEPTUAL_SCHEMA_VERSION == "1.0.0"
    assert result.schema_version == "1.0.0"
    assert result.to_dict()["schema_version"] == "1.0.0"


def test_result_state_requires_reason_when_not_computed() -> None:
    with pytest.raises(ValueError, match="requires a reason"):
        ResultState(ResultStatus.UNAVAILABLE)


def test_invalid_required_identifier_and_contradictory_computed_state() -> None:
    with pytest.raises(ValueError, match="measurement_id"):
        Measurement(
            measurement_id="",
            name="level",
            value=ScalarValue(1.0, UnitBasis.UNDEFINED),
            source="test",
        )

    with pytest.raises(ValueError, match="at least one result component"):
        PerceptualAnalysisResult(state=COMPUTED)


def test_normalized_value_validation_and_explicit_undefined_unit() -> None:
    undefined = ScalarValue(value="research_pending", unit_basis=UnitBasis.UNDEFINED)
    assert undefined.unit is None and undefined.scale is None

    with pytest.raises(ValueError, match="within"):
        _normalized(1.1)


def test_unknown_serialized_fields_are_rejected() -> None:
    payload = PerceptualAnalysisResult(
        state=ResultState(ResultStatus.INSUFFICIENT_EVIDENCE, "No components have run.")
    ).to_dict()
    payload["magic"] = "not part of schema"

    with pytest.raises(ValueError, match="Unknown"):
        PerceptualAnalysisResult.from_dict(payload)


def test_deserialization_rejects_wrong_primitive_type() -> None:
    with pytest.raises(TypeError, match="float"):
        TimeRange.from_dict({"start_seconds": "0.0", "end_seconds": 1.0})
    with pytest.raises(TypeError, match="bool"):
        ScalarValue.from_dict(
            {
                "value": 1.0,
                "unit_basis": "undefined",
                "unit": None,
                "scale": None,
                "normalized": 1,
            }
        )


def test_float_transport_accepts_json_integer_and_preserves_float() -> None:
    integer_payload = TimeRange.from_dict({"start_seconds": 1, "end_seconds": 2})
    float_payload = TimeRange.from_dict({"start_seconds": 1.25, "end_seconds": 2.5})

    assert integer_payload == TimeRange(1.0, 2.0)
    assert type(integer_payload.start_seconds) is float
    assert float_payload == TimeRange(1.25, 2.5)
    assert type(float_payload.start_seconds) is float


@pytest.mark.parametrize("value", [True, "1.0"])
def test_float_transport_rejects_bool_and_numeric_string(value: object) -> None:
    with pytest.raises(TypeError, match="float"):
        TimeRange.from_dict({"start_seconds": value, "end_seconds": 2.0})


@pytest.mark.parametrize("value", [1.0, True])
def test_int_transport_rejects_float_and_bool(value: object) -> None:
    with pytest.raises(TypeError, match="int"):
        AnalysisMetadata.from_dict(
            {
                "source_id": None,
                "duration_seconds": None,
                "sample_rate_hz": value,
                "channel_count": 2,
                "auditory_frontend": None,
            }
        )


def test_scalar_integer_round_trip_preserves_integer_variant() -> None:
    value = ScalarValue(value=1, unit_basis=UnitBasis.UNDEFINED)
    reconstructed = ScalarValue.from_dict(value.to_dict())

    assert type(reconstructed.value) is int


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_time_range_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        TimeRange(value, 1.0)
    with pytest.raises(ValueError, match="finite"):
        TimeRange(0.0, value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_frequency_range_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        FrequencyRange(value, 1_000.0)
    with pytest.raises(ValueError, match="finite"):
        FrequencyRange(20.0, value)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_confidence_and_scalar_reject_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        Confidence(score=value)
    with pytest.raises(ValueError, match="finite"):
        ScalarValue(value=value, unit_basis=UnitBasis.UNDEFINED)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_auditory_metadata_and_context_reject_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        AuditoryBand(FrequencyRange(20.0, 20_000.0), center_hz=value)
    with pytest.raises(ValueError, match="finite"):
        AnalysisMetadata(duration_seconds=value)
    with pytest.raises(ValueError):
        AnalysisMetadata(sample_rate_hz=value)
    with pytest.raises(ValueError):
        AnalysisMetadata(channel_count=value)
    with pytest.raises(ValueError, match="finite"):
        PerceptualContext(listening_level_db_spl=value)


def test_valid_nested_payload_uses_strict_json_numbers() -> None:
    result = PerceptualAnalysisResult(
        state=COMPUTED,
        metadata=AnalysisMetadata(
            source_id="fixture.wav",
            duration_seconds=10.0,
            sample_rate_hz=48_000,
            channel_count=2,
        ),
        context=PerceptualContext(listening_level_db_spl=72.5),
        descriptors=[_descriptor("brightness", 0.4)],
    )

    payload = result.to_dict()
    json.dumps(payload, allow_nan=False)
    assert PerceptualAnalysisResult.from_dict(payload) == result


def test_deserialization_rejects_invalid_scalar_union_payload() -> None:
    payload = {
        "value": {"unexpected": "object"},
        "unit_basis": "undefined",
        "unit": None,
        "scale": None,
        "normalized": False,
    }

    with pytest.raises(TypeError, match="does not match union"):
        ScalarValue.from_dict(payload)


def test_deserialization_rejects_non_string_list_member() -> None:
    with pytest.raises(TypeError, match="str"):
        Confidence.from_dict(
            {
                "score": None,
                "basis": "unknown",
                "reason": None,
                "limitations": ["valid", 3],
            }
        )


def test_deserialization_rejects_non_string_mapping_value() -> None:
    payload = PlaybackProfile(
        profile_id="reference",
        display_name="Reference",
        version="1.0.0",
        description="Reference playback context.",
    ).to_dict()
    payload["metadata"] = {"owner": 7}

    with pytest.raises(TypeError, match="str"):
        PlaybackProfile.from_dict(payload)


def test_deserialization_rejects_invalid_enum_value() -> None:
    with pytest.raises(ValueError):
        ResultState.from_dict({"status": "not_a_status", "reason": None})


def test_deserialization_rejects_union_with_no_valid_candidate() -> None:
    with pytest.raises(TypeError, match="does not match union"):
        MethodMetadata.from_dict(
            {"method_id": "method", "version": "1", "description": ["invalid"]}
        )


def test_perception_import_is_lightweight() -> None:
    script = """
import sys
import noisyne.perception
heavy = {'torch', 'transformers', 'sentence_transformers', 'PySide6'}
print(','.join(sorted(heavy.intersection(sys.modules))))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_perception_package_has_no_forbidden_architecture_imports() -> None:
    forbidden = (
        "PySide6",
        "FastAPI",
        "openai",
        "chromadb",
        "torch",
        "transformers",
        "onnxruntime",
        "noisyne.integration",
        "noisyne.providers",
    )
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "noisyne" / "perception").glob("*.py"))
    )

    assert all(item not in source for item in forbidden)
