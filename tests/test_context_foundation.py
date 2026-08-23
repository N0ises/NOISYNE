from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from phasenox.perception import (
    PERCEPTUAL_SCHEMA_VERSION,
    ConfidenceBasis,
    ContextClaim,
    ContextDimension,
    ContextPolicyBinding,
    ContextPolicySelectionResult,
    ContextPolicySelectionStatus,
    ContextProvenance,
    ContextRequirement,
    ContextRequirementOperator,
    ContextResolutionResult,
    ContextResolutionStatus,
    ListeningConditionMeasurement,
    ListeningLevel,
    MonoCompatibility,
    PerceptualContext,
    PlaybackProfileReference,
    ResolvedContextDimension,
    ScalarValue,
    TranslationEvidenceDimensionId,
    TranslationPolicyProvenance,
    TranslationRiskComparison,
    TranslationRiskCriterion,
    TranslationRiskPolicy,
    UnitBasis,
)
from phasenox.perception.context_resolution import ContextPolicySelector, PerceptualContextResolver
from phasenox.runtime.capabilities import CapabilityStatus, registry


def _claim(
    claim_id: str,
    dimension: ContextDimension,
    value: object,
    *,
    provenance: ContextProvenance = ContextProvenance.USER_DECLARED,
    source: str = "Test caller",
    source_version: str | None = None,
    measurement: ListeningConditionMeasurement | None = None,
) -> ContextClaim:
    return ContextClaim(
        claim_id=claim_id,
        context_dimension=dimension,
        value=value,
        provenance=provenance,
        source=source,
        source_version=source_version,
        measurement=measurement,
    )


def _policy(policy_id: str = "fixture.policy", version: str = "1.0.0") -> TranslationRiskPolicy:
    criterion = TranslationRiskCriterion(
        criterion_id="fixture.criterion",
        criterion_version="1.0.0",
        evidence_dimension_id=TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
        comparison=TranslationRiskComparison.ABSOLUTE_GREATER_THAN,
        threshold=ScalarValue(3.0, UnitBasis.DECLARED_UNIT, unit="dB"),
        direction_semantics="Exact fixture comparison only",
        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
        source="Fixture project policy",
        description="Explicit fixture threshold; not generated from context",
    )
    return TranslationRiskPolicy(
        policy_id=policy_id,
        version=version,
        provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
        source="Fixture project policy",
        description="Explicit fixture policy",
        criteria=[criterion],
    )


def _binding(
    value: str = "fixture.delivery",
    *,
    binding_id: str = "fixture.binding",
    policy_id: str = "fixture.policy",
    policy_version: str = "1.0.0",
) -> ContextPolicyBinding:
    return ContextPolicyBinding(
        binding_id=binding_id,
        version="1.0.0",
        requirements=[
            ContextRequirement(
                context_dimension=ContextDimension.DELIVERY_TARGET,
                operator=ContextRequirementOperator.EQUALS,
                expected_value=value,
            )
        ],
        policy_id=policy_id,
        policy_version=policy_version,
        provenance=ContextProvenance.PROJECT_DECLARED,
        source="Fixture project binding",
    )


def test_one_user_declared_genre_resolves_exactly() -> None:
    result = PerceptualContextResolver().resolve(
        claims=[_claim("genre.user", ContextDimension.GENRE, "Techno")]
    )
    dimension = result.dimension(ContextDimension.GENRE)
    assert result.status is ContextResolutionStatus.RESOLVED
    assert dimension.values == ["Techno"]
    assert dimension.claims[0].provenance is ContextProvenance.USER_DECLARED
    assert dimension.claims[0].confidence.score is None
    assert dimension.claims[0].confidence.basis is ConfidenceBasis.UNKNOWN


def test_same_genre_from_two_sources_is_consistent_and_retains_both_claims() -> None:
    result = PerceptualContextResolver().resolve(
        claims=[
            _claim("genre.user", ContextDimension.GENRE, "techno"),
            _claim(
                "genre.project",
                ContextDimension.GENRE,
                "techno",
                provenance=ContextProvenance.PROJECT_DECLARED,
            ),
        ]
    )
    dimension = result.dimension(ContextDimension.GENRE)
    assert dimension.status is ContextResolutionStatus.RESOLVED
    assert dimension.values == ["techno"]
    assert len(dimension.claims) == 2


def test_conflicting_genre_is_reported_without_a_winner() -> None:
    result = PerceptualContextResolver().resolve(
        claims=[
            _claim("genre.a", ContextDimension.GENRE, "techno"),
            _claim("genre.b", ContextDimension.GENRE, "ambient"),
        ]
    )
    assert result.status is ContextResolutionStatus.CONFLICT
    assert result.dimension(ContextDimension.GENRE).values == ["techno", "ambient"]


def test_resolved_dimension_rejects_values_not_derived_from_claims() -> None:
    claim = _claim("genre.techno", ContextDimension.GENRE, "techno")
    with pytest.raises(ValueError, match="distinct claim values"):
        ResolvedContextDimension(
            context_dimension=ContextDimension.GENRE,
            status=ContextResolutionStatus.RESOLVED,
            values=["ambient"],
            claims=[claim],
        )
    payload = {
        "context_dimension": "genre",
        "status": "resolved",
        "values": ["ambient"],
        "claims": [claim.to_dict()],
    }
    with pytest.raises(ValueError, match="distinct claim values"):
        ResolvedContextDimension.from_dict(payload)


def test_resolved_dimension_rejects_missing_duplicate_and_reordered_values() -> None:
    claims = [
        _claim("genre.techno", ContextDimension.GENRE, "techno"),
        _claim("genre.ambient", ContextDimension.GENRE, "ambient"),
    ]
    for values in (["techno"], ["techno", "ambient", "ambient"], ["ambient", "techno"]):
        with pytest.raises(ValueError, match="distinct claim values"):
            ResolvedContextDimension(
                context_dimension=ContextDimension.GENRE,
                status=ContextResolutionStatus.CONFLICT,
                values=values,
                claims=claims,
            )


def test_resolved_dimension_accepts_same_value_from_multiple_sources() -> None:
    claims = [
        _claim("genre.user", ContextDimension.GENRE, "techno"),
        _claim(
            "genre.project",
            ContextDimension.GENRE,
            "techno",
            provenance=ContextProvenance.PROJECT_DECLARED,
        ),
    ]
    dimension = ResolvedContextDimension(
        context_dimension=ContextDimension.GENRE,
        status=ContextResolutionStatus.RESOLVED,
        values=["techno"],
        claims=claims,
    )
    assert len(dimension.claims) == 2


def test_listener_preference_values_are_canonical_distinct_claim_values() -> None:
    claims = [
        _claim("preference.a.1", ContextDimension.LISTENER_PREFERENCE, "A"),
        _claim("preference.b", ContextDimension.LISTENER_PREFERENCE, "B"),
        _claim("preference.a.2", ContextDimension.LISTENER_PREFERENCE, "A"),
    ]
    dimension = ResolvedContextDimension(
        context_dimension=ContextDimension.LISTENER_PREFERENCE,
        status=ContextResolutionStatus.RESOLVED,
        values=["A", "B"],
        claims=claims,
    )
    assert dimension.values == ["A", "B"]
    assert len(dimension.claims) == 3
    with pytest.raises(ValueError, match="distinct claim values"):
        replace(dimension, values=["A"])


def test_delivery_target_exact_binding_selects_exact_policy_identity() -> None:
    resolution = PerceptualContextResolver().resolve(
        PerceptualContext(delivery_target="fixture.delivery")
    )
    result = ContextPolicySelector().select(resolution, [_binding()], [_policy()])
    assert result.status is ContextPolicySelectionStatus.SELECTED
    assert result.selected_policy.policy_id == "fixture.policy"
    assert result.selected_policy.version == "1.0.0"


def test_delivery_target_mismatch_selects_no_policy() -> None:
    resolution = PerceptualContextResolver().resolve(
        PerceptualContext(delivery_target="other.delivery")
    )
    result = ContextPolicySelector().select(resolution, [_binding()], [_policy()])
    assert result.status is ContextPolicySelectionStatus.NO_MATCH
    assert result.selected_policy is None


def test_multiple_matching_bindings_are_ambiguous_without_ranking() -> None:
    resolution = PerceptualContextResolver().resolve(
        PerceptualContext(delivery_target="fixture.delivery")
    )
    result = ContextPolicySelector().select(
        resolution,
        [_binding(binding_id="binding.a"), _binding(binding_id="binding.b")],
        [_policy()],
    )
    assert result.status is ContextPolicySelectionStatus.AMBIGUOUS
    assert result.matched_binding_ids == ["binding.a", "binding.b"]
    assert result.selected_policy is None


def test_no_bindings_returns_no_match_without_fallback() -> None:
    resolution = PerceptualContextResolver().resolve(PerceptualContext(genre="fixture"))
    result = ContextPolicySelector().select(resolution, [], [_policy()])
    assert result.status is ContextPolicySelectionStatus.NO_MATCH


def test_missing_or_invalid_provenance_is_rejected() -> None:
    claim = _claim("genre", ContextDimension.GENRE, "fixture")
    with pytest.raises(TypeError, match="provenance"):
        replace(claim, provenance=None)
    with pytest.raises(ValueError, match="source"):
        replace(claim, source=" ")


def test_reference_specification_requires_identity_version_and_is_not_conformance() -> None:
    with pytest.raises(ValueError, match="source_version"):
        _claim(
            "reference",
            ContextDimension.ARTISTIC_INTENT,
            "Listening context references ITU-R BS.1116-3 only; conformance not asserted",
            provenance=ContextProvenance.REFERENCE_SPECIFICATION,
            source="ITU-R BS.1116-3",
        )
    claim = _claim(
        "reference",
        ContextDimension.ARTISTIC_INTENT,
        "Listening context references ITU-R BS.1116-3 only; conformance not asserted",
        provenance=ContextProvenance.REFERENCE_SPECIFICATION,
        source="ITU-R BS.1116-3",
        source_version="02/2015",
    )
    assert "conformance not asserted" in claim.value


def test_numeric_listening_spl_is_explicit_finite_and_uninterpreted() -> None:
    claim = _claim("spl.declared", ContextDimension.LISTENING_LEVEL_DB_SPL, 72.0)
    result = PerceptualContextResolver().resolve(claims=[claim])
    assert result.dimension(ContextDimension.LISTENING_LEVEL_DB_SPL).values == [72.0]
    with pytest.raises(ValueError, match="finite"):
        replace(claim, value=float("nan"))


def test_measured_listening_spl_requires_measurement_metadata() -> None:
    with pytest.raises(ValueError, match="measurement metadata"):
        _claim(
            "spl.measured",
            ContextDimension.LISTENING_LEVEL_DB_SPL,
            72.0,
            provenance=ContextProvenance.MEASURED_LISTENING_CONDITION,
        )
    metadata = ListeningConditionMeasurement(
        measurement_method="Calibrated sound-level meter supplied by caller",
        weighting="Z weighting",
        time_basis="Caller-declared 60 second equivalent level",
        acoustic_reference="dB SPL re 20 micropascals",
        measurement_position_context="Mix position at seated ear height",
    )
    claim = _claim(
        "spl.measured",
        ContextDimension.LISTENING_LEVEL_DB_SPL,
        72.0,
        provenance=ContextProvenance.MEASURED_LISTENING_CONDITION,
        measurement=metadata,
    )
    assert claim.measurement == metadata


def test_no_audio_or_digital_level_inference_api_exists() -> None:
    resolver = PerceptualContextResolver()
    assert not hasattr(resolver, "resolve_audio")
    assert not hasattr(resolver, "infer_listening_level_db_spl")


def test_qualitative_and_numeric_listening_levels_remain_separate() -> None:
    result = PerceptualContextResolver().resolve(
        PerceptualContext(listening_level=ListeningLevel.LOW, listening_level_db_spl=72.0)
    )
    assert result.dimension(ContextDimension.LISTENING_LEVEL_QUALITATIVE).values == [
        ListeningLevel.LOW
    ]
    assert result.dimension(ContextDimension.LISTENING_LEVEL_DB_SPL).values == [72.0]


def test_mono_required_is_context_only_and_does_not_downmix() -> None:
    result = PerceptualContextResolver().resolve(
        PerceptualContext(mono_compatibility=MonoCompatibility.REQUIRED)
    )
    assert result.dimension(ContextDimension.MONO_COMPATIBILITY).values == [
        MonoCompatibility.REQUIRED
    ]
    assert not hasattr(result, "audio")
    assert not hasattr(PerceptualContextResolver(), "downmix")


def test_playback_expectation_remains_a_context_only_reference() -> None:
    reference = PlaybackProfileReference("fixture.headphones", "1.0.0")
    result = PerceptualContextResolver().resolve(PerceptualContext(playback_expectation=reference))
    assert result.dimension(ContextDimension.PLAYBACK_EXPECTATION).values == [reference]
    assert not hasattr(result, "transfer")


def test_genre_binding_selects_policy_but_never_creates_criteria() -> None:
    binding = replace(
        _binding(),
        requirements=[
            ContextRequirement(
                ContextDimension.GENRE,
                ContextRequirementOperator.EQUALS,
                "electronic",
            )
        ],
    )
    policy = _policy()
    resolution = PerceptualContextResolver().resolve(PerceptualContext(genre="electronic"))
    selected = ContextPolicySelector().select(resolution, [binding], [policy])
    assert selected.selected_policy is policy
    assert selected.selected_policy.criteria == policy.criteria


def test_listener_preferences_and_artistic_intent_round_trip_exactly() -> None:
    context = PerceptualContext(
        artistic_intent="dark tonal balance",
        listener_preferences=["prefers low playback level", "headphone-first workflow"],
    )
    resolution = PerceptualContextResolver().resolve(context)
    assert resolution.dimension(ContextDimension.ARTISTIC_INTENT).values == ["dark tonal balance"]
    assert resolution.dimension(ContextDimension.LISTENER_PREFERENCE).values == [
        "prefers low playback level",
        "headphone-first workflow",
    ]
    assert resolution.status is ContextResolutionStatus.RESOLVED


def test_policy_id_and_version_must_both_match_exactly() -> None:
    resolution = PerceptualContextResolver().resolve(
        PerceptualContext(delivery_target="fixture.delivery")
    )
    result = ContextPolicySelector().select(resolution, [_binding()], [_policy(version="2.0.0")])
    assert result.status is ContextPolicySelectionStatus.UNRESOLVED
    assert result.selected_policy is None


def test_conflicting_delivery_context_prevents_policy_selection() -> None:
    resolution = PerceptualContextResolver().resolve(
        claims=[
            _claim("delivery.a", ContextDimension.DELIVERY_TARGET, "fixture.delivery.a"),
            _claim("delivery.b", ContextDimension.DELIVERY_TARGET, "fixture.delivery.b"),
        ]
    )
    result = ContextPolicySelector().select(
        resolution, [_binding("fixture.delivery.a")], [_policy()]
    )
    assert result.status is ContextPolicySelectionStatus.CONFLICT
    assert result.selected_policy is None


def test_selected_status_requires_resolved_context_and_exactly_one_match() -> None:
    selector = ContextPolicySelector()
    selected = selector.select(
        PerceptualContextResolver().resolve(PerceptualContext(delivery_target="fixture.delivery")),
        [_binding()],
        [_policy()],
    )
    conflict = PerceptualContextResolver().resolve(
        claims=[
            _claim("genre.a", ContextDimension.GENRE, "A"),
            _claim("genre.b", ContextDimension.GENRE, "B"),
        ]
    )
    with pytest.raises(ValueError, match="resolved context"):
        replace(selected, resolution=conflict)
    for matched_ids in ([], ["fixture.binding", "other.binding"]):
        with pytest.raises(ValueError, match="exactly its selected binding"):
            replace(selected, matched_binding_ids=matched_ids)


def test_nonselected_statuses_enforce_resolution_and_match_cardinality() -> None:
    resolver = PerceptualContextResolver()
    selector = ContextPolicySelector()
    resolved = resolver.resolve(PerceptualContext(delivery_target="fixture.delivery"))
    conflict_resolution = resolver.resolve(
        claims=[
            _claim("delivery.a", ContextDimension.DELIVERY_TARGET, "A"),
            _claim("delivery.b", ContextDimension.DELIVERY_TARGET, "B"),
        ]
    )
    no_match = selector.select(resolved, [], [_policy()])
    conflict = selector.select(conflict_resolution, [_binding("A")], [_policy()])
    ambiguous = selector.select(
        resolved,
        [_binding(binding_id="binding.a"), _binding(binding_id="binding.b")],
        [_policy()],
    )
    unresolved = selector.select(resolved, [_binding()], [_policy(version="2.0.0")])

    with pytest.raises(ValueError, match="no-match.*matched bindings"):
        replace(no_match, matched_binding_ids=["binding.a"])
    forged_payload = no_match.to_dict()
    forged_payload["matched_binding_ids"] = ["binding.a"]
    with pytest.raises(ValueError, match="no-match.*matched bindings"):
        ContextPolicySelectionResult.from_dict(forged_payload)
    with pytest.raises(ValueError, match="no-match.*conflicting context"):
        replace(no_match, resolution=conflict_resolution)
    with pytest.raises(ValueError, match="conflict.*matched bindings"):
        replace(conflict, matched_binding_ids=["binding.a"])
    with pytest.raises(ValueError, match="conflict.*conflicting context"):
        replace(conflict, resolution=resolved)
    with pytest.raises(ValueError, match="at least two"):
        replace(ambiguous, matched_binding_ids=["binding.a"])
    with pytest.raises(ValueError, match="unique"):
        replace(ambiguous, matched_binding_ids=["binding.a", "binding.a"])
    with pytest.raises(ValueError, match="ambiguous.*resolved context"):
        replace(ambiguous, resolution=conflict_resolution)
    for matched_ids in ([], ["binding.a", "binding.b"]):
        with pytest.raises(ValueError, match="exactly one"):
            replace(unresolved, matched_binding_ids=matched_ids)
    with pytest.raises(ValueError, match="unresolved.*resolved context"):
        replace(unresolved, resolution=conflict_resolution)


def test_selector_generated_statuses_all_satisfy_transport_invariants() -> None:
    resolver = PerceptualContextResolver()
    selector = ContextPolicySelector()
    resolved = resolver.resolve(PerceptualContext(delivery_target="fixture.delivery"))
    conflict_resolution = resolver.resolve(
        claims=[
            _claim("delivery.a", ContextDimension.DELIVERY_TARGET, "A"),
            _claim("delivery.b", ContextDimension.DELIVERY_TARGET, "B"),
        ]
    )
    results = [
        selector.select(resolved, [_binding()], [_policy()]),
        selector.select(conflict_resolution, [_binding("A")], [_policy()]),
        selector.select(
            resolved,
            [_binding(binding_id="binding.a"), _binding(binding_id="binding.b")],
            [_policy()],
        ),
        selector.select(resolved, [], [_policy()]),
        selector.select(resolved, [_binding()], [_policy(version="2.0.0")]),
    ]
    assert [result.status for result in results] == [
        ContextPolicySelectionStatus.SELECTED,
        ContextPolicySelectionStatus.CONFLICT,
        ContextPolicySelectionStatus.AMBIGUOUS,
        ContextPolicySelectionStatus.NO_MATCH,
        ContextPolicySelectionStatus.UNRESOLVED,
    ]
    assert [
        ContextPolicySelectionResult.from_dict(result.to_dict()) for result in results
    ] == results


def test_json_round_trip_preserves_typed_values_and_selection() -> None:
    resolution = PerceptualContextResolver().resolve(
        PerceptualContext(
            genre="fixture",
            listening_level=ListeningLevel.MODERATE,
            playback_expectation=PlaybackProfileReference("fixture.profile", "1.0.0"),
            mono_compatibility=MonoCompatibility.PREFERRED,
        )
    )
    assert ContextResolutionResult.from_dict(resolution.to_dict()) == resolution
    selection = ContextPolicySelector().select(
        PerceptualContextResolver().resolve(PerceptualContext(delivery_target="fixture.delivery")),
        [_binding()],
        [_policy()],
    )
    payload = selection.to_dict()
    assert ContextPolicySelectionResult.from_dict(payload) == selection
    json.dumps(payload, allow_nan=False)


def test_repeated_resolution_and_selection_are_deterministic() -> None:
    context = PerceptualContext(delivery_target="fixture.delivery", genre="fixture")
    resolver = PerceptualContextResolver()
    first = resolver.resolve(context)
    second = resolver.resolve(context)
    assert first == second
    selector = ContextPolicySelector()
    assert selector.select(first, [_binding()], [_policy()]) == selector.select(
        second, [_binding()], [_policy()]
    )


def test_exact_matching_is_case_sensitive_and_no_fuzzy_path_exists() -> None:
    resolution = PerceptualContextResolver().resolve(
        PerceptualContext(delivery_target="Fixture.Delivery")
    )
    result = ContextPolicySelector().select(resolution, [_binding("fixture.delivery")], [_policy()])
    assert result.status is ContextPolicySelectionStatus.NO_MATCH
    assert not hasattr(ContextPolicySelector(), "fuzzy_match")


def test_frozen_sprint_1_contract_schema_and_capability_truth() -> None:
    assert PERCEPTUAL_SCHEMA_VERSION == "1.0.0"
    assert registry.get("perceptual_context_foundation").status is CapabilityStatus.IMPLEMENTED
    assert registry.get("context_policy_binding").status is CapabilityStatus.IMPLEMENTED
    for prohibited in (
        "genre_intelligence",
        "listener_model",
        "delivery_optimization",
        "mastering_target_prediction",
        "platform_mastering",
        "context_ai",
    ):
        assert registry.get(prohibited) is None


def test_lightweight_perception_and_context_resolution_import_avoid_dsp_and_ml() -> None:
    repository = Path(__file__).resolve().parents[1]
    program = (
        "import sys; "
        f"sys.path.insert(0, {str(repository)!r}); "
        "import phasenox.perception; import phasenox.perception.context_resolution; "
        "assert 'numpy' not in sys.modules; assert 'torch' not in sys.modules; "
        "assert 'phasenox.perception.translation' not in sys.modules; "
        "assert 'phasenox.perception.transfer' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
