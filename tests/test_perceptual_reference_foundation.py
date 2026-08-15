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
    ReferenceEvidenceResult,
    ReferenceProvenance,
    ReferenceRole,
    ReferenceSet,
    ReferenceTrackIdentity,
    ResultStatus,
)
from noisyne.perception.reference_intelligence import (
    EmbeddingCosineComparator,
    ObjectiveReferenceComparator,
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
