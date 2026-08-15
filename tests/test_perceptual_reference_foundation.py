from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception import (
    EmbeddingSimilarityMetric,
    MethodMetadata,
    ReferenceComparisonConfig,
    ReferenceComparisonMode,
    ReferenceEmbeddingEvidence,
    ReferenceEmbeddingProviderIdentity,
    ReferenceEvidenceDimensionId,
    ReferenceEvidenceResult,
    ReferenceProvenance,
    ReferenceRole,
    ReferenceSet,
    ReferenceTrackIdentity,
    ResultStatus,
    reference_intelligence,
)
from noisyne.perception.reference_intelligence import (
    EmbeddingCosineComparator,
    ObjectiveReferenceComparator,
    ReferenceRuntimeResult,
)
from noisyne.runtime.capabilities import CapabilityStatus, registry

ROOT = Path(__file__).resolve().parents[1]


def _audio(
    samples: np.ndarray, sample_rate: int = 48_000, name: str = "synthetic.wav"
) -> AudioData:
    values = np.asarray(samples, dtype=np.float64)
    channels = values.shape[1] if values.ndim == 2 else 1
    return AudioData(
        samples=values,
        metadata=AudioMetadata(
            path=Path(name),
            filename=name,
            extension=".wav",
            format="wav",
            codec=None,
            sample_rate=sample_rate,
            channels=channels,
            duration=len(values) / sample_rate,
            bit_depth=24,
            file_size=values.size * values.dtype.itemsize,
        ),
    )


def _tone(
    frequency_hz: float,
    *,
    amplitude: float = 0.2,
    sample_count: int = 4096,
    sample_rate: int = 48_000,
) -> np.ndarray:
    time = np.arange(sample_count, dtype=np.float64) / sample_rate
    return amplitude * np.sin(2.0 * np.pi * frequency_hz * time)


def _identity(audio: AudioData, reference_id: str = "reference-a") -> ReferenceTrackIdentity:
    return ReferenceTrackIdentity(
        reference_id=reference_id,
        version="1",
        display_name="Analytical reference",
        provenance=ReferenceProvenance.USER_SUPPLIED,
        source="unit_test_fixture",
        duration_seconds=audio.metadata.duration,
        sample_rate_hz=audio.metadata.sample_rate,
        channel_count=audio.metadata.channels,
    )


def _provider(**changes: object) -> ReferenceEmbeddingProviderIdentity:
    values: dict[str, object] = {
        "provider_id": "fake-provider",
        "implementation": "deterministic-test-double",
        "model_id": "fake-model",
        "model_version_or_checkpoint": "checkpoint-1",
        "preprocessing_id": "identity-vector-input",
        "preprocessing_version": "1",
        "embedding_dimension": 3,
        "input_sample_rate_hz": 48_000,
        "clip_window_policy": "caller_supplied_single_test_vector",
        "aggregation_policy": "none",
        "backend": "numpy",
        "device": "cpu",
        "available": True,
    }
    values.update(changes)
    return ReferenceEmbeddingProviderIdentity(**values)


def _compare(source: AudioData, reference: AudioData, **kwargs: object):
    return ObjectiveReferenceComparator().compare(
        source, reference, _identity(reference), source_id="source-a", **kwargs
    )


def _readonly(values: np.ndarray) -> np.ndarray:
    result = np.array(values, copy=True)
    result.setflags(write=False)
    return result


def test_identical_reference_has_zero_deltas_and_immutable_runtime_arrays() -> None:
    audio = _audio(_tone(1000.0))
    result = _compare(audio, audio)

    assert result.evidence.brightness.signed_delta.value == pytest.approx(0.0, abs=1e-12)
    assert result.evidence.programme_energy.signed_delta.value == pytest.approx(0.0, abs=1e-12)
    assert result.evidence.sample_peak.signed_delta.value == pytest.approx(0.0, abs=1e-12)
    assert np.allclose(
        result.channel_erb_delta_db[result.channel_erb_delta_defined], 0.0, atol=1e-12
    )
    for array in (
        result.source_channel_erb_power,
        result.reference_channel_erb_power,
        result.channel_erb_delta_db,
        result.channel_erb_delta_defined,
    ):
        assert array.flags.writeable is False
    with pytest.raises(ValueError):
        result.channel_erb_delta_db[0, 0] = 1.0


def test_half_gain_reference_preserves_centroid_and_erb_shape() -> None:
    source = _audio(_tone(1000.0))
    reference = _audio(source.samples * 0.5)
    raw = _compare(source, reference)
    shape = _compare(
        source,
        reference,
        config=ReferenceComparisonConfig(mode=ReferenceComparisonMode.SHAPE_ONLY),
    )

    expected_db = 6.020599913279624
    assert raw.evidence.programme_energy.signed_delta.value == pytest.approx(expected_db)
    assert raw.evidence.brightness.signed_delta.value == pytest.approx(0.0, abs=1e-10)
    assert np.allclose(
        raw.channel_erb_delta_db[raw.channel_erb_delta_defined], expected_db, atol=1e-9
    )
    assert shape.evidence.programme_energy.state.status is ResultStatus.SKIPPED
    assert shape.evidence.sample_peak.state.status is ResultStatus.SKIPPED
    assert np.allclose(shape.channel_erb_delta_db[shape.channel_erb_delta_defined], 0.0, atol=1e-9)


def test_explicit_gain_is_the_only_level_normalization() -> None:
    source = _audio(_tone(1000.0))
    reference = _audio(source.samples * 0.5)
    config = ReferenceComparisonConfig(
        mode=ReferenceComparisonMode.EXPLICIT_DIGITAL_GAIN,
        reference_gain_db=6.020599913279624,
        gain_method=MethodMetadata(
            "test.caller_declared_gain", "1", "Analytical inverse of half amplitude."
        ),
    )
    result = _compare(source, reference, config=config)

    assert result.evidence.programme_energy.signed_delta.value == pytest.approx(0.0, abs=1e-12)
    assert result.evidence.sample_peak.signed_delta.value == pytest.approx(0.0, abs=1e-12)
    assert result.evidence.comparison.config.gain_method == config.gain_method
    with pytest.raises(ValueError, match="requires gain_method"):
        ReferenceComparisonConfig(mode=ReferenceComparisonMode.EXPLICIT_DIGITAL_GAIN)
    with pytest.raises(ValueError, match="prohibit applied gains"):
        ReferenceComparisonConfig(mode=ReferenceComparisonMode.RAW_LEVEL, source_gain_db=1.0)


def test_high_frequency_source_has_positive_brightness_delta_and_erb_redistribution() -> None:
    source = _audio(_tone(6000.0))
    reference = _audio(_tone(500.0))
    result = _compare(
        source,
        reference,
        config=ReferenceComparisonConfig(mode=ReferenceComparisonMode.SHAPE_ONLY),
    )

    assert result.evidence.brightness.signed_delta.value > 0.0
    defined = result.channel_erb_delta_db[result.channel_erb_delta_defined]
    assert np.any(defined > 0.0)
    assert np.any(defined < 0.0)


def test_silence_reports_undefined_logarithmic_evidence_honestly() -> None:
    silence = _audio(np.zeros(4096, dtype=np.float64))
    result = _compare(silence, silence)

    assert result.evidence.brightness.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence.programme_energy.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence.erb_power_distribution.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence.sample_peak.state.status is ResultStatus.COMPUTED
    assert result.evidence.sample_peak.signed_delta.value == 0.0


def test_channel_mismatch_keeps_scalars_but_refuses_erb_mapping() -> None:
    mono = _tone(1000.0)
    source = _audio(np.column_stack((mono, mono)))
    reference = _audio(mono)
    result = _compare(source, reference)

    assert result.evidence.programme_energy.state.status is ResultStatus.COMPUTED
    assert result.evidence.erb_power_distribution.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert result.channel_erb_delta_db.shape == (0, 0)
    assert "requires identical channels" in result.evidence.comparison.channel_policy


def test_different_durations_use_independent_global_summaries() -> None:
    source = _audio(_tone(1000.0, sample_count=6144))
    reference = _audio(_tone(1000.0, sample_count=3072))
    result = _compare(source, reference)

    assert result.evidence.brightness.state.status is ResultStatus.COMPUTED
    assert (
        result.evidence.comparison.source_duration_seconds != _identity(reference).duration_seconds
    )
    assert result.evidence.comparison.temporal_alignment.endswith("no_temporal_alignment")


def test_reference_identity_and_set_are_explicit_and_json_safe() -> None:
    audio = _audio(_tone(440.0))
    identity = replace(_identity(audio), declared_role=ReferenceRole.TONAL_REFERENCE)
    reference_set = ReferenceSet(
        set_id="set-a",
        version="2",
        references=[identity],
        declared_purpose="caller_declared_tonal_examples",
        provenance=ReferenceProvenance.PROJECT_SUPPLIED,
        source="project_manifest",
    )
    payload = reference_set.to_dict()

    assert ReferenceSet.from_dict(payload) == reference_set
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert "path" not in json.dumps(payload).lower()
    assert payload["references"][0]["version"] == "1"
    with pytest.raises(ValueError, match="unique"):
        replace(reference_set, references=[identity, identity])
    with pytest.raises(ValueError):
        replace(identity, source=" ")
    assert _identity(audio).declared_role is None


def test_reference_identity_must_match_supplied_reference_audio() -> None:
    audio = _audio(_tone(440.0))
    bad = replace(_identity(audio), sample_rate_hz=44_100)
    with pytest.raises(ValueError, match="sample rate"):
        ObjectiveReferenceComparator().compare(audio, audio, bad)


def test_transport_round_trip_excludes_runtime_arrays_and_scores() -> None:
    audio = _audio(_tone(880.0))
    result = _compare(audio, audio)
    payload = result.evidence.to_dict()
    serialized = json.dumps(payload, allow_nan=False).lower()

    assert ReferenceEvidenceResult.from_dict(payload) == result.evidence
    assert "channel_erb_delta_db" not in serialized
    assert "recommendations" not in payload
    assert "match_score" not in serialized
    assert "similarity_percent" not in serialized
    assert payload["erb_power_distribution"]["arrays_serialized"] is False


@pytest.mark.parametrize(
    ("field_name", "wrong_dimension"),
    [
        ("brightness", ReferenceEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB),
        ("programme_energy", ReferenceEvidenceDimensionId.SAMPLE_PEAK_DELTA_ABSOLUTE),
        ("sample_peak", ReferenceEvidenceDimensionId.BRIGHTNESS_CENTROID_DELTA_HZ),
    ],
)
def test_reference_result_rejects_component_dimension_mismatch(
    field_name: str, wrong_dimension: ReferenceEvidenceDimensionId
) -> None:
    audio = _audio(_tone(880.0))
    evidence = _compare(audio, audio).evidence
    forged_component = replace(getattr(evidence, field_name), dimension_id=wrong_dimension)

    with pytest.raises(ValueError, match="wrong reference evidence dimension"):
        replace(evidence, **{field_name: forged_component})


def test_reference_result_rejects_component_comparison_mode_mismatch() -> None:
    audio = _audio(_tone(880.0))
    evidence = _compare(audio, audio).evidence
    forged_brightness = replace(
        evidence.brightness, comparison_mode=ReferenceComparisonMode.SHAPE_ONLY
    )

    with pytest.raises(ValueError, match="comparison_mode must match"):
        replace(evidence, brightness=forged_brightness)


@pytest.mark.parametrize("field_name", ["programme_energy", "sample_peak"])
def test_shape_only_rejects_non_skipped_level_transport(field_name: str) -> None:
    audio = _audio(_tone(880.0))
    raw = _compare(audio, audio).evidence
    shape = _compare(
        audio,
        audio,
        config=ReferenceComparisonConfig(mode=ReferenceComparisonMode.SHAPE_ONLY),
    ).evidence
    forged_component = replace(
        getattr(raw, field_name), comparison_mode=ReferenceComparisonMode.SHAPE_ONLY
    )

    with pytest.raises(ValueError, match=f"shape-only {field_name} must be skipped"):
        replace(shape, **{field_name: forged_component})


def test_forged_reference_result_from_dict_mismatch_is_rejected() -> None:
    audio = _audio(_tone(880.0))
    payload = _compare(audio, audio).evidence.to_dict()
    payload["brightness"]["dimension_id"] = "programme_energy_delta_db"

    with pytest.raises(ValueError, match="wrong reference evidence dimension"):
        ReferenceEvidenceResult.from_dict(payload)


def test_runtime_rejects_source_power_shape_inconsistent_with_summary() -> None:
    audio = _audio(_tone(880.0))
    result = _compare(audio, audio)
    wrong = _readonly(np.zeros((2, result.source_channel_erb_power.shape[1])))

    with pytest.raises(ValueError, match="source ERB power shape"):
        replace(result, source_channel_erb_power=wrong)


def test_runtime_rejects_reference_power_shape_inconsistent_with_summary() -> None:
    audio = _audio(_tone(880.0))
    result = _compare(audio, audio)
    wrong = _readonly(np.zeros((2, result.reference_channel_erb_power.shape[1])))

    with pytest.raises(ValueError, match="reference ERB power shape"):
        replace(result, reference_channel_erb_power=wrong)


@pytest.mark.parametrize("field_name", ["channel_erb_delta_db", "channel_erb_delta_defined"])
def test_runtime_rejects_delta_or_mask_shape_inconsistent_with_summary(
    field_name: str,
) -> None:
    audio = _audio(_tone(880.0))
    result = _compare(audio, audio)
    dtype = np.bool_ if field_name.endswith("defined") else np.float64
    wrong = _readonly(np.zeros((1, 1), dtype=dtype))

    with pytest.raises(ValueError, match="shape"):
        replace(result, **{field_name: wrong})


def test_runtime_rejects_defined_mask_count_inconsistent_with_summary() -> None:
    audio = _audio(_tone(880.0))
    result = _compare(audio, audio)
    wrong = np.array(result.channel_erb_delta_defined, copy=True)
    wrong.flat[0] = not wrong.flat[0]
    wrong.setflags(write=False)

    with pytest.raises(ValueError, match="definition-mask count"):
        replace(result, channel_erb_delta_defined=wrong)


def test_incompatible_channel_empty_delta_runtime_representation_still_validates() -> None:
    mono = _tone(880.0)
    result = _compare(_audio(np.column_stack((mono, mono))), _audio(mono))

    reconstructed = ReferenceRuntimeResult(
        evidence=result.evidence,
        source_channel_erb_power=result.source_channel_erb_power,
        reference_channel_erb_power=result.reference_channel_erb_power,
        channel_erb_delta_db=result.channel_erb_delta_db,
        channel_erb_delta_defined=result.channel_erb_delta_defined,
    )
    assert reconstructed.channel_erb_delta_db.shape == (0, 0)
    assert reconstructed.channel_erb_delta_defined.shape == (0, 0)


def test_objective_comparison_is_deterministic() -> None:
    source = _audio(_tone(1600.0))
    reference = _audio(_tone(900.0))
    first = _compare(source, reference)
    second = _compare(source, reference)

    assert first.evidence.to_dict() == second.evidence.to_dict()
    assert np.array_equal(first.channel_erb_delta_db, second.channel_erb_delta_db)
    assert np.array_equal(first.channel_erb_delta_defined, second.channel_erb_delta_defined)


@pytest.mark.parametrize(
    ("source", "reference", "expected"),
    [
        ([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], 1.0),
        ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], 0.0),
        ([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], -1.0),
        ([1.0, 2.0, 3.0], [7.0, 14.0, 21.0], 1.0),
    ],
)
def test_embedding_cosine_analytical_vectors(source, reference, expected) -> None:
    evidence = EmbeddingCosineComparator().compare(
        np.asarray(source),
        np.asarray(reference),
        _provider(),
        _provider(),
        source_embedding_id="source-vector",
        reference_embedding_id="reference-vector",
    )

    assert evidence.metric is EmbeddingSimilarityMetric.COSINE_SIMILARITY
    assert evidence.similarity.value == pytest.approx(expected)
    assert evidence.similarity.scale == "cosine_similarity_-1_to_1"
    assert evidence.similarity.normalized is False
    assert ReferenceEmbeddingEvidence.from_dict(evidence.to_dict()) == evidence


def test_embedding_zero_vector_is_insufficient_without_epsilon() -> None:
    evidence = EmbeddingCosineComparator().compare(
        np.zeros(3),
        np.ones(3),
        _provider(),
        _provider(),
        source_embedding_id="zero",
        reference_embedding_id="ones",
    )
    assert evidence.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert evidence.similarity is None


def test_embedding_extreme_finite_vectors_use_stable_cosine() -> None:
    maximum = np.finfo(np.float64).max
    evidence = EmbeddingCosineComparator().compare(
        np.array([maximum, maximum, 0.0]),
        np.array([maximum, 0.0, 0.0]),
        _provider(),
        _provider(),
        source_embedding_id="extreme-source",
        reference_embedding_id="extreme-reference",
    )

    assert evidence.similarity.value == pytest.approx(1.0 / np.sqrt(2.0))


def test_embedding_rejects_nonfinite_intermediate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reference_intelligence.np.linalg, "norm", lambda _: float("inf"))

    with pytest.raises(ValueError, match="finite"):
        EmbeddingCosineComparator().compare(
            np.ones(3),
            np.ones(3),
            _provider(),
            _provider(),
            source_embedding_id="source",
            reference_embedding_id="reference",
        )


def test_embedding_clamps_only_finite_roundoff_overshoot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overshoot = np.nextafter(1.0, np.inf)
    monkeypatch.setattr(reference_intelligence.np, "dot", lambda _x, _y: overshoot)
    evidence = EmbeddingCosineComparator().compare(
        np.array([1.0, 0.0, 0.0]),
        np.array([1.0, 0.0, 0.0]),
        _provider(),
        _provider(),
        source_embedding_id="source",
        reference_embedding_id="reference",
    )
    assert evidence.similarity.value == 1.0

    monkeypatch.setattr(reference_intelligence.np, "dot", lambda _x, _y: 1.001)
    with pytest.raises(ValueError, match="outside its mathematical interval"):
        EmbeddingCosineComparator().compare(
            np.array([1.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
            _provider(),
            _provider(),
            source_embedding_id="source",
            reference_embedding_id="reference",
        )


def test_extreme_finite_negative_gain_that_underflows_is_rejected() -> None:
    audio = _audio(_tone(880.0))
    config = ReferenceComparisonConfig(
        mode=ReferenceComparisonMode.EXPLICIT_DIGITAL_GAIN,
        source_gain_db=-1.0e308,
        gain_method=MethodMetadata(
            "test.extreme_gain", "1", "Exercise finite-to-zero gain underflow."
        ),
    )

    with pytest.raises(ValueError, match="gain is not representable"):
        _compare(audio, audio, config=config)


@pytest.mark.parametrize("bad", [np.array([1.0, np.nan, 2.0]), np.array([1.0, np.inf, 2.0])])
def test_embedding_nonfinite_values_are_rejected(bad: np.ndarray) -> None:
    with pytest.raises(ValueError, match="finite"):
        EmbeddingCosineComparator().compare(
            bad,
            np.ones(3),
            _provider(),
            _provider(),
            source_embedding_id="bad",
            reference_embedding_id="ones",
        )


def test_embedding_dimension_and_representation_identity_mismatch_are_rejected() -> None:
    comparator = EmbeddingCosineComparator()
    with pytest.raises(ValueError, match="dimensions"):
        comparator.compare(
            np.ones(3),
            np.ones(2),
            _provider(),
            _provider(),
            source_embedding_id="source",
            reference_embedding_id="reference",
        )
    with pytest.raises(ValueError, match="exact provider"):
        comparator.compare(
            np.ones(3),
            np.ones(3),
            _provider(),
            _provider(model_version_or_checkpoint="checkpoint-2"),
            source_embedding_id="source",
            reference_embedding_id="reference",
        )


def test_capability_truth_is_narrow_and_clap_remains_verified() -> None:
    for capability_name in (
        "perceptual_reference_foundation",
        "reference_objective_comparison",
        "reference_embedding_contract",
    ):
        assert registry.get(capability_name).status is CapabilityStatus.IMPLEMENTED
    assert registry.get("clap_embedding").status is CapabilityStatus.VERIFIED
    assert registry.get("reference_clap_similarity") is None


def test_perception_contract_import_remains_lightweight() -> None:
    code = (
        "import sys; import noisyne.perception; "
        "assert 'numpy' not in sys.modules; assert 'torch' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)
