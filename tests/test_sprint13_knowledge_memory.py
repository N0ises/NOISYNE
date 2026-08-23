from __future__ import annotations

import pytest

from phasenox.perception import (
    HistoryActor,
    KnowledgeFilter,
    KnowledgeMemoryType,
    KnowledgeQuery,
    KnowledgeRetrievalResult,
    MemoryItem,
    MemoryPayload,
    MemoryScope,
    MemoryStore,
    PersonalizationEffect,
    PersonalizationPolicy,
    ProjectHistoryEvent,
    ProvenanceKind,
    ReferenceMemoryItem,
    RetrievedKnowledgeItem,
    TrustBasis,
    UserPreferenceItem,
)
from phasenox.perception.knowledge_store import InMemoryMemoryStore
from phasenox.perception.validation_contracts import ValidationStatus
from phasenox.perception.validation_matrix import PerceptualValidationMatrix
from phasenox.runtime.capabilities import CapabilityStatus, registry


def _memory_item(
    memory_id: str = "m1",
    memory_type: KnowledgeMemoryType = KnowledgeMemoryType.USER_PREFERENCE,
    scope: MemoryScope = MemoryScope.PROJECT,
    provenance: ProvenanceKind = ProvenanceKind.USER_ENTERED,
    source_identity: str = "user_dialog",
    payload_value: object = {"target_lufs": -9.0},
    payload_type: str = "user_preference",
    project_id: str | None = "project_a",
    user_id: str | None = "user_1",
    mutable: bool | None = None,
    trust_basis: TrustBasis = TrustBasis.DECLARED,
    **kwargs: object,
) -> MemoryItem:
    if mutable is None:
        # Historical/scientific records are append-oriented by design and must be
        # immutable once stored.  Callers may still explicitly override for tests.
        mutable = memory_type not in (
            KnowledgeMemoryType.PROJECT_HISTORY,
            KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
        )
    return MemoryItem(
        memory_id=memory_id,
        memory_type=memory_type,
        scope=scope,
        provenance=provenance,
        source_identity=source_identity,
        payload=MemoryPayload(payload_type=payload_type, value=payload_value),
        project_id=project_id,
        user_id=user_id,
        mutable=mutable,
        trust_basis=trust_basis,
        **kwargs,
    )


# =============================================================================
# 1. Serialization round-trip
# =============================================================================


class TestSerializationRoundTrip:
    def test_memory_item_round_trip(self) -> None:
        item = _memory_item()
        data = item.to_dict()
        restored = MemoryItem.from_dict(data)
        assert restored == item

    def test_knowledge_query_and_result_round_trip(self) -> None:
        query = KnowledgeQuery(
            query_id="q1",
            provider_identity="noisyne.test",
            filters=KnowledgeFilter(
                memory_types=[KnowledgeMemoryType.USER_PREFERENCE],
                scopes=[MemoryScope.PROJECT],
            ),
        )
        assert KnowledgeQuery.from_dict(query.to_dict()) == query

        item = _memory_item()
        result = RetrievedKnowledgeItem(
            result_id="r1",
            query_id="q1",
            memory_item=item,
            rank=0,
            retrieval_score=0.75,
            score_semantics="cosine_similarity_normalized",
        )
        assert RetrievedKnowledgeItem.from_dict(result.to_dict()) == result

        aggregate = KnowledgeRetrievalResult(
            query_id="q1",
            provider_identity="noisyne.test",
            results=[result],
            retrieval_policy="filter_sort",
        )
        assert KnowledgeRetrievalResult.from_dict(aggregate.to_dict()) == aggregate

    def test_user_preference_round_trip(self) -> None:
        pref = UserPreferenceItem(
            preference_id="p1",
            category="export_target",
            payload=MemoryPayload(payload_type="preference", value="streaming"),
        )
        assert UserPreferenceItem.from_dict(pref.to_dict()) == pref

    def test_project_history_event_round_trip(self) -> None:
        event = ProjectHistoryEvent(
            event_id="e1",
            event_type="analysis_performed",
            project_id="project_a",
            actor=HistoryActor.SYSTEM,
            description="analysis completed",
            related_memory_ids=["m1"],
            timestamp="2026-08-17T12:00:00Z",
        )
        assert ProjectHistoryEvent.from_dict(event.to_dict()) == event

    def test_reference_memory_item_round_trip(self) -> None:
        ref = ReferenceMemoryItem(
            reference_identity="ref_1",
            source_path="/projects/a/refs/ref1.wav",
            comparison_mode="raw_level",
            project_associations=["project_a"],
            tags=["piano", "reference"],
            annotations=[MemoryPayload(payload_type="note", value="warm reference")],
        )
        assert ReferenceMemoryItem.from_dict(ref.to_dict()) == ref

    def test_personalization_policy_round_trip(self) -> None:
        policy = PersonalizationPolicy(
            policy_id="pol1",
            allowed_effects=[PersonalizationEffect.PRESENTATION, PersonalizationEffect.DEFAULTS],
        )
        assert PersonalizationPolicy.from_dict(policy.to_dict()) == policy


# =============================================================================
# 2. Stable memory IDs and identity
# =============================================================================


class TestStableIdentity:
    def test_same_inputs_same_memory_id(self) -> None:
        item_a = _memory_item(memory_id="pref_1")
        item_b = _memory_item(memory_id="pref_1")
        assert item_a.memory_id == item_b.memory_id
        assert item_a == item_b

    def test_distinct_ids_remain_distinct(self) -> None:
        item_a = _memory_item(memory_id="m_a")
        item_b = _memory_item(memory_id="m_b")
        assert item_a.memory_id != item_b.memory_id
        assert item_a != item_b


# =============================================================================
# 3. Source and provenance preservation
# =============================================================================


class TestProvenancePreservation:
    def test_memory_item_preserves_provenance(self) -> None:
        item = _memory_item(
            memory_type=KnowledgeMemoryType.VERIFIED_PROJECT_KNOWLEDGE,
            provenance=ProvenanceKind.DERIVED,
            source_identity="derived_from_analysis",
            trust_basis=TrustBasis.VERIFIED,
        )
        assert item.provenance is ProvenanceKind.DERIVED
        assert item.source_identity == "derived_from_analysis"
        restored = MemoryItem.from_dict(item.to_dict())
        assert restored.provenance is ProvenanceKind.DERIVED

    def test_model_generated_requires_unverified(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_type=KnowledgeMemoryType.MODEL_GENERATED_CONTENT,
                provenance=ProvenanceKind.MODEL_GENERATED,
                trust_basis=TrustBasis.VERIFIED,
            )

    def test_scientific_reference_requires_verified_or_validated(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
                provenance=ProvenanceKind.IMPORTED,
                trust_basis=TrustBasis.DECLARED,
            )

    def test_validated_requires_validation_link(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(trust_basis=TrustBasis.VALIDATED)


# =============================================================================
# 4. Scope isolation
# =============================================================================


class TestScopeIsolation:
    def test_project_memory_isolated_from_global_user(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="global_1", scope=MemoryScope.GLOBAL_USER))
        store.put(_memory_item(memory_id="project_1", scope=MemoryScope.PROJECT, project_id="p1"))
        project_items = store.list(scope=MemoryScope.PROJECT, project_id="p1")
        assert len(project_items) == 1
        assert project_items[0].memory_id == "project_1"

    def test_session_memory_isolated(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="session_1", scope=MemoryScope.SESSION, project_id="p1"))
        session_items = store.list(scope=MemoryScope.SESSION, project_id="p1")
        assert len(session_items) == 1

    def test_reference_library_scope_isolated(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="ref_1",
                scope=MemoryScope.REFERENCE_LIBRARY,
                memory_type=KnowledgeMemoryType.RETRIEVED_KNOWLEDGE,
                provenance=ProvenanceKind.RETRIEVED,
                source_identity="reference_retrieval",
                trust_basis=TrustBasis.RETRIEVED,
            )
        )
        ref_items = store.list(scope=MemoryScope.REFERENCE_LIBRARY)
        assert len(ref_items) == 1


# =============================================================================
# 5. No silent scope promotion
# =============================================================================


class TestNoSilentScopePromotion:
    def test_put_does_not_promote_session_to_project(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="s1", scope=MemoryScope.SESSION, project_id="p1"))
        project_items = store.list(scope=MemoryScope.PROJECT, project_id="p1")
        assert len(project_items) == 0

    def test_clear_scope_respects_scope_only(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="global_1", scope=MemoryScope.GLOBAL_USER, user_id="u1"))
        store.put(_memory_item(memory_id="project_1", scope=MemoryScope.PROJECT, project_id="p1"))
        # SESSION requires explicit project_id or all_projects=True to avoid
        # accidental broad deletion.
        deleted = store.clear_scope(MemoryScope.SESSION, all_projects=True)
        assert deleted == 0
        assert store.count() == 2


# =============================================================================
# 6. Deterministic ordering
# =============================================================================


class TestDeterministicOrdering:
    def test_search_results_are_deterministically_ordered(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="m_early",
                scope=MemoryScope.PROJECT,
                project_id="p1",
                created_at="2026-08-17T10:00:00Z",
            )
        )
        store.put(
            _memory_item(
                memory_id="m_late",
                scope=MemoryScope.PROJECT,
                project_id="p1",
                created_at="2026-08-17T11:00:00Z",
            )
        )
        query = KnowledgeQuery(
            query_id="q_order",
            provider_identity="noisyne.test",
            filters=KnowledgeFilter(scopes=[MemoryScope.PROJECT], project_id="p1"),
        )
        result = store.search(query)
        assert [r.memory_item.memory_id for r in result.results] == ["m_early", "m_late"]


# =============================================================================
# 7. Duplicate semantics
# =============================================================================


class TestDuplicateSemantics:
    def test_same_id_upserts(self) -> None:
        store = InMemoryMemoryStore()
        first = _memory_item(
            memory_id="m1",
            payload_value={"target_lufs": -9.0},
            created_at="2026-08-17T10:00:00Z",
        )
        second = _memory_item(
            memory_id="m1",
            payload_value={"target_lufs": -10.0},
            created_at="2026-08-17T10:00:00Z",
            updated_at="2026-08-17T11:00:00Z",
        )
        store.put(first)
        store.put(second)
        assert store.count() == 1
        assert store.get("m1") == second

    def test_similar_payloads_remain_distinct(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="m_a", payload_value={"x": 1}))
        store.put(_memory_item(memory_id="m_b", payload_value={"x": 1}))
        assert store.count() == 2


# =============================================================================
# 8. Explicit delete / forget
# =============================================================================


class TestExplicitDelete:
    def test_delete_existing_item(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="m1"))
        assert store.delete("m1") is True
        assert store.get("m1") is None
        assert store.count() == 0

    def test_delete_missing_item(self) -> None:
        store = InMemoryMemoryStore()
        assert store.delete("missing") is False

    def test_clear_scope_deletes_only_matching_items(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="g1", scope=MemoryScope.GLOBAL_USER, user_id="u1"))
        store.put(_memory_item(memory_id="p1", scope=MemoryScope.PROJECT, project_id="p1"))
        store.put(_memory_item(memory_id="p2", scope=MemoryScope.PROJECT, project_id="p2"))
        deleted = store.clear_scope(MemoryScope.PROJECT, project_id="p1")
        assert deleted == 1
        assert store.get("p1") is None
        assert store.get("p2") is not None
        assert store.get("g1") is not None


# =============================================================================
# 8b. Append-oriented project history / scientific immutability
# =============================================================================


class TestAppendOrientedImmutability:
    def test_project_history_must_be_immutable(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_id="h1",
                memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                provenance=ProvenanceKind.SYSTEM_OBSERVED,
                trust_basis=TrustBasis.UNVERIFIED,
                mutable=True,
            )

    def test_project_history_payload_cannot_be_rewritten(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="h1",
                memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                provenance=ProvenanceKind.SYSTEM_OBSERVED,
                trust_basis=TrustBasis.UNVERIFIED,
                payload_value={"event": "analysis_performed"},
                created_at="2026-08-17T10:00:00Z",
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="h1",
                    memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                    provenance=ProvenanceKind.SYSTEM_OBSERVED,
                    trust_basis=TrustBasis.UNVERIFIED,
                    payload_value={"event": "analysis_never_happened"},
                    created_at="2026-08-17T10:00:00Z",
                )
            )
        assert store.get("h1").payload.value == {"event": "analysis_performed"}

    def test_scientific_reference_must_be_immutable(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_id="ref1",
                memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
                provenance=ProvenanceKind.IMPORTED,
                trust_basis=TrustBasis.VERIFIED,
                mutable=True,
            )

    def test_scientific_reference_payload_cannot_change_claim(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="ref1",
                memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
                provenance=ProvenanceKind.IMPORTED,
                source_identity="iso_226_2023",
                trust_basis=TrustBasis.VALIDATED,
                validation_link="validation:sprint12:loudness_foundation",
                payload_value={"claim": "equal_loudness_contours"},
                created_at="2026-08-17T10:00:00Z",
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="ref1",
                    memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
                    provenance=ProvenanceKind.IMPORTED,
                    source_identity="iso_226_2023",
                    trust_basis=TrustBasis.VALIDATED,
                    validation_link="validation:sprint12:loudness_foundation",
                    payload_value={"claim": "different_claim"},
                    created_at="2026-08-17T10:00:00Z",
                )
            )
        assert store.get("ref1").payload.value == {"claim": "equal_loudness_contours"}


# =============================================================================
# 9. Stale / versioning
# =============================================================================


class TestStaleVersioning:
    def test_superseded_by_link(self) -> None:
        old = _memory_item(memory_id="old", superseded_by="new")
        assert old.superseded_by == "new"
        restored = MemoryItem.from_dict(old.to_dict())
        assert restored.superseded_by == "new"


# =============================================================================
# 10. Retrieval score semantics
# =============================================================================


class TestRetrievalScoreSemantics:
    def test_score_requires_semantics(self) -> None:
        with pytest.raises(ValueError):
            RetrievedKnowledgeItem(
                result_id="r1",
                query_id="q1",
                memory_item=_memory_item(),
                rank=0,
                retrieval_score=0.8,
                score_semantics=None,
            )

    def test_score_semantics_without_score_rejected(self) -> None:
        with pytest.raises(ValueError):
            RetrievedKnowledgeItem(
                result_id="r1",
                query_id="q1",
                memory_item=_memory_item(),
                rank=0,
                retrieval_score=None,
                score_semantics="cosine",
            )

    def test_score_is_finite(self) -> None:
        with pytest.raises(ValueError):
            RetrievedKnowledgeItem(
                result_id="r1",
                query_id="q1",
                memory_item=_memory_item(),
                rank=0,
                retrieval_score=float("inf"),
                score_semantics="cosine",
            )
        with pytest.raises(ValueError):
            RetrievedKnowledgeItem(
                result_id="r1",
                query_id="q1",
                memory_item=_memory_item(),
                rank=0,
                retrieval_score=float("nan"),
                score_semantics="cosine",
            )

    def test_unbounded_finite_score_is_allowed(self) -> None:
        # The contract does not impose a universal [0, 1] scale; provider-specific
        # semantics (e.g., distance, inner product) may legitimately lie outside it.
        result = RetrievedKnowledgeItem(
            result_id="r1",
            query_id="q1",
            memory_item=_memory_item(),
            rank=0,
            retrieval_score=-0.5,
            score_semantics="euclidean_distance_negative_example",
        )
        assert result.retrieval_score == pytest.approx(-0.5, abs=1e-12)

    def test_retrieval_score_not_percentage(self) -> None:
        result = RetrievedKnowledgeItem(
            result_id="r1",
            query_id="q1",
            memory_item=_memory_item(),
            rank=0,
            retrieval_score=0.75,
            score_semantics="cosine_similarity_normalized",
        )
        assert "%" not in result.score_semantics
        assert result.retrieval_score == pytest.approx(0.75, abs=1e-12)


# =============================================================================
# 11. Model-generated content remains unverified
# =============================================================================


class TestModelGeneratedMemory:
    def test_model_generated_payload_accepted(self) -> None:
        item = _memory_item(
            memory_id="mg1",
            memory_type=KnowledgeMemoryType.MODEL_GENERATED_CONTENT,
            provenance=ProvenanceKind.MODEL_GENERATED,
            source_identity="offline_template_provider",
            trust_basis=TrustBasis.UNVERIFIED,
        )
        assert item.memory_type is KnowledgeMemoryType.MODEL_GENERATED_CONTENT
        assert item.trust_basis is TrustBasis.UNVERIFIED


# =============================================================================
# 12. User preference cannot become scientific truth
# =============================================================================


class TestPreferenceCannotBecomeScientificTruth:
    def test_user_preference_contract(self) -> None:
        pref = UserPreferenceItem(
            preference_id="pref_1",
            category="preferred_loudness_target",
            payload=MemoryPayload(payload_type="preference", value=-9.0),
        )
        assert pref.category == "preferred_loudness_target"
        # Preference payload value is just a number, not a claim of scientific validity
        assert pref.payload.value == -9.0

    def test_preference_item_is_not_scientific_reference(self) -> None:
        item = _memory_item(memory_type=KnowledgeMemoryType.USER_PREFERENCE)
        assert item.memory_type is not KnowledgeMemoryType.SCIENTIFIC_REFERENCE

    def test_preference_cannot_be_validated(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_type=KnowledgeMemoryType.USER_PREFERENCE,
                trust_basis=TrustBasis.VALIDATED,
                validation_link="validation:preference",
            )


# =============================================================================
# 13. Project history cannot become source-bound evidence
# =============================================================================


class TestProjectHistoryCannotBecomeEvidence:
    def test_project_history_is_distinct_type(self) -> None:
        event = ProjectHistoryEvent(
            event_id="ev1",
            event_type="analysis_performed",
            project_id="p1",
            actor=HistoryActor.SYSTEM,
            description="ran perceptual analysis",
        )
        assert isinstance(event, ProjectHistoryEvent)
        # History records are not MemoryItem scientific evidence
        assert not isinstance(event, MemoryItem)


# =============================================================================
# 14. Memory cannot mutate Sprint 10/11 source truth
# =============================================================================


class TestMemoryDoesNotMutatePerceptualTruth:
    def test_memory_payload_is_separate_from_perceptual_result(self) -> None:
        item = _memory_item(
            memory_id="mem_fact",
            memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
            trust_basis=TrustBasis.VERIFIED,
            validation_link="validation:sprint12:brightness_correlate",
        )
        # Memory carries a reference to validation; it does not contain or mutate the
        # original Sprint 10/11 source-bound evidence or reasoning facts.
        assert item.validation_link is not None
        assert item.memory_type is KnowledgeMemoryType.SCIENTIFIC_REFERENCE


# =============================================================================
# 15. Invalid input rejection
# =============================================================================


class TestInvalidInputRejection:
    def test_empty_memory_id_rejected(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(memory_id="")

    def test_nan_payload_rejected(self) -> None:
        with pytest.raises(ValueError):
            MemoryPayload(payload_type="measurement", value=float("nan"))

    def test_inf_payload_rejected(self) -> None:
        with pytest.raises(ValueError):
            MemoryPayload(payload_type="measurement", value=float("inf"))

    def test_arbitrary_object_payload_rejected(self) -> None:
        with pytest.raises(TypeError):
            MemoryPayload(payload_type="object", value=object())  # type: ignore[arg-type]

    def test_invalid_enum_rejected(self) -> None:
        with pytest.raises(TypeError):
            MemoryItem(
                memory_id="bad",
                memory_type="not_an_enum",  # type: ignore[arg-type]
                scope=MemoryScope.PROJECT,
                provenance=ProvenanceKind.USER_ENTERED,
                source_identity="test",
                payload=MemoryPayload(payload_type="x", value=1),
            )


# =============================================================================
# 16. No credentials accepted
# =============================================================================


class TestNoCredentials:
    def test_memory_payload_rejects_secret_like_objects(self) -> None:
        # MemoryPayload only accepts JSON-safe primitives/containers; it cannot store
        # a custom credential object.
        class FakeCredential:
            token: str = "secret"

        with pytest.raises(TypeError):
            MemoryPayload(payload_type="credential", value=FakeCredential())  # type: ignore[arg-type]


# =============================================================================
# 17. Personalization policy safeguards
# =============================================================================


class TestPersonalizationPolicy:
    def test_default_policy_prohibits_scientific_evidence(self) -> None:
        policy = PersonalizationPolicy(
            policy_id="default",
            allowed_effects=[PersonalizationEffect.PRESENTATION],
        )
        assert "scientific_evidence" in policy.prohibited_effects

    def test_policy_without_scientific_evidence_prohibition_rejected(self) -> None:
        with pytest.raises(ValueError):
            PersonalizationPolicy(
                policy_id="bad",
                allowed_effects=[PersonalizationEffect.PRESENTATION],
                prohibited_effects=["defaults"],
            )


# =============================================================================
# 18. Capability / validation truth integration
# =============================================================================


class TestValidatedTrustSemantics:
    def test_validated_scientific_reference_is_asserted_reference_not_proof(self) -> None:
        # A caller can supply a validation_link, but the contract treats it as an
        # asserted external reference, not as authoritative scientific validation.
        item = _memory_item(
            memory_id="ref_1",
            memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
            provenance=ProvenanceKind.IMPORTED,
            source_identity="iso_226_2023",
            trust_basis=TrustBasis.VALIDATED,
            validation_link="validation:external:iso_226_2023",
        )
        assert item.trust_basis is TrustBasis.VALIDATED
        assert item.validation_link == "validation:external:iso_226_2023"
        # The memory object does not convert itself into a Sprint 10/11 GroundingFact
        # and does not mutate the Sprint 12 validation matrix.
        assert not hasattr(MemoryItem, "to_grounding_fact")

    def test_validation_link_alone_does_not_upgrade_foundation_status(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        record = matrix.by_capability("loudness_foundation")
        assert record is not None
        assert record.validation_status is ValidationStatus.FOUNDATION_ONLY


class TestCapabilityAndValidationTruth:
    def test_sprint13_capabilities_registered(self) -> None:
        for name in (
            "knowledge_memory_foundation",
            "personalization_foundation",
            "knowledge_retrieval_contract",
        ):
            cap = registry.get(name)
            assert cap is not None
            assert cap.status is CapabilityStatus.IMPLEMENTED

    def test_sprint13_matrix_records_are_foundation_only(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        for capability_id in (
            "knowledge_memory_foundation",
            "personalization_foundation",
            "knowledge_retrieval_contract",
        ):
            record = matrix.by_capability(capability_id)
            assert record is not None
            assert record.implementation_status is ValidationStatus.IMPLEMENTED
            assert record.validation_status is ValidationStatus.FOUNDATION_ONLY

    def test_sprint13_records_do_not_claim_validated(self) -> None:
        matrix = PerceptualValidationMatrix.build()
        sprint13 = [
            "knowledge_memory_foundation",
            "personalization_foundation",
            "knowledge_retrieval_contract",
        ]
        for capability_id in sprint13:
            record = matrix.by_capability(capability_id)
            assert record is not None
            assert record.validation_status is not ValidationStatus.VALIDATED
            for claim in record.supported_claims:
                assert "validated" not in claim.lower() or "must not" in claim.lower()


# =============================================================================
# 19. MemoryStore protocol conformance
# =============================================================================


class TestMemoryStoreProtocol:
    def test_in_memory_store_conforms_to_protocol(self) -> None:
        store = InMemoryMemoryStore()
        assert isinstance(store, MemoryStore)

    def test_store_search_filters_by_memory_type(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="pref_1",
                memory_type=KnowledgeMemoryType.USER_PREFERENCE,
                scope=MemoryScope.PROJECT,
                project_id="p1",
            )
        )
        store.put(
            _memory_item(
                memory_id="hist_1",
                memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                scope=MemoryScope.PROJECT,
                project_id="p1",
            )
        )
        query = KnowledgeQuery(
            query_id="q_type",
            provider_identity="noisyne.test",
            filters=KnowledgeFilter(
                memory_types=[KnowledgeMemoryType.USER_PREFERENCE],
                scopes=[MemoryScope.PROJECT],
                project_id="p1",
            ),
        )
        result = store.search(query)
        assert result.result_count == 1
        assert result.results[0].memory_item.memory_id == "pref_1"

    def test_store_search_returns_declared_provider_identity(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="m1", scope=MemoryScope.GLOBAL_USER))
        query = KnowledgeQuery(
            query_id="q_provider",
            provider_identity="custom.provider",
            filters=KnowledgeFilter(scopes=[MemoryScope.GLOBAL_USER]),
        )
        result = store.search(query)
        assert result.provider_identity == "noisyne.in_memory_memory_store"
        assert result.retrieval_policy == "deterministic_filter_sort"


# =============================================================================
# 20. Consent semantics
# =============================================================================


class TestConsentSemantics:
    def test_default_policy_requires_consent_but_does_not_grant_it(self) -> None:
        policy = PersonalizationPolicy(
            policy_id="default",
            allowed_effects=[PersonalizationEffect.PRESENTATION],
        )
        assert policy.requires_explicit_user_consent is True
        assert policy.consent_granted is False

    def test_explicit_consent_can_be_recorded(self) -> None:
        policy = PersonalizationPolicy(
            policy_id="explicit",
            allowed_effects=[PersonalizationEffect.PRESENTATION],
            requires_explicit_user_consent=True,
            consent_granted=True,
        )
        assert policy.consent_granted is True

    def test_policy_without_consent_requirement_remains_ungranted(self) -> None:
        policy = PersonalizationPolicy(
            policy_id="optional",
            allowed_effects=[PersonalizationEffect.PRESENTATION],
            requires_explicit_user_consent=False,
            consent_granted=False,
        )
        assert policy.requires_explicit_user_consent is False
        assert policy.consent_granted is False


# =============================================================================
# 21. Type / provenance / trust invariants
# =============================================================================


class TestTypeProvenanceTrustInvariants:
    @pytest.mark.parametrize(
        ("memory_type", "provenance", "trust_basis", "validation_link"),
        [
            (
                KnowledgeMemoryType.MODEL_GENERATED_CONTENT,
                ProvenanceKind.USER_ENTERED,
                TrustBasis.UNVERIFIED,
                None,
            ),
            (
                KnowledgeMemoryType.MODEL_GENERATED_CONTENT,
                ProvenanceKind.MODEL_GENERATED,
                TrustBasis.DECLARED,
                None,
            ),
            (
                KnowledgeMemoryType.RETRIEVED_KNOWLEDGE,
                ProvenanceKind.DERIVED,
                TrustBasis.RETRIEVED,
                None,
            ),
            (
                KnowledgeMemoryType.RETRIEVED_KNOWLEDGE,
                ProvenanceKind.RETRIEVED,
                TrustBasis.VALIDATED,
                "validation:retrieved",
            ),
            (
                KnowledgeMemoryType.USER_PREFERENCE,
                ProvenanceKind.SYSTEM_OBSERVED,
                TrustBasis.DECLARED,
                None,
            ),
            (
                KnowledgeMemoryType.USER_PREFERENCE,
                ProvenanceKind.USER_ENTERED,
                TrustBasis.VERIFIED,
                None,
            ),
            (
                KnowledgeMemoryType.USER_DECLARATION,
                ProvenanceKind.USER_ENTERED,
                TrustBasis.VALIDATED,
                "validation:declared",
            ),
            (
                KnowledgeMemoryType.PROJECT_HISTORY,
                ProvenanceKind.IMPORTED,
                TrustBasis.DECLARED,
                None,
            ),
            (
                KnowledgeMemoryType.PROJECT_HISTORY,
                ProvenanceKind.SYSTEM_OBSERVED,
                TrustBasis.VERIFIED,
                None,
            ),
            (
                KnowledgeMemoryType.VERIFIED_PROJECT_KNOWLEDGE,
                ProvenanceKind.USER_ENTERED,
                TrustBasis.VERIFIED,
                None,
            ),
            (
                KnowledgeMemoryType.VERIFIED_PROJECT_KNOWLEDGE,
                ProvenanceKind.DERIVED,
                TrustBasis.DECLARED,
                None,
            ),
            (
                KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
                ProvenanceKind.IMPORTED,
                TrustBasis.UNVERIFIED,
                None,
            ),
        ],
    )
    def test_invalid_combinations_rejected(
        self,
        memory_type: KnowledgeMemoryType,
        provenance: ProvenanceKind,
        trust_basis: TrustBasis,
        validation_link: str | None,
    ) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_type=memory_type,
                provenance=provenance,
                trust_basis=trust_basis,
                validation_link=validation_link,
            )

    def test_model_generated_requires_model_generated_provenance(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_id="mg_bad",
                memory_type=KnowledgeMemoryType.MODEL_GENERATED_CONTENT,
                provenance=ProvenanceKind.USER_ENTERED,
                trust_basis=TrustBasis.UNVERIFIED,
            )

    def test_retrieved_knowledge_cannot_claim_validated(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_id="rk_bad",
                memory_type=KnowledgeMemoryType.RETRIEVED_KNOWLEDGE,
                provenance=ProvenanceKind.RETRIEVED,
                source_identity="retrieval",
                trust_basis=TrustBasis.VALIDATED,
                validation_link="validation:retrieval",
            )

    def test_system_observation_requires_system_observed_and_unverified(self) -> None:
        with pytest.raises(ValueError):
            _memory_item(
                memory_id="so_bad",
                memory_type=KnowledgeMemoryType.SYSTEM_OBSERVATION,
                provenance=ProvenanceKind.USER_ENTERED,
                trust_basis=TrustBasis.UNVERIFIED,
            )
        with pytest.raises(ValueError):
            _memory_item(
                memory_id="so_bad2",
                memory_type=KnowledgeMemoryType.SYSTEM_OBSERVATION,
                provenance=ProvenanceKind.SYSTEM_OBSERVED,
                trust_basis=TrustBasis.VERIFIED,
            )


# =============================================================================
# 22. Store overwrite and deletion safety
# =============================================================================


class TestStoreOverwriteAndDeleteSafety:
    def test_cross_scope_overwrite_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="x", scope=MemoryScope.GLOBAL_USER))
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    scope=MemoryScope.PROJECT,
                    project_id="p1",
                )
            )
        assert store.get("x").scope is MemoryScope.GLOBAL_USER

    def test_project_id_change_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="x",
                scope=MemoryScope.PROJECT,
                project_id="p1",
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    scope=MemoryScope.PROJECT,
                    project_id="p2",
                )
            )

    def test_user_id_change_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="x",
                scope=MemoryScope.GLOBAL_USER,
                user_id="u1",
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    scope=MemoryScope.GLOBAL_USER,
                    user_id="u2",
                )
            )

    def test_immutable_item_overwrite_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(_memory_item(memory_id="x", mutable=False))
        with pytest.raises(ValueError):
            store.put(_memory_item(memory_id="x", mutable=True))
        assert store.get("x").mutable is False

    def test_memory_type_change_on_overwrite_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="x",
                memory_type=KnowledgeMemoryType.USER_PREFERENCE,
                provenance=ProvenanceKind.USER_ENTERED,
                trust_basis=TrustBasis.DECLARED,
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    memory_type=KnowledgeMemoryType.MODEL_GENERATED_CONTENT,
                    provenance=ProvenanceKind.MODEL_GENERATED,
                    trust_basis=TrustBasis.UNVERIFIED,
                )
            )
        assert store.get("x").memory_type is KnowledgeMemoryType.USER_PREFERENCE

    def test_provenance_change_on_overwrite_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="x",
                memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                provenance=ProvenanceKind.SYSTEM_OBSERVED,
                trust_basis=TrustBasis.UNVERIFIED,
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                    provenance=ProvenanceKind.USER_ENTERED,
                    trust_basis=TrustBasis.UNVERIFIED,
                )
            )
        assert store.get("x").provenance is ProvenanceKind.SYSTEM_OBSERVED

    def test_trust_basis_change_on_overwrite_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="x",
                memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                provenance=ProvenanceKind.SYSTEM_OBSERVED,
                trust_basis=TrustBasis.UNVERIFIED,
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    memory_type=KnowledgeMemoryType.PROJECT_HISTORY,
                    provenance=ProvenanceKind.SYSTEM_OBSERVED,
                    trust_basis=TrustBasis.DECLARED,
                )
            )
        assert store.get("x").trust_basis is TrustBasis.UNVERIFIED

    def test_source_identity_change_on_overwrite_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="x",
                memory_type=KnowledgeMemoryType.USER_PREFERENCE,
                provenance=ProvenanceKind.USER_ENTERED,
                source_identity="dialog_a",
                trust_basis=TrustBasis.DECLARED,
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    memory_type=KnowledgeMemoryType.USER_PREFERENCE,
                    provenance=ProvenanceKind.USER_ENTERED,
                    source_identity="dialog_b",
                    trust_basis=TrustBasis.DECLARED,
                )
            )
        assert store.get("x").source_identity == "dialog_a"

    def test_validation_link_change_on_overwrite_rejected(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="x",
                memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
                provenance=ProvenanceKind.IMPORTED,
                source_identity="standard_doc",
                trust_basis=TrustBasis.VALIDATED,
                validation_link="validation:sprint12:brightness_correlate",
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="x",
                    memory_type=KnowledgeMemoryType.SCIENTIFIC_REFERENCE,
                    provenance=ProvenanceKind.IMPORTED,
                    source_identity="standard_doc",
                    trust_basis=TrustBasis.VALIDATED,
                    validation_link="validation:arbitrary_other",
                )
            )
        assert store.get("x").validation_link == "validation:sprint12:brightness_correlate"

    def test_clear_project_requires_project_id_or_all_projects(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="p1",
                scope=MemoryScope.PROJECT,
                project_id="p1",
            )
        )
        with pytest.raises(ValueError):
            store.clear_scope(MemoryScope.PROJECT)
        with pytest.raises(ValueError):
            store.clear_scope(MemoryScope.SESSION)
        assert store.clear_scope(MemoryScope.PROJECT, project_id="p1") == 1

    def test_clear_global_user_requires_user_id_or_all_users(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="g1",
                scope=MemoryScope.GLOBAL_USER,
                user_id="u1",
            )
        )
        with pytest.raises(ValueError):
            store.clear_scope(MemoryScope.GLOBAL_USER)
        store.put(
            _memory_item(
                memory_id="g2",
                scope=MemoryScope.GLOBAL_USER,
                user_id="u2",
            )
        )
        assert store.clear_scope(MemoryScope.GLOBAL_USER, user_id="u1") == 1
        assert store.get("g1") is None
        assert store.get("g2") is not None

    def test_clear_scope_does_not_affect_other_scopes(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="g1",
                scope=MemoryScope.GLOBAL_USER,
                user_id="u1",
            )
        )
        store.put(
            _memory_item(
                memory_id="p1",
                scope=MemoryScope.PROJECT,
                project_id="p1",
            )
        )
        store.put(
            _memory_item(
                memory_id="p2",
                scope=MemoryScope.PROJECT,
                project_id="p2",
            )
        )
        store.put(
            _memory_item(
                memory_id="r1",
                scope=MemoryScope.REFERENCE_LIBRARY,
                memory_type=KnowledgeMemoryType.RETRIEVED_KNOWLEDGE,
                provenance=ProvenanceKind.RETRIEVED,
                source_identity="retrieval",
                trust_basis=TrustBasis.RETRIEVED,
            )
        )
        deleted = store.clear_scope(MemoryScope.PROJECT, project_id="p1")
        assert deleted == 1
        assert store.get("g1") is not None
        assert store.get("p1") is None
        assert store.get("p2") is not None
        assert store.get("r1") is not None

    def test_created_at_cannot_change_under_same_id(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="m1",
                created_at="2026-08-17T10:00:00Z",
            )
        )
        with pytest.raises(ValueError):
            store.put(
                _memory_item(
                    memory_id="m1",
                    created_at="2026-08-17T11:00:00Z",
                )
            )
        assert store.get("m1").created_at == "2026-08-17T10:00:00Z"


class TestPreferenceMutableUpdate:
    def test_user_preference_payload_and_updated_at_may_change(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="pref_1",
                memory_type=KnowledgeMemoryType.USER_PREFERENCE,
                provenance=ProvenanceKind.USER_ENTERED,
                trust_basis=TrustBasis.DECLARED,
                payload_value={"target_lufs": -9.0},
                created_at="2026-08-17T10:00:00Z",
            )
        )
        store.put(
            _memory_item(
                memory_id="pref_1",
                memory_type=KnowledgeMemoryType.USER_PREFERENCE,
                provenance=ProvenanceKind.USER_ENTERED,
                trust_basis=TrustBasis.DECLARED,
                payload_value={"target_lufs": -10.0},
                created_at="2026-08-17T10:00:00Z",
                updated_at="2026-08-17T11:00:00Z",
            )
        )
        item = store.get("pref_1")
        assert item.payload.value == {"target_lufs": -10.0}
        assert item.updated_at == "2026-08-17T11:00:00Z"
        assert item.created_at == "2026-08-17T10:00:00Z"


# =============================================================================
# 23. Deterministic tie ordering
# =============================================================================


class TestDeterministicTieOrdering:
    def test_same_created_at_ordered_by_memory_id(self) -> None:
        store = InMemoryMemoryStore()
        store.put(
            _memory_item(
                memory_id="b",
                scope=MemoryScope.PROJECT,
                project_id="p1",
                created_at="2026-08-17T10:00:00Z",
            )
        )
        store.put(
            _memory_item(
                memory_id="a",
                scope=MemoryScope.PROJECT,
                project_id="p1",
                created_at="2026-08-17T10:00:00Z",
            )
        )
        query = KnowledgeQuery(
            query_id="q_tie",
            provider_identity="noisyne.test",
            filters=KnowledgeFilter(scopes=[MemoryScope.PROJECT], project_id="p1"),
        )
        result = store.search(query)
        assert [r.memory_item.memory_id for r in result.results] == ["a", "b"]


# =============================================================================
# 24. Retrieval score semantics across providers
# =============================================================================


class TestCrossProviderScoreSemantics:
    def test_provider_semantics_are_preserved_not_normalized(self) -> None:
        item = _memory_item(memory_id="m1")
        result_a = RetrievedKnowledgeItem(
            result_id="r_a",
            query_id="q1",
            memory_item=item,
            rank=0,
            retrieval_score=0.9,
            score_semantics="provider_a_cosine_similarity",
        )
        result_b = RetrievedKnowledgeItem(
            result_id="r_b",
            query_id="q1",
            memory_item=item,
            rank=1,
            retrieval_score=0.9,
            score_semantics="provider_b_inner_product",
        )
        assert result_a.score_semantics != result_b.score_semantics
        assert result_a.retrieval_score == pytest.approx(0.9, abs=1e-12)
        assert result_b.retrieval_score == pytest.approx(0.9, abs=1e-12)
        # Scores must not be converted to percentages or merged into one scale.
        assert "%" not in result_a.score_semantics
        assert "%" not in result_b.score_semantics


# =============================================================================
# 25. Source truth cannot be mutated through memory objects
# =============================================================================


class TestSourceTruthImmutabilityViaMemory:
    def test_memory_item_has_no_grounding_fact_conversion(self) -> None:
        # Sprint 13 memory/retrieval must not silently manufacture Sprint 10/11
        # source-bound GroundingFacts.
        assert not hasattr(MemoryItem, "to_grounding_fact")
        assert not hasattr(RetrievedKnowledgeItem, "to_grounding_fact")

    def test_arbitrary_object_payload_rejected_including_complex_artifacts(self) -> None:
        class FakeSourceResult:
            value: str = "sprint10_source"

        with pytest.raises(TypeError):
            MemoryPayload(
                payload_type="source_result", value=FakeSourceResult()  # type: ignore[arg-type]
            )
