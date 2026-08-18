from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ._serialization import JsonContract
from .common import (
    MethodMetadata,
    _require_finite_number,
    _require_identifier,
)

KNOWLEDGE_FOUNDATION_METHOD_ID = "noisyne.knowledge_memory_foundation"
KNOWLEDGE_FOUNDATION_METHOD_VERSION = "1.0.0"
KNOWLEDGE_FOUNDATION_SCHEMA_VERSION = "1.0.0"


class KnowledgeMemoryType(str, Enum):
    """Strict source/type taxonomy for stored knowledge and memory.

    These categories deliberately remain distinct.  They must not be collapsed
    into a single generic "memory" type.
    """

    SCIENTIFIC_REFERENCE = "scientific_reference"
    VERIFIED_PROJECT_KNOWLEDGE = "verified_project_knowledge"
    RETRIEVED_KNOWLEDGE = "retrieved_knowledge"
    PROJECT_HISTORY = "project_history"
    USER_PREFERENCE = "user_preference"
    USER_DECLARATION = "user_declaration"
    SYSTEM_OBSERVATION = "system_observation"
    MODEL_GENERATED_CONTENT = "model_generated_content"


class MemoryScope(str, Enum):
    """Explicit scope boundary for a memory item."""

    GLOBAL_USER = "global_user"
    PROJECT = "project"
    SESSION = "session"
    REFERENCE_LIBRARY = "reference_library"


class ProvenanceKind(str, Enum):
    """Origin of a persisted memory or knowledge item."""

    USER_ENTERED = "user_entered"
    SYSTEM_OBSERVED = "system_observed"
    IMPORTED = "imported"
    RETRIEVED = "retrieved"
    DERIVED = "derived"
    MODEL_GENERATED = "model_generated"


class TrustBasis(str, Enum):
    """Basis on which an item's trustworthiness is declared.

    This is not a hidden confidence score.  It is an explicit categorization
    that preserves the Sprint 12 validation boundary.
    """

    VALIDATED = "validated"
    VERIFIED = "verified"
    DECLARED = "declared"
    RETRIEVED = "retrieved"
    UNVERIFIED = "unverified"


class PersonalizationEffect(str, Enum):
    """Allowed effect category of a personalization policy."""

    PRESENTATION = "presentation"
    DEFAULTS = "defaults"
    WORKFLOW_FOCUS = "workflow_focus"


class HistoryActor(str, Enum):
    """Actor that produced a project history event."""

    USER = "user"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class MemoryPayload(JsonContract):
    """Structured JSON-safe payload with explicit type declaration.

    Rejects opaque arbitrary objects; only JSON-safe primitives and containers
    are permitted.
    """

    payload_type: str
    value: dict[str, Any] | list[Any] | str | int | float | bool | None

    def __post_init__(self) -> None:
        _require_identifier(self.payload_type, "payload_type")
        self._validate_value(self.value, "value")

    @staticmethod
    def _validate_value(value: Any, field_name: str) -> None:
        if value is None or isinstance(value, str | bool | int):
            return
        if isinstance(value, float):
            _require_finite_number(value, field_name)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError(f"{field_name} mapping keys must be strings")
                MemoryPayload._validate_value(item, f"{field_name}[{key}]")
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                MemoryPayload._validate_value(item, f"{field_name}[{index}]")
            return
        raise TypeError(
            f"{field_name} must be a JSON-safe primitive or container, not {type(value).__name__}"
        )


@dataclass(frozen=True, slots=True)
class MemoryItem(JsonContract):
    """Core deterministic memory item contract.

    Preserves identity, type, provenance, scope, and trust basis.  Never stores
    arbitrary objects, chain-of-thought, hidden prompts, or credentials.
    """

    memory_id: str
    memory_type: KnowledgeMemoryType
    scope: MemoryScope
    provenance: ProvenanceKind
    source_identity: str
    payload: MemoryPayload
    schema_version: str = KNOWLEDGE_FOUNDATION_SCHEMA_VERSION
    mutable: bool = True
    trust_basis: TrustBasis = TrustBasis.UNVERIFIED
    validation_link: str | None = None
    project_id: str | None = None
    user_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    expiration: str | None = None
    superseded_by: str | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.memory_id, "memory_id")
        if not isinstance(self.memory_type, KnowledgeMemoryType):
            raise TypeError("memory_type must be a KnowledgeMemoryType")
        if not isinstance(self.scope, MemoryScope):
            raise TypeError("scope must be a MemoryScope")
        if not isinstance(self.provenance, ProvenanceKind):
            raise TypeError("provenance must be a ProvenanceKind")
        if not isinstance(self.trust_basis, TrustBasis):
            raise TypeError("trust_basis must be a TrustBasis")
        _require_identifier(self.source_identity, "source_identity")
        _require_identifier(self.schema_version, "schema_version")
        if self.validation_link is not None:
            _require_identifier(self.validation_link, "validation_link")
        if self.project_id is not None:
            _require_identifier(self.project_id, "project_id")
        if self.user_id is not None:
            _require_identifier(self.user_id, "user_id")
        for timestamp_name in ("created_at", "updated_at", "expiration"):
            value = getattr(self, timestamp_name)
            if value is not None:
                _require_identifier(value, timestamp_name)
        if self.superseded_by is not None:
            _require_identifier(self.superseded_by, "superseded_by")
        if self.trust_basis is TrustBasis.VALIDATED:
            if self.validation_link is None:
                raise ValueError("validated trust basis requires a validation_link")
            if self.memory_type is not KnowledgeMemoryType.SCIENTIFIC_REFERENCE:
                raise ValueError("validated trust basis is reserved for scientific_reference")

        # Conservative type/provenance/trust invariants: callers cannot relabel
        # unsafe information as trusted merely by choosing enum values.
        if (
            self.memory_type is KnowledgeMemoryType.SCIENTIFIC_REFERENCE
            and self.trust_basis
            not in (
                TrustBasis.VALIDATED,
                TrustBasis.VERIFIED,
            )
        ):
            raise ValueError("scientific_reference requires validated or verified trust basis")
        if self.memory_type is KnowledgeMemoryType.VERIFIED_PROJECT_KNOWLEDGE:
            if self.trust_basis is not TrustBasis.VERIFIED:
                raise ValueError("verified_project_knowledge requires verified trust basis")
            if self.provenance not in (ProvenanceKind.DERIVED, ProvenanceKind.SYSTEM_OBSERVED):
                raise ValueError(
                    "verified_project_knowledge requires derived or system_observed provenance"
                )
        if self.memory_type is KnowledgeMemoryType.RETRIEVED_KNOWLEDGE:
            if self.provenance is not ProvenanceKind.RETRIEVED:
                raise ValueError("retrieved_knowledge requires retrieved provenance")
            if self.trust_basis is not TrustBasis.RETRIEVED:
                raise ValueError("retrieved_knowledge requires retrieved trust basis")
        if self.memory_type is KnowledgeMemoryType.USER_PREFERENCE:
            if self.provenance is not ProvenanceKind.USER_ENTERED:
                raise ValueError("user_preference requires user_entered provenance")
            if self.trust_basis is not TrustBasis.DECLARED:
                raise ValueError("user_preference requires declared trust basis")
        if self.memory_type is KnowledgeMemoryType.USER_DECLARATION:
            if self.provenance is not ProvenanceKind.USER_ENTERED:
                raise ValueError("user_declaration requires user_entered provenance")
            if self.trust_basis is not TrustBasis.DECLARED:
                raise ValueError("user_declaration requires declared trust basis")
        if self.memory_type is KnowledgeMemoryType.PROJECT_HISTORY:
            if self.provenance not in (
                ProvenanceKind.USER_ENTERED,
                ProvenanceKind.SYSTEM_OBSERVED,
            ):
                raise ValueError(
                    "project_history requires user_entered or system_observed provenance"
                )
            if self.trust_basis not in (TrustBasis.DECLARED, TrustBasis.UNVERIFIED):
                raise ValueError("project_history requires declared or unverified trust basis")
        if self.memory_type is KnowledgeMemoryType.MODEL_GENERATED_CONTENT:
            if self.provenance is not ProvenanceKind.MODEL_GENERATED:
                raise ValueError("model_generated_content requires model_generated provenance")
            if self.trust_basis is not TrustBasis.UNVERIFIED:
                raise ValueError("model_generated_content must remain unverified")
        if self.memory_type is KnowledgeMemoryType.SYSTEM_OBSERVATION:
            if self.provenance is not ProvenanceKind.SYSTEM_OBSERVED:
                raise ValueError("system_observation requires system_observed provenance")
            if self.trust_basis is not TrustBasis.UNVERIFIED:
                raise ValueError("system_observation must remain unverified")
        for limitation in self.limitations:
            _require_identifier(limitation, "limitations")


@dataclass(frozen=True, slots=True)
class KnowledgeFilter(JsonContract):
    """Deterministic filter for knowledge/memory retrieval queries."""

    memory_types: list[KnowledgeMemoryType] = field(default_factory=list)
    scopes: list[MemoryScope] = field(default_factory=list)
    provenance_kinds: list[ProvenanceKind] = field(default_factory=list)
    project_id: str | None = None
    user_id: str | None = None
    created_after: str | None = None
    created_before: str | None = None
    trust_basis: list[TrustBasis] = field(default_factory=list)
    source_identity: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.memory_types, list) or any(
            not isinstance(item, KnowledgeMemoryType) for item in self.memory_types
        ):
            raise TypeError("memory_types must be a list of KnowledgeMemoryType")
        if not isinstance(self.scopes, list) or any(
            not isinstance(item, MemoryScope) for item in self.scopes
        ):
            raise TypeError("scopes must be a list of MemoryScope")
        if not isinstance(self.provenance_kinds, list) or any(
            not isinstance(item, ProvenanceKind) for item in self.provenance_kinds
        ):
            raise TypeError("provenance_kinds must be a list of ProvenanceKind")
        if not isinstance(self.trust_basis, list) or any(
            not isinstance(item, TrustBasis) for item in self.trust_basis
        ):
            raise TypeError("trust_basis must be a list of TrustBasis")
        for optional_id in ("project_id", "user_id", "source_identity"):
            value = getattr(self, optional_id)
            if value is not None:
                _require_identifier(value, optional_id)
        for timestamp_name in ("created_after", "created_before"):
            value = getattr(self, timestamp_name)
            if value is not None:
                _require_identifier(value, timestamp_name)


@dataclass(frozen=True, slots=True)
class KnowledgeQuery(JsonContract):
    """Structured knowledge retrieval query with explicit provider identity."""

    query_id: str
    provider_identity: str
    filters: KnowledgeFilter = field(default_factory=KnowledgeFilter)
    text: str | None = None
    ordering_policy: str = "created_at_ascending"

    def __post_init__(self) -> None:
        _require_identifier(self.query_id, "query_id")
        _require_identifier(self.provider_identity, "provider_identity")
        if not isinstance(self.filters, KnowledgeFilter):
            raise TypeError("filters must be a KnowledgeFilter")
        if self.text is not None:
            _require_identifier(self.text, "text")
        _require_identifier(self.ordering_policy, "ordering_policy")


@dataclass(frozen=True, slots=True)
class RetrievedKnowledgeItem(JsonContract):
    """One retrieved result with explicit score semantics.

    Retrieval score must not be treated as confidence or truth.
    """

    result_id: str
    query_id: str
    memory_item: MemoryItem
    rank: int
    retrieval_score: float | None = None
    score_semantics: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.result_id, "result_id")
        _require_identifier(self.query_id, "query_id")
        if not isinstance(self.memory_item, MemoryItem):
            raise TypeError("memory_item must be a MemoryItem")
        if type(self.rank) is not int or self.rank < 0:
            raise ValueError("rank must be a non-negative integer")
        if self.retrieval_score is not None:
            _require_finite_number(self.retrieval_score, "retrieval_score")
            if not 0.0 <= self.retrieval_score <= 1.0:
                raise ValueError("retrieval_score must be within [0, 1]")
            _require_identifier(self.score_semantics, "score_semantics")
        elif self.score_semantics is not None:
            raise ValueError("score_semantics requires a retrieval_score")


@dataclass(frozen=True, slots=True)
class KnowledgeRetrievalResult(JsonContract):
    """Deterministic retrieval result container."""

    query_id: str
    provider_identity: str
    results: list[RetrievedKnowledgeItem]
    retrieval_policy: str

    def __post_init__(self) -> None:
        _require_identifier(self.query_id, "query_id")
        _require_identifier(self.provider_identity, "provider_identity")
        _require_identifier(self.retrieval_policy, "retrieval_policy")
        if not isinstance(self.results, list):
            raise TypeError("results must be a list")
        for item in self.results:
            if not isinstance(item, RetrievedKnowledgeItem):
                raise TypeError("results must contain RetrievedKnowledgeItem values")

    @property
    def result_count(self) -> int:
        return len(self.results)


@dataclass(frozen=True, slots=True)
class UserPreferenceItem(JsonContract):
    """Explicit, reversible user preference.

    A preference must never be treated as scientific validation or objective
    quality.
    """

    preference_id: str
    category: str
    payload: MemoryPayload
    reversible: bool = True
    project_id: str | None = None
    user_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.preference_id, "preference_id")
        _require_identifier(self.category, "category")
        if not isinstance(self.payload, MemoryPayload):
            raise TypeError("payload must be a MemoryPayload")
        for optional_id in ("project_id", "user_id"):
            value = getattr(self, optional_id)
            if value is not None:
                _require_identifier(value, optional_id)
        for timestamp_name in ("created_at", "updated_at"):
            value = getattr(self, timestamp_name)
            if value is not None:
                _require_identifier(value, timestamp_name)


@dataclass(frozen=True, slots=True)
class ProjectHistoryEvent(JsonContract):
    """Append-oriented structured project history record."""

    event_id: str
    event_type: str
    project_id: str
    actor: HistoryActor
    description: str
    related_memory_ids: list[str] = field(default_factory=list)
    session_id: str | None = None
    timestamp: str | None = None
    method: MethodMetadata | None = None

    def __post_init__(self) -> None:
        for field_name in ("event_id", "event_type", "project_id", "description"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.actor, HistoryActor):
            raise TypeError("actor must be a HistoryActor")
        if not isinstance(self.related_memory_ids, list) or any(
            not isinstance(item, str) or not item.strip() for item in self.related_memory_ids
        ):
            raise TypeError("related_memory_ids must be a list of non-empty strings")
        if self.session_id is not None:
            _require_identifier(self.session_id, "session_id")
        if self.timestamp is not None:
            _require_identifier(self.timestamp, "timestamp")
        if self.method is not None and not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be a MethodMetadata")


@dataclass(frozen=True, slots=True)
class ReferenceMemoryItem(JsonContract):
    """Safe reference-history metadata.

    Historical similarity must not be treated as a universal quality score.
    """

    reference_identity: str
    source_path: str
    comparison_mode: str
    project_associations: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    annotations: list[MemoryPayload] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.reference_identity, "reference_identity")
        _require_identifier(self.source_path, "source_path")
        _require_identifier(self.comparison_mode, "comparison_mode")
        if not isinstance(self.project_associations, list) or any(
            not isinstance(item, str) or not item.strip() for item in self.project_associations
        ):
            raise TypeError("project_associations must be a list of non-empty strings")
        if not isinstance(self.tags, list) or any(
            not isinstance(item, str) or not item.strip() for item in self.tags
        ):
            raise TypeError("tags must be a list of non-empty strings")
        for annotation in self.annotations:
            if not isinstance(annotation, MemoryPayload):
                raise TypeError("annotations must contain MemoryPayload values")


@dataclass(frozen=True, slots=True)
class PersonalizationPolicy(JsonContract):
    """Bounded personalization policy.

    Personalization may influence presentation, defaults, and workflow focus.
    It must never modify scientific evidence, validation status, source-bound
    facts, criterion arithmetic, or contradictory evidence.

    `requires_explicit_user_consent` records whether the policy requires consent
    before personalization may be applied.  `consent_granted` records whether the
    user has actually granted that consent.  These are deliberately separate.
    """

    policy_id: str
    allowed_effects: list[PersonalizationEffect]
    requires_explicit_user_consent: bool = True
    consent_granted: bool = False
    prohibited_effects: list[str] = field(default_factory=lambda: ["scientific_evidence"])

    def __post_init__(self) -> None:
        _require_identifier(self.policy_id, "policy_id")
        if not isinstance(self.allowed_effects, list) or any(
            not isinstance(item, PersonalizationEffect) for item in self.allowed_effects
        ):
            raise TypeError("allowed_effects must be a list of PersonalizationEffect")
        if not isinstance(self.prohibited_effects, list) or any(
            not isinstance(item, str) or not item.strip() for item in self.prohibited_effects
        ):
            raise TypeError("prohibited_effects must be a list of non-empty strings")
        if "scientific_evidence" not in self.prohibited_effects:
            raise ValueError("prohibited_effects must include 'scientific_evidence'")
        if type(self.requires_explicit_user_consent) is not bool:
            raise TypeError("requires_explicit_user_consent must be a bool")
        if type(self.consent_granted) is not bool:
            raise TypeError("consent_granted must be a bool")


__all__ = [
    "KNOWLEDGE_FOUNDATION_METHOD_ID",
    "KNOWLEDGE_FOUNDATION_METHOD_VERSION",
    "KNOWLEDGE_FOUNDATION_SCHEMA_VERSION",
    "HistoryActor",
    "KnowledgeFilter",
    "KnowledgeMemoryType",
    "KnowledgeQuery",
    "KnowledgeRetrievalResult",
    "MemoryItem",
    "MemoryPayload",
    "MemoryScope",
    "PersonalizationEffect",
    "PersonalizationPolicy",
    "ProjectHistoryEvent",
    "ProvenanceKind",
    "ReferenceMemoryItem",
    "RetrievedKnowledgeItem",
    "TrustBasis",
    "UserPreferenceItem",
]
