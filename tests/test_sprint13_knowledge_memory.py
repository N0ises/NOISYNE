from __future__ import annotations

import pytest

from noisyne.perception import (
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
from noisyne.perception.knowledge_store import InMemoryMemoryStore
from noisyne.perception.validation_contracts import ValidationStatus
from noisyne.perception.validation_matrix import PerceptualValidationMatrix
from noisyne.runtime.capabilities import CapabilityStatus, registry


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
    mutable: bool = True,
    trust_basis: TrustBasis = TrustBasis.DECLARED,
    **kwargs: object,
) -> MemoryItem:
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
        item = _memory_item(provenance=ProvenanceKind.IMPORTED, source_identity="imported_yaml")
        assert item.provenance is ProvenanceKind.IMPORTED
        assert item.source_identity == "imported_yaml"
        restored = MemoryItem.from_dict(item.to_dict())
        assert restored.provenance is ProvenanceKind.IMPORTED

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
        deleted = store.clear_scope(MemoryScope.SESSION)
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
        first = _memory_item(memory_id="m1", created_at="2026-08-17T10:00:00Z")
        second = _memory_item(memory_id="m1", created_at="2026-08-17T11:00:00Z")
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

    def test_score_is_normalized_finite(self) -> None:
        with pytest.raises(ValueError):
            RetrievedKnowledgeItem(
                result_id="r1",
                query_id="q1",
                memory_item=_memory_item(),
                rank=0,
                retrieval_score=1.5,
                score_semantics="cosine",
            )

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
