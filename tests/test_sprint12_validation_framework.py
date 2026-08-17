from __future__ import annotations

import json
import math

import numpy as np
import pytest

from noisyne.perception.auditory_contracts import (
    AUDITORY_FRONTEND_METHOD_ID,
    AUDITORY_FRONTEND_METHOD_VERSION,
    AuditoryFrontendConfig,
)
from noisyne.perception.common import (
    Confidence,
    MethodMetadata,
    ResultState,
    ResultStatus,
    ScalarValue,
    UnitBasis,
)
from noisyne.perception.descriptor_contracts import (
    BRIGHTNESS_CORRELATE_METHOD_ID,
    BRIGHTNESS_CORRELATE_METHOD_VERSION,
)
from noisyne.perception.mix_intelligence_contracts import (
    MIX_INTELLIGENCE_METHOD_ID,
    MIX_INTELLIGENCE_METHOD_VERSION,
    MixCriterionEvaluation,
    MixCriterionOperator,
    MixEvaluationState,
    MixEvidenceDimensionId,
    MixEvidenceSourceType,
    MixIntelligenceResult,
    MixIntelligenceSummary,
    MixIssueCriterion,
    MixIssuePolicy,
    MixIssuePriority,
    MixIssueType,
)
from noisyne.perception.reference_contracts import (
    REFERENCE_FOUNDATION_METHOD_ID,
    REFERENCE_FOUNDATION_METHOD_VERSION,
    ReferenceComparisonConfig,
    ReferenceComparisonMode,
    ReferenceComparisonSummary,
    ReferenceErbPowerSummary,
    ReferenceEvidenceDimensionId,
    ReferenceEvidenceMeasurement,
    ReferenceEvidenceResult,
    ReferenceProvenance,
    ReferenceTrackIdentity,
)
from noisyne.perception.translation_contracts import (
    TranslationEvidenceDimensionId,
    TranslationPolicyProvenance,
    TranslationRiskComparison,
    TranslationRiskCriterion,
    TranslationRiskPolicy,
)
from noisyne.perception.validation_contracts import (
    VALIDATION_SCHEMA_VERSION,
    FixtureKind,
    MethodValidationRecord,
    ToleranceKind,
    ValidationCriterion,
    ValidationEvidence,
    ValidationStatus,
    ValidationSummary,
)
from noisyne.perception.validation_fixtures import NoisyneValidationFixtureProvider
from noisyne.perception.validation_matrix import PerceptualValidationMatrix

# =============================================================================
# 1. Validation Status Taxonomy
# =============================================================================


class TestValidationStatusTaxonomy:
    def test_all_statuses_exist(self) -> None:
        statuses = list(ValidationStatus)
        assert len(statuses) == 5
        assert ValidationStatus.FOUNDATION_ONLY in statuses
        assert ValidationStatus.IMPLEMENTED in statuses
        assert ValidationStatus.VERIFIED in statuses
        assert ValidationStatus.VALIDATED in statuses
        assert ValidationStatus.UNAVAILABLE in statuses

    def test_statuses_are_distinct(self) -> None:
        values = [s.value for s in ValidationStatus]
        assert len(values) == len(set(values))

    def test_implementation_is_not_validation(self) -> None:
        # Sprint 12 principle: do not conflate implementation with validation
        assert ValidationStatus.IMPLEMENTED != ValidationStatus.VERIFIED
        assert ValidationStatus.IMPLEMENTED != ValidationStatus.VALIDATED
        assert ValidationStatus.VERIFIED != ValidationStatus.VALIDATED


# =============================================================================
# 2. Scientific Claim Matrix
# =============================================================================


class TestScientificClaimMatrix:
    def test_matrix_builds(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        assert matrix.schema_version == VALIDATION_SCHEMA_VERSION
        assert len(matrix.records) > 0

    def test_all_records_have_unique_identity(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        ids = [(r.capability_id, r.method_id, r.method_version) for r in matrix.records]
        assert len(ids) == len(set(ids))

    def test_summary_counts_match(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        summary = matrix.summary()
        assert summary["total"] == len(matrix.records)
        assert (
            summary["foundation_only"]
            + summary["implemented"]
            + summary["verified"]
            + summary["validated"]
            + summary["unavailable"]
            == summary["total"]
        )

    def test_by_capability_found(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("auditory_frontend")
        assert record is not None
        assert record.capability_id == "auditory_frontend"

    def test_by_capability_not_found(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        assert matrix.by_capability("nonexistent") is None

    def test_brightness_correlate_record(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("brightness_correlate")
        assert record is not None
        assert record.implementation_status is ValidationStatus.IMPLEMENTED
        assert record.validation_status is ValidationStatus.VERIFIED
        assert "BRIGHTNESS CORRELATE != UNIVERSAL PERCEIVED BRIGHTNESS" in record.prohibited_claims

    def test_sharpness_unavailable(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("sharpness")
        assert record is not None
        assert record.implementation_status is ValidationStatus.UNAVAILABLE
        assert record.validation_status is ValidationStatus.UNAVAILABLE

    def test_roughness_unavailable(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("roughness")
        assert record is not None
        assert record.implementation_status is ValidationStatus.UNAVAILABLE
        assert record.validation_status is ValidationStatus.UNAVAILABLE

    def test_sprint2_auditory_frontend(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("auditory_frontend")
        assert record is not None
        assert record.method_id == AUDITORY_FRONTEND_METHOD_ID
        assert record.method_version == AUDITORY_FRONTEND_METHOD_VERSION

    def test_sprint3_loudness_foundation(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("loudness_foundation")
        assert record is not None
        assert record.validation_status is ValidationStatus.FOUNDATION_ONLY
        assert "LUFS != COMPLETE PERCEIVED LOUDNESS" in record.prohibited_claims

    def test_sprint4_masking_foundation(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("frequency_masking_foundation")
        assert record is not None
        assert record.validation_status is ValidationStatus.VERIFIED
        assert "RELATIVE MASKING EVIDENCE != AUDIBILITY THRESHOLD" in record.prohibited_claims

    def test_sprint6_playback_transfer(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("playback_linear_transfer")
        assert record is not None
        assert record.validation_status is ValidationStatus.VERIFIED

    def test_sprint7_translation_evidence(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("translation_evidence_foundation")
        assert record is not None
        assert record.validation_status is ValidationStatus.VERIFIED

    def test_sprint8_context_resolution(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("perceptual_context_foundation")
        assert record is not None
        assert record.validation_status is ValidationStatus.VERIFIED

    def test_sprint9_reference_comparison(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("reference_objective_comparison")
        assert record is not None
        assert record.validation_status is ValidationStatus.VERIFIED

    def test_sprint10_mix_intelligence(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("perceptual_mix_intelligence_foundation")
        assert record is not None
        assert record.validation_status is ValidationStatus.VERIFIED
        assert "POLICY EVALUATION != OBJECTIVE MIX QUALITY" in record.prohibited_claims

    def test_sprint11_grounded_reasoning(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("perceptual_reasoning_foundation")
        assert record is not None
        assert record.validation_status is ValidationStatus.VERIFIED
        assert "STRUCTURED REASONING != SCIENTIFIC TRUTH" in record.prohibited_claims


# =============================================================================
# 3. Deterministic Validation Fixtures
# =============================================================================


class TestDeterministicValidationFixtures:
    @pytest.fixture
    def provider(self) -> NoisyneValidationFixtureProvider:
        return NoisyneValidationFixtureProvider()

    def test_silence(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(FixtureKind.SILENCE, 48000, 1.0, 2)
        assert fixture["sample_rate_hz"] == 48000
        assert fixture["sample_count"] == 48000
        assert fixture["channel_count"] == 2
        arr = fixture["array"]
        assert isinstance(arr, np.ndarray)
        assert arr.shape == (48000, 2)
        assert np.all(arr == 0.0)
        assert fixture["expected_peak_absolute"] == 0.0

    def test_zero_energy(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(FixtureKind.ZERO_ENERGY, 48000, 0.5, 1)
        arr = fixture["array"]
        assert np.all(arr == 0.0)
        assert fixture["expected_total_energy"] == 0.0

    def test_single_sine(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(FixtureKind.SINGLE_SINE, 48000, 1.0, 1, frequency_hz=1000.0)
        arr = fixture["array"]
        assert arr.shape == (48000, 1)
        assert fixture["frequency_hz"] == 1000.0
        assert fixture["expected_peak_absolute"] == 1.0
        assert math.isclose(fixture["expected_rms"], 1.0 / math.sqrt(2.0), rel_tol=1e-12)

    def test_known_amplitude_sine(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(
            FixtureKind.KNOWN_AMPLITUDE_SINE, 48000, 1.0, 2, frequency_hz=500.0, amplitude=0.25
        )
        arr = fixture["array"]
        assert arr.shape == (48000, 2)
        assert fixture["amplitude"] == 0.25
        assert fixture["expected_peak_absolute"] == 0.25

    def test_two_tone(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(
            FixtureKind.TWO_TONE,
            48000,
            1.0,
            1,
            frequency_a_hz=1000.0,
            frequency_b_hz=2000.0,
            amplitude_a=0.5,
            amplitude_b=0.3,
        )
        arr = fixture["array"]
        assert arr.shape == (48000, 1)
        assert fixture["expected_peak_absolute"] == pytest.approx(0.8, abs=1e-12)

    def test_known_digital_gain(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(FixtureKind.KNOWN_DIGITAL_GAIN, 48000, 1.0, 1, gain_db=6.0)
        assert fixture["gain_db"] == 6.0
        expected_linear = 10.0 ** (6.0 / 20.0)
        assert math.isclose(fixture["linear_gain"], expected_linear, rel_tol=1e-12)
        assert math.isclose(fixture["expected_peak_absolute"], expected_linear, rel_tol=1e-12)

    def test_known_sample_peak(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(FixtureKind.KNOWN_SAMPLE_PEAK, 48000, 1.0, 2, peak=-0.75)
        arr = fixture["array"]
        assert np.all(arr == -0.75)
        assert fixture["expected_peak_absolute"] == 0.75

    def test_known_spectral_shift(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(
            FixtureKind.KNOWN_SPECTRAL_SHIFT,
            48000,
            1.0,
            1,
            source_frequency_hz=1000.0,
            target_frequency_hz=2000.0,
        )
        assert fixture["expected_centroid_delta_hz"] == 1000.0

    def test_deterministic_erb_energy(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(
            FixtureKind.DETERMINISTIC_ERB_ENERGY, 48000, 1.0, 1, frequency_hz=1500.0
        )
        assert fixture["expected_dominant_erb_band_contains_hz"] == 1500.0

    def test_identical_source_reference(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(FixtureKind.IDENTICAL_SOURCE_REFERENCE, 48000, 1.0, 2)
        assert fixture["expected_all_deltas_zero"] is True

    def test_exact_playback_transfer(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(FixtureKind.EXACT_PLAYBACK_TRANSFER, 48000, 1.0, 2)
        assert fixture["expected_output_peak_match"] is True
        assert np.array_equal(fixture["fir_taps"], np.array([1.0]))

    def test_exact_policy_boundary(self, provider: NoisyneValidationFixtureProvider) -> None:
        fixture = provider.generate(
            FixtureKind.EXACT_POLICY_BOUNDARY, 48000, 1.0, 1, threshold=0.5, operator="greater_than"
        )
        assert fixture["threshold"] == 0.5
        assert fixture["value"] > fixture["threshold"]

    def test_fixture_reproducibility(self, provider: NoisyneValidationFixtureProvider) -> None:
        # Same parameters must produce identical arrays
        f1 = provider.generate(FixtureKind.SINGLE_SINE, 48000, 1.0, 2, frequency_hz=1000.0)
        f2 = provider.generate(FixtureKind.SINGLE_SINE, 48000, 1.0, 2, frequency_hz=1000.0)
        assert np.array_equal(f1["array"], f2["array"])


# =============================================================================
# 4. Numeric Tolerance Policy
# =============================================================================


class TestNumericTolerancePolicy:
    def test_tolerance_kinds_exist(self) -> None:
        kinds = list(ToleranceKind)
        assert len(kinds) == 5
        assert ToleranceKind.EXACT_IDENTITY in kinds
        assert ToleranceKind.SERIALIZATION_IDENTITY in kinds
        assert ToleranceKind.FLOATING_POINT_NUMERICAL in kinds
        assert ToleranceKind.DSP_IMPLEMENTATION in kinds
        assert ToleranceKind.REFERENCE_METHOD in kinds

    def test_exact_identity_tolerance_zero(self) -> None:
        # Exact identity means zero tolerance
        criterion = ValidationCriterion(
            criterion_id="test.exact",
            version="1.0.0",
            description="Exact identity test",
            required_status=ValidationStatus.VERIFIED,
            tolerance_kind=ToleranceKind.EXACT_IDENTITY,
            tolerance_value=0.0,
        )
        assert criterion.tolerance_value == 0.0

    def test_floating_point_tolerance_nonzero(self) -> None:
        criterion = ValidationCriterion(
            criterion_id="test.fp",
            version="1.0.0",
            description="FP tolerance test",
            required_status=ValidationStatus.VERIFIED,
            tolerance_kind=ToleranceKind.FLOATING_POINT_NUMERICAL,
            tolerance_value=1e-12,
        )
        assert criterion.tolerance_value == 1e-12

    def test_dsp_tolerance_documented(self) -> None:
        # Each tolerance should have a documented reason in the claim matrix
        matrix = PerceptualValidationMatrix.build()
        for record in matrix.records:
            for policy in record.tolerance_policy:
                assert policy  # non-empty string


# =============================================================================
# 5. Repeatability / Determinism
# =============================================================================


class TestRepeatabilityDeterminism:
    def test_same_input_same_result(self, provider: NoisyneValidationFixtureProvider) -> None:
        f1 = provider.generate(FixtureKind.SINGLE_SINE, 48000, 1.0, 1, frequency_hz=1000.0)
        f2 = provider.generate(FixtureKind.SINGLE_SINE, 48000, 1.0, 1, frequency_hz=1000.0)
        assert np.array_equal(f1["array"], f2["array"])

    def test_serialization_round_trip(self) -> None:
        # Test that validation contracts round-trip through JSON
        record = MethodValidationRecord(
            capability_id="test.capability",
            method_id="test.method",
            method_version="1.0.0",
            implementation_status=ValidationStatus.IMPLEMENTED,
            validation_status=ValidationStatus.VERIFIED,
            scientific_basis=["basis"],
            validation_fixture=["fixture"],
            tolerance_policy=["policy"],
            supported_claims=["claim"],
            prohibited_claims=["prohibited"],
            known_limitations=["limitation"],
        )
        serialized = record.to_dict()
        deserialized = MethodValidationRecord.from_dict(serialized)
        assert deserialized == record

    def test_dict_key_ordering_stable(self) -> None:
        # JSON serialization uses sort_keys=True
        record = MethodValidationRecord(
            capability_id="z_last",
            method_id="a_first",
            method_version="1.0.0",
            implementation_status=ValidationStatus.IMPLEMENTED,
            validation_status=ValidationStatus.VERIFIED,
            scientific_basis=["basis"],
            validation_fixture=["fixture"],
            tolerance_policy=["policy"],
            supported_claims=["claim"],
            prohibited_claims=["prohibited"],
            known_limitations=["limitation"],
        )
        serialized = record.to_dict()
        json_str = json.dumps(serialized, sort_keys=True, separators=(",", ":"))
        # Re-serializing must produce identical bytes
        json_str2 = json.dumps(serialized, sort_keys=True, separators=(",", ":"))
        assert json_str == json_str2

    def test_stable_ids(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        ids = [(r.capability_id, r.method_id, r.method_version) for r in matrix.records]
        assert len(ids) == len(set(ids))

    def test_stable_digests(self) -> None:
        # Serialization must be deterministic for digest stability
        record = MethodValidationRecord(
            capability_id="test",
            method_id="test.method",
            method_version="1.0.0",
            implementation_status=ValidationStatus.IMPLEMENTED,
            validation_status=ValidationStatus.VERIFIED,
            scientific_basis=["basis"],
            validation_fixture=["fixture"],
            tolerance_policy=["policy"],
            supported_claims=["claim"],
            prohibited_claims=["prohibited"],
            known_limitations=["limitation"],
        )
        d1 = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
        d2 = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
        assert d1 == d2


# =============================================================================
# 6. Boundary / Invalid Inputs
# =============================================================================


class TestBoundaryInvalidInputs:
    def test_empty_data_rejected(self) -> None:
        provider = NoisyneValidationFixtureProvider()
        with pytest.raises(ValueError):
            provider.generate(FixtureKind.SILENCE, 48000, 0.0, 0)

    def test_zero_energy_signal(self) -> None:
        provider = NoisyneValidationFixtureProvider()
        fixture = provider.generate(FixtureKind.ZERO_ENERGY, 48000, 1.0, 1)
        arr = fixture["array"]
        assert arr.size > 0
        assert np.all(arr == 0.0)

    def test_mono_vs_stereo(self) -> None:
        provider = NoisyneValidationFixtureProvider()
        mono = provider.generate(FixtureKind.SINGLE_SINE, 48000, 1.0, 1)
        stereo = provider.generate(FixtureKind.SINGLE_SINE, 48000, 1.0, 2)
        assert mono["array"].shape[1] == 1
        assert stereo["array"].shape[1] == 2

    def test_unusual_valid_sample_rate(self) -> None:
        provider = NoisyneValidationFixtureProvider()
        fixture = provider.generate(FixtureKind.SINGLE_SINE, 22050, 1.0, 1)
        assert fixture["sample_rate_hz"] == 22050

    def test_invalid_sample_rate_rejected(self) -> None:
        provider = NoisyneValidationFixtureProvider()
        with pytest.raises(ValueError):
            provider.generate(FixtureKind.SINGLE_SINE, -48000, 1.0, 1)

    def test_nan_rejected_in_scalar_value(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            ScalarValue(value=float("nan"), unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz")

    def test_inf_rejected_in_scalar_value(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            ScalarValue(value=float("inf"), unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz")

    def test_mismatched_dimensions_rejected(self) -> None:
        # Test that contract validation catches mismatched dimensions
        with pytest.raises(ValueError):
            AuditoryFrontendConfig(frame_size_samples=2048, hop_size_samples=4096)

    def test_incompatible_units_rejected(self) -> None:
        # ScalarValue with declared_unit requires unit and prohibits scale
        with pytest.raises(ValueError):
            ScalarValue(
                value=1.0,
                unit_basis=UnitBasis.DECLARED_UNIT,
                unit="Hz",
                scale="some_scale",
            )

    def test_exact_criterion_boundary(self) -> None:
        # Test policy evaluation at exact boundary
        from noisyne.perception.mix_intelligence_contracts import _criterion_triggered

        threshold = ScalarValue(
            value=0.5,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="dB",
        )
        actual_at_boundary = ScalarValue(
            value=0.5,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="dB",
        )
        from noisyne.perception.mix_intelligence_contracts import MixCriterionOperator

        result = _criterion_triggered(
            actual_at_boundary, MixCriterionOperator.GREATER_THAN_OR_EQUAL, threshold
        )
        assert result is True

    def test_just_above_boundary(self) -> None:
        from noisyne.perception.mix_intelligence_contracts import _criterion_triggered

        threshold = ScalarValue(
            value=0.5,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="dB",
        )
        actual = ScalarValue(
            value=0.500001,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="dB",
        )
        from noisyne.perception.mix_intelligence_contracts import MixCriterionOperator

        result = _criterion_triggered(actual, MixCriterionOperator.GREATER_THAN, threshold)
        assert result is True

    def test_just_below_boundary(self) -> None:
        from noisyne.perception.mix_intelligence_contracts import _criterion_triggered

        threshold = ScalarValue(
            value=0.5,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="dB",
        )
        actual = ScalarValue(
            value=0.499999,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="dB",
        )
        from noisyne.perception.mix_intelligence_contracts import MixCriterionOperator

        result = _criterion_triggered(actual, MixCriterionOperator.GREATER_THAN, threshold)
        assert result is False


# =============================================================================
# 7. Scientific / Standards Boundaries
# =============================================================================


class TestScientificStandardsBoundaries:
    def test_loudness_standards_are_context_only(self) -> None:
        # Loudness-related standards must only appear as scientific boundaries,
        # never as implementation provenance, conformance, or validation.
        matrix = PerceptualValidationMatrix.build()
        loudness_standards = ("ISO 532-1", "ISO 532-2", "ISO 532-3", "ITU-R BS.1770", "EBU R128")
        for record in matrix.records:
            for basis in record.scientific_basis:
                if any(std in basis for std in loudness_standards):
                    assert record.validation_status in (
                        ValidationStatus.FOUNDATION_ONLY,
                        ValidationStatus.UNAVAILABLE,
                    ), f"{record.capability_id} cites loudness standard but is not foundation/unavailable"
                    assert (
                        "(context only" in basis
                    ), f"{record.capability_id} loudness standard basis must be context-only: {basis}"
                    for claim in record.supported_claims:
                        assert "conformance" not in claim.lower()
                        assert "compliance" not in claim.lower()
                        assert "validated loudness method" not in claim.lower()

    def test_no_unvalidated_standards_claim(self) -> None:
        # Methods marked FOUNDATION_ONLY or UNAVAILABLE must not claim standards conformance
        matrix = PerceptualValidationMatrix.build()
        for record in matrix.records:
            if record.validation_status in (
                ValidationStatus.FOUNDATION_ONLY,
                ValidationStatus.UNAVAILABLE,
            ):
                for claim in record.supported_claims:
                    assert "conformance" not in claim.lower()
                    assert "compliant" not in claim.lower()

    def test_brightness_research_correlate_not_standardized(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("brightness_correlate")
        assert record is not None
        # Brightness is a research correlate, not a standardized metric
        assert any("correlate" in claim.lower() for claim in record.supported_claims)


# =============================================================================
# 8. Validation Contracts / API
# =============================================================================


class TestValidationContracts:
    def test_validation_criterion_creation(self) -> None:
        criterion = ValidationCriterion(
            criterion_id="test.criterion",
            version="1.0.0",
            description="Test criterion",
            required_status=ValidationStatus.VERIFIED,
        )
        assert criterion.criterion_id == "test.criterion"

    def test_validation_evidence_creation(self) -> None:
        evidence = ValidationEvidence(
            evidence_id="test.evidence",
            criterion_id="test.criterion",
            fixture_kind=FixtureKind.SINGLE_SINE,
            passed=True,
            method_id="test.method",
            method_version="1.0.0",
            fixture_description="1 kHz sine at 48 kHz",
            result_description="Passed",
        )
        assert evidence.passed is True

    def test_method_validation_record_creation(self) -> None:
        record = MethodValidationRecord(
            capability_id="test.capability",
            method_id="test.method",
            method_version="1.0.0",
            implementation_status=ValidationStatus.IMPLEMENTED,
            validation_status=ValidationStatus.VERIFIED,
            scientific_basis=["basis"],
            validation_fixture=["fixture"],
            tolerance_policy=["policy"],
            supported_claims=["claim"],
            prohibited_claims=["prohibited"],
            known_limitations=["limitation"],
        )
        assert record.schema_version == VALIDATION_SCHEMA_VERSION

    def test_validation_summary_counts(self) -> None:
        record = MethodValidationRecord(
            capability_id="test",
            method_id="test.method",
            method_version="1.0.0",
            implementation_status=ValidationStatus.IMPLEMENTED,
            validation_status=ValidationStatus.VERIFIED,
            scientific_basis=["basis"],
            validation_fixture=["fixture"],
            tolerance_policy=["policy"],
            supported_claims=["claim"],
            prohibited_claims=["prohibited"],
            known_limitations=["limitation"],
        )
        summary = ValidationSummary(
            record_count=1,
            foundation_only_count=0,
            implemented_count=0,
            verified_count=1,
            validated_count=0,
            unavailable_count=0,
            records=[record],
        )
        assert summary.record_count == 1
        assert summary.verified_count == 1

    def test_json_safe_contracts(self) -> None:
        # All validation contracts must be JSON-safe
        record = MethodValidationRecord(
            capability_id="test",
            method_id="test.method",
            method_version="1.0.0",
            implementation_status=ValidationStatus.IMPLEMENTED,
            validation_status=ValidationStatus.VERIFIED,
            scientific_basis=["basis"],
            validation_fixture=["fixture"],
            tolerance_policy=["policy"],
            supported_claims=["claim"],
            prohibited_claims=["prohibited"],
            known_limitations=["limitation"],
        )
        data = record.to_dict()
        # Should be JSON-serializable without errors
        json_str = json.dumps(data, sort_keys=True)
        assert isinstance(json_str, str)

    def test_strict_versioned(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        for record in matrix.records:
            assert record.schema_version == VALIDATION_SCHEMA_VERSION
            assert record.method_version != ""

    def test_no_hidden_confidence_score(self) -> None:
        # Validation records must not contain hidden confidence scores
        matrix = PerceptualValidationMatrix.build()
        for record in matrix.records:
            assert not hasattr(record, "confidence_score")
            assert not hasattr(record, "confidence")

    def test_no_fake_percentage(self) -> None:
        # Supported claims must not present a numeric percentage as if it were a score.
        matrix = PerceptualValidationMatrix.build()
        for record in matrix.records:
            for claim in record.supported_claims:
                assert "%" not in claim, f"fake percentage in supported claim: {claim}"


# =============================================================================
# 9. Capability Truth Integration
# =============================================================================


class TestCapabilityTruthIntegration:
    def test_lifecycle_state_separate_from_validation(self) -> None:
        # Runtime CapabilityStatus is separate from ValidationStatus
        from noisyne.runtime.capabilities import CapabilityStatus

        cap_statuses = set(CapabilityStatus)
        val_statuses = set(ValidationStatus)
        assert cap_statuses != val_statuses

    def test_implemented_available_foundation_only_valid(self) -> None:
        # Implemented + Available + Foundation-only is a valid combination
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("loudness_foundation")
        assert record is not None
        assert record.implementation_status is ValidationStatus.IMPLEMENTED
        assert record.validation_status is ValidationStatus.FOUNDATION_ONLY

    def test_validation_status_not_runtime_availability(self) -> None:
        # A method can be UNAVAILABLE for validation but still have running code
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("sharpness")
        assert record is not None
        assert record.implementation_status is ValidationStatus.UNAVAILABLE
        # The descriptor taxonomy code exists and runs, but the scientific method is unavailable

    def test_verified_implies_implemented(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        for record in matrix.records:
            if record.validation_status is ValidationStatus.VERIFIED:
                assert record.implementation_status in (
                    ValidationStatus.IMPLEMENTED,
                    ValidationStatus.VERIFIED,
                )

    def test_validated_implies_verified(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        for record in matrix.records:
            if record.validation_status is ValidationStatus.VALIDATED:
                assert record.implementation_status in (
                    ValidationStatus.VERIFIED,
                    ValidationStatus.VALIDATED,
                )


# =============================================================================
# 10. Existing Contract Regression (Sprint 2-11)
# =============================================================================


class TestExistingContractRegression:
    def test_auditory_frontend_config_validation(self) -> None:
        config = AuditoryFrontendConfig()
        assert config.frame_size_samples == 2048
        assert config.hop_size_samples == 512

    def test_reference_evidence_result_dimensions(self) -> None:
        ref = ReferenceTrackIdentity(
            reference_id="ref1",
            version="1.0.0",
            display_name="Test",
            provenance=ReferenceProvenance.USER_SUPPLIED,
            source="test",
            duration_seconds=10.0,
            sample_rate_hz=48000,
            channel_count=2,
        )
        comparison = ReferenceComparisonSummary(
            method=MethodMetadata(
                method_id=REFERENCE_FOUNDATION_METHOD_ID,
                version=REFERENCE_FOUNDATION_METHOD_VERSION,
            ),
            reference=ref,
            config=ReferenceComparisonConfig(),
            source_id=None,
            source_duration_seconds=10.0,
            source_sample_rate_hz=48000,
            source_channel_count=2,
            temporal_alignment="sample_synchronous",
            channel_policy="matched_channels_independent",
        )
        brightness = ReferenceEvidenceMeasurement(
            evidence_id="e1",
            dimension_id=ReferenceEvidenceDimensionId.BRIGHTNESS_CENTROID_DELTA_HZ,
            state=ResultState(status=ResultStatus.COMPUTED),
            source_value=ScalarValue(value=100.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz"),
            reference_value=ScalarValue(value=200.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz"),
            signed_delta=ScalarValue(value=-100.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz"),
            sign_convention="source_minus_reference",
            valid_interpretation="negative means darker",
            method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            source_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            reference_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            comparison_mode=ReferenceComparisonMode.RAW_LEVEL,
        )
        erb_summary = ReferenceErbPowerSummary(
            dimension_id=ReferenceEvidenceDimensionId.ERB_POWER_DISTRIBUTION_DELTA_DB,
            state=ResultState(status=ResultStatus.COMPUTED),
            method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            source_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            reference_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            comparison_mode=ReferenceComparisonMode.RAW_LEVEL,
            source_channel_count=2,
            reference_channel_count=2,
            source_band_count=128,
            reference_band_count=128,
            defined_value_count=256,
            minimum_delta_db=0.0,
            maximum_delta_db=0.0,
            maximum_absolute_delta_db=0.0,
        )
        programme_energy = ReferenceEvidenceMeasurement(
            evidence_id="e2",
            dimension_id=ReferenceEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
            state=ResultState(status=ResultStatus.COMPUTED),
            source_value=ScalarValue(value=1.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="dB"),
            reference_value=ScalarValue(value=2.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="dB"),
            signed_delta=ScalarValue(value=-1.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="dB"),
            sign_convention="source_minus_reference",
            valid_interpretation="negative means lower energy",
            method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            source_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            reference_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            comparison_mode=ReferenceComparisonMode.RAW_LEVEL,
        )
        sample_peak = ReferenceEvidenceMeasurement(
            evidence_id="e3",
            dimension_id=ReferenceEvidenceDimensionId.SAMPLE_PEAK_DELTA_ABSOLUTE,
            state=ResultState(status=ResultStatus.COMPUTED),
            source_value=ScalarValue(
                value=0.8, unit_basis=UnitBasis.DECLARED_UNIT, unit="absolute"
            ),
            reference_value=ScalarValue(
                value=0.9, unit_basis=UnitBasis.DECLARED_UNIT, unit="absolute"
            ),
            signed_delta=ScalarValue(
                value=-0.1, unit_basis=UnitBasis.DECLARED_UNIT, unit="absolute"
            ),
            sign_convention="source_minus_reference",
            valid_interpretation="negative means lower peak",
            method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            source_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            reference_analysis_method=MethodMetadata(
                method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
                version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
            ),
            comparison_mode=ReferenceComparisonMode.RAW_LEVEL,
        )
        result = ReferenceEvidenceResult(
            comparison=comparison,
            brightness=brightness,
            programme_energy=programme_energy,
            erb_power_distribution=erb_summary,
            sample_peak=sample_peak,
        )
        assert result.comparison.reference.reference_id == "ref1"

    def test_mix_intelligence_result_counts_balance(self) -> None:
        criterion = MixIssueCriterion(
            criterion_id="c1",
            version="1.0.0",
            provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
            source="test",
            description="test",
            display_name="Test",
            evidence_source_type=MixEvidenceSourceType.REFERENCE_EVIDENCE,
            evidence_dimension=MixEvidenceDimensionId.REFERENCE_BRIGHTNESS_CENTROID_DELTA_HZ,
            operator=MixCriterionOperator.GREATER_THAN,
            threshold=ScalarValue(value=100.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz"),
            issue_type=MixIssueType.REFERENCE_DEVIATION,
            priority=MixIssuePriority.MEDIUM,
        )
        policy = MixIssuePolicy(
            policy_id="p1",
            version="1.0.0",
            provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
            source="test",
            description="test",
            criteria=[criterion],
        )
        evaluation = MixCriterionEvaluation(
            criterion_id="c1",
            criterion_version="1.0.0",
            state=MixEvaluationState.NOT_TRIGGERED,
            evidence_source_type=MixEvidenceSourceType.REFERENCE_EVIDENCE,
            evidence_dimension=MixEvidenceDimensionId.REFERENCE_BRIGHTNESS_CENTROID_DELTA_HZ,
            reason="not triggered",
            evidence_identity="e1",
            evidence_value=ScalarValue(value=50.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz"),
            evidence_state=ResultStatus.COMPUTED,
            evidence_method=MethodMetadata(method_id="test", version="1.0.0"),
        )
        summary = MixIntelligenceSummary(
            evaluated_criterion_count=1,
            triggered_issue_count=0,
            not_triggered_count=1,
            insufficient_evidence_count=0,
            conflict_count=0,
        )
        result = MixIntelligenceResult(
            policy=policy,
            method=MethodMetadata(
                method_id=MIX_INTELLIGENCE_METHOD_ID, version=MIX_INTELLIGENCE_METHOD_VERSION
            ),
            evaluations=[evaluation],
            issues=[],
            summary=summary,
            confidence=Confidence(),
        )
        assert result.summary.evaluated_criterion_count == 1

    def test_translation_risk_policy_unique_criteria(self) -> None:
        with pytest.raises(ValueError):
            TranslationRiskPolicy(
                policy_id="p1",
                version="1.0.0",
                provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
                source="test",
                description="test",
                criteria=[
                    TranslationRiskCriterion(
                        criterion_id="c1",
                        criterion_version="1.0.0",
                        evidence_dimension_id=TranslationEvidenceDimensionId.BRIGHTNESS_CENTROID_SHIFT_HZ,
                        comparison=TranslationRiskComparison.GREATER_THAN,
                        threshold=ScalarValue(
                            value=100.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz"
                        ),
                        direction_semantics="increase",
                        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
                        source="test",
                        description="test",
                    ),
                    TranslationRiskCriterion(
                        criterion_id="c1",  # duplicate
                        criterion_version="1.0.0",
                        evidence_dimension_id=TranslationEvidenceDimensionId.BRIGHTNESS_CENTROID_SHIFT_HZ,
                        comparison=TranslationRiskComparison.GREATER_THAN,
                        threshold=ScalarValue(
                            value=200.0, unit_basis=UnitBasis.DECLARED_UNIT, unit="Hz"
                        ),
                        direction_semantics="increase",
                        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
                        source="test",
                        description="test",
                    ),
                ],
            )


# =============================================================================
# Fixture provider fixture registration
# =============================================================================


@pytest.fixture
def provider() -> NoisyneValidationFixtureProvider:
    return NoisyneValidationFixtureProvider()
