from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .common import Confidence, ConfidenceBasis, MethodMetadata, ScalarValue, UnitBasis
from .mix_intelligence_contracts import MixIntelligenceResult, MixIssue
from .reasoning_contracts import (
    PERCEPTUAL_REASONING_METHOD_ID,
    PERCEPTUAL_REASONING_METHOD_VERSION,
    GroundingFact,
    GroundingFactType,
    PerceptualReasoningProvider,
    PerceptualReasoningResult,
    PerceptualReasoningState,
    PerceptualReasoningSummary,
    ProviderReasoningResponse,
    ProviderReasoningStatement,
    ReasoningError,
    ReasoningErrorCode,
    ReasoningEvidenceReference,
    ReasoningGroundingStatus,
    ReasoningProviderAvailability,
    ReasoningProviderIdentity,
    ReasoningProviderType,
    ReasoningRequest,
    ReasoningStatement,
    ReasoningStatementKind,
    grounding_fact_id,
    grounding_fact_set_digest,
    reasoning_request_id,
    reasoning_statement_id,
    render_reasoning_statement,
    source_result_digest,
)

_OBSERVATION_TEMPLATE = "observation.scalar"
_POLICY_TEMPLATE = "policy.declared_criterion_triggered"
_KIND_ORDER = {
    ReasoningStatementKind.OBSERVATION: 0,
    ReasoningStatementKind.POLICY_INTERPRETATION: 1,
    ReasoningStatementKind.LIMITATION: 2,
    ReasoningStatementKind.REVIEW_SUGGESTION: 3,
}


@dataclass(frozen=True, slots=True)
class _ValidationResult:
    statements: list[ReasoningStatement]
    rejected_count: int


class DeterministicReasoningProvider:
    """Select approved fact-backed templates without invoking a model."""

    @property
    def identity(self) -> ReasoningProviderIdentity:
        return ReasoningProviderIdentity(
            provider_id="noisyne.deterministic_reasoning",
            provider_type=ReasoningProviderType.DETERMINISTIC_TEMPLATE,
            provider_version="1.0.0",
            structured_output_supported=True,
            availability=ReasoningProviderAvailability.AVAILABLE,
        )

    def generate(self, request: ReasoningRequest) -> ProviderReasoningResponse:
        facts_by_issue: dict[str, list[GroundingFact]] = {
            issue_id: [] for issue_id in request.issue_ids
        }
        for fact in request.allowed_facts:
            if fact.issue_id is not None:
                facts_by_issue[fact.issue_id].append(fact)

        statements: list[ProviderReasoningStatement] = []
        for issue_id in request.issue_ids:
            facts = facts_by_issue[issue_id]
            if not facts:
                continue
            criterion_id = facts[0].criterion_id
            issue_type = _fact_by_type(facts, GroundingFactType.ISSUE_TYPE).value.value
            statements.extend(
                (
                    _candidate(
                        ReasoningStatementKind.OBSERVATION,
                        _OBSERVATION_TEMPLATE,
                        facts,
                        issue_id,
                        criterion_id,
                        (
                            GroundingFactType.EVIDENCE_DIMENSION,
                            GroundingFactType.EVIDENCE_VALUE,
                        ),
                    ),
                    _candidate(
                        ReasoningStatementKind.POLICY_INTERPRETATION,
                        _POLICY_TEMPLATE,
                        facts,
                        issue_id,
                        criterion_id,
                        (
                            GroundingFactType.EVIDENCE_VALUE,
                            GroundingFactType.THRESHOLD,
                            GroundingFactType.OPERATOR,
                            GroundingFactType.TRIGGERED,
                        ),
                    ),
                    _candidate(
                        ReasoningStatementKind.LIMITATION,
                        f"limitation.{issue_type}",
                        facts,
                        issue_id,
                        criterion_id,
                        (GroundingFactType.ISSUE_TYPE,),
                    ),
                    _candidate(
                        ReasoningStatementKind.REVIEW_SUGGESTION,
                        f"review.{issue_type}",
                        facts,
                        issue_id,
                        criterion_id,
                        (GroundingFactType.ISSUE_TYPE,),
                    ),
                )
            )
        return ProviderReasoningResponse(statements)


class GroundingValidator:
    """Validate provider selections and render canonical text from deterministic facts."""

    def validate(
        self,
        source: MixIntelligenceResult,
        provider: ReasoningProviderIdentity,
        facts: list[GroundingFact],
        response: ProviderReasoningResponse,
    ) -> _ValidationResult:
        fact_by_id = {item.fact_id: item for item in facts}
        issue_by_id = {item.issue_id: item for item in source.issues}
        issue_order = {item.issue_id: index for index, item in enumerate(source.issues)}
        accepted: list[ReasoningStatement] = []
        rejected = 0

        for candidate in response.statements:
            issue = issue_by_id.get(candidate.issue_id)
            selected = [fact_by_id.get(fact_id) for fact_id in candidate.fact_ids]
            if (
                candidate.text is not None
                or issue is None
                or candidate.criterion_id != issue.criterion.criterion_id
                or any(fact is None for fact in selected)
                or any(
                    fact.issue_id != candidate.issue_id
                    or fact.criterion_id != candidate.criterion_id
                    for fact in selected
                )
            ):
                rejected += 1
                continue

            source_facts = [fact for fact in selected if fact is not None]
            try:
                text = render_reasoning_statement(
                    candidate.kind,
                    candidate.template_id,
                    source_facts,
                )
            except (KeyError, TypeError, ValueError):
                rejected += 1
                continue
            references = [
                ReasoningEvidenceReference(
                    fact_id=fact.fact_id,
                    source_contract=fact.source_contract,
                    source_identity=fact.source_identity,
                    issue_id=fact.issue_id,
                    criterion_id=fact.criterion_id,
                )
                for fact in source_facts
            ]
            accepted.append(
                ReasoningStatement(
                    statement_id=reasoning_statement_id(
                        provider.provider_id,
                        issue.issue_id,
                        candidate.kind,
                        candidate.template_id,
                        candidate.fact_ids,
                    ),
                    kind=candidate.kind,
                    text=text,
                    grounding_status=ReasoningGroundingStatus.GROUNDED,
                    template_id=candidate.template_id,
                    issue_id=issue.issue_id,
                    criterion_id=issue.criterion.criterion_id,
                    evidence_references=references,
                    source_facts=source_facts,
                    assumptions=["The statement is rendered only from validated Sprint 10 facts."],
                    limitations=["Structural grounding does not establish perceptual certainty."],
                )
            )

        accepted.sort(
            key=lambda item: (
                issue_order[item.issue_id],
                _KIND_ORDER[item.kind],
                item.statement_id,
            )
        )
        return _ValidationResult(accepted, rejected)


class PerceptualReasoningEngine:
    """Produce validated explanations from Sprint 10 transport without DSP, RAG, or memory."""

    def explain(
        self,
        source: MixIntelligenceResult,
        provider: PerceptualReasoningProvider | None = None,
    ) -> PerceptualReasoningResult:
        if not isinstance(source, MixIntelligenceResult):
            raise TypeError("source must be a MixIntelligenceResult")
        selected_provider = provider or DeterministicReasoningProvider()
        identity = selected_provider.identity
        if not isinstance(identity, ReasoningProviderIdentity):
            raise TypeError("reasoning provider identity must be ReasoningProviderIdentity")
        source_digest = source_result_digest(source)
        facts = extract_grounding_facts(source, source_digest)
        fact_set_digest = grounding_fact_set_digest(facts)
        request = ReasoningRequest(
            request_id=reasoning_request_id(
                source_digest,
                [item.issue_id for item in source.issues],
            ),
            source_result_digest=source_digest,
            source_fact_set_digest=fact_set_digest,
            source_policy_id=source.policy.policy_id,
            source_policy_version=source.policy.version,
            issue_ids=[item.issue_id for item in source.issues],
            allowed_facts=facts,
        )
        if identity.availability is ReasoningProviderAvailability.UNAVAILABLE:
            return _failed_result(
                request,
                source,
                identity,
                PerceptualReasoningState.PROVIDER_UNAVAILABLE,
                ReasoningErrorCode.PROVIDER_UNAVAILABLE,
                "The selected reasoning provider is unavailable.",
            )
        if not identity.structured_output_supported:
            return _failed_result(
                request,
                source,
                identity,
                PerceptualReasoningState.INVALID_PROVIDER_RESPONSE,
                ReasoningErrorCode.INVALID_PROVIDER_RESPONSE,
                "The selected provider does not support the required structured output.",
            )
        try:
            response = selected_provider.generate(request)
        except TimeoutError:
            return _failed_result(
                request,
                source,
                identity,
                PerceptualReasoningState.TIMEOUT,
                ReasoningErrorCode.TIMEOUT,
                "The reasoning provider exceeded its configured timeout.",
            )
        except Exception:  # noqa: BLE001 - provider failures map to a safe public error
            return _failed_result(
                request,
                source,
                identity,
                PerceptualReasoningState.INVALID_PROVIDER_RESPONSE,
                ReasoningErrorCode.INVALID_PROVIDER_RESPONSE,
                "The reasoning provider failed without a valid structured response.",
            )
        if not isinstance(response, ProviderReasoningResponse):
            return _failed_result(
                request,
                source,
                identity,
                PerceptualReasoningState.INVALID_PROVIDER_RESPONSE,
                ReasoningErrorCode.INVALID_PROVIDER_RESPONSE,
                "The reasoning provider returned an invalid structured response.",
            )

        validation = GroundingValidator().validate(source, identity, facts, response)
        if validation.statements:
            return PerceptualReasoningResult(
                request_id=request.request_id,
                source_result_digest=request.source_result_digest,
                source_fact_set_digest=request.source_fact_set_digest,
                source_result=source,
                state=PerceptualReasoningState.COMPLETED,
                provider=identity,
                source_policy_id=request.source_policy_id,
                source_policy_version=request.source_policy_version,
                method=_method(),
                facts=facts,
                statements=validation.statements,
                summary=PerceptualReasoningSummary(
                    len(response.statements),
                    len(validation.statements),
                    validation.rejected_count,
                ),
                errors=[],
                confidence=_confidence(),
                assumptions=["Sprint 10 transport is the authoritative source of truth."],
                limitations=[
                    "Grounded explanation is not perceptual certainty or an audible-defect claim."
                ],
            )
        state = (
            PerceptualReasoningState.GROUNDING_REJECTED
            if response.statements
            else PerceptualReasoningState.NO_GROUNDED_STATEMENTS
        )
        code = (
            ReasoningErrorCode.GROUNDING_REJECTED
            if response.statements
            else ReasoningErrorCode.NO_GROUNDED_STATEMENTS
        )
        message = (
            "All provider statements failed deterministic grounding validation."
            if response.statements
            else "The provider returned no grounded statement selections."
        )
        return _failed_result(
            request,
            source,
            identity,
            state,
            code,
            message,
            provider_statement_count=len(response.statements),
            rejected_statement_count=validation.rejected_count,
        )


def extract_grounding_facts(
    source: MixIntelligenceResult,
    source_digest: str | None = None,
) -> list[GroundingFact]:
    if not isinstance(source, MixIntelligenceResult):
        raise TypeError("source must be a MixIntelligenceResult")
    bound_digest = source_digest or source_result_digest(source)
    if bound_digest != source_result_digest(source):
        raise ValueError("supplied source digest does not match the Sprint 10 result")
    policy_identity = f"{source.policy.policy_id}@{source.policy.version}"
    facts: list[GroundingFact] = [
        _global_fact(
            "fact.policy.identity",
            GroundingFactType.POLICY_IDENTITY,
            _named(policy_identity, "mix_policy_identity"),
            policy_identity,
            bound_digest,
        ),
        _global_fact(
            "fact.summary.evaluated_criterion_count",
            GroundingFactType.SUMMARY_COUNT,
            ScalarValue(
                source.summary.evaluated_criterion_count,
                UnitBasis.NAMED_SCALE,
                scale="evaluated_criterion_count",
            ),
            policy_identity,
            bound_digest,
        ),
        _global_fact(
            "fact.summary.triggered_issue_count",
            GroundingFactType.SUMMARY_COUNT,
            ScalarValue(
                source.summary.triggered_issue_count,
                UnitBasis.NAMED_SCALE,
                scale="triggered_issue_count",
            ),
            policy_identity,
            bound_digest,
        ),
        _global_fact(
            "fact.summary.not_triggered_count",
            GroundingFactType.SUMMARY_COUNT,
            ScalarValue(
                source.summary.not_triggered_count,
                UnitBasis.NAMED_SCALE,
                scale="not_triggered_count",
            ),
            policy_identity,
            bound_digest,
        ),
        _global_fact(
            "fact.summary.insufficient_evidence_count",
            GroundingFactType.SUMMARY_COUNT,
            ScalarValue(
                source.summary.insufficient_evidence_count,
                UnitBasis.NAMED_SCALE,
                scale="insufficient_evidence_count",
            ),
            policy_identity,
            bound_digest,
        ),
        _global_fact(
            "fact.summary.conflict_count",
            GroundingFactType.SUMMARY_COUNT,
            ScalarValue(
                source.summary.conflict_count,
                UnitBasis.NAMED_SCALE,
                scale="conflict_count",
            ),
            policy_identity,
            bound_digest,
        ),
        _global_fact(
            "fact.source.confidence_semantics",
            GroundingFactType.CONFIDENCE_SEMANTICS,
            _named("unscored_unknown", "confidence_semantics"),
            policy_identity,
            bound_digest,
        ),
    ]
    for issue in source.issues:
        values = [
            (
                GroundingFactType.ISSUE_TYPE,
                _named(issue.criterion.issue_type.value, "mix_issue_type"),
            ),
            (GroundingFactType.ISSUE_TITLE, _named(issue.title, "policy_issue_title")),
            (
                GroundingFactType.PRIORITY,
                _named(issue.criterion.priority.value, "mix_issue_priority"),
            ),
            (
                GroundingFactType.EVIDENCE_IDENTITY,
                _named(issue.evidence_identity, "evidence_identity"),
            ),
            (
                GroundingFactType.EVIDENCE_DIMENSION,
                _named(issue.criterion.evidence_dimension.value, "evidence_dimension"),
            ),
            (GroundingFactType.EVIDENCE_VALUE, issue.evidence_value),
            (
                GroundingFactType.CRITERION_IDENTITY,
                _named(
                    f"{issue.criterion.criterion_id}@{issue.criterion.version}",
                    "criterion_identity",
                ),
            ),
            (GroundingFactType.THRESHOLD, issue.criterion.threshold),
            (
                GroundingFactType.OPERATOR,
                _named(issue.criterion.operator.value, "criterion_operator"),
            ),
            (GroundingFactType.TRIGGERED, _named(True, "criterion_triggered")),
        ]
        if issue.exceedance is not None:
            values.append((GroundingFactType.EXCEEDANCE, issue.exceedance))
        for fact_type, value in values:
            facts.append(_fact(issue, fact_type, value, fact_type.value, bound_digest))
        for index, assumption in enumerate(issue.assumptions):
            facts.append(
                _fact(
                    issue,
                    GroundingFactType.ASSUMPTION,
                    _named(assumption, "policy_assumption"),
                    f"assumption.{index}.{_short_hash(assumption)}",
                    bound_digest,
                )
            )
        for index, limitation in enumerate(issue.limitations):
            facts.append(
                _fact(
                    issue,
                    GroundingFactType.LIMITATION,
                    _named(limitation, "policy_limitation"),
                    f"limitation.{index}.{_short_hash(limitation)}",
                    bound_digest,
                )
            )
    return facts


def _candidate(
    kind: ReasoningStatementKind,
    template_id: str,
    facts: list[GroundingFact],
    issue_id: str,
    criterion_id: str,
    fact_types: tuple[GroundingFactType, ...],
) -> ProviderReasoningStatement:
    return ProviderReasoningStatement(
        kind=kind,
        template_id=template_id,
        fact_ids=[_fact_by_type(facts, fact_type).fact_id for fact_type in fact_types],
        issue_id=issue_id,
        criterion_id=criterion_id,
    )


def _fact_by_type(facts: list[GroundingFact], fact_type: GroundingFactType) -> GroundingFact:
    matches = [item for item in facts if item.fact_type is fact_type]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {fact_type.value} fact")
    return matches[0]


def _fact(
    issue: MixIssue,
    fact_type: GroundingFactType,
    value: ScalarValue,
    suffix: str,
    source_digest: str,
) -> GroundingFact:
    semantic_id = f"{issue.issue_id}.{suffix}"
    return GroundingFact(
        fact_id=grounding_fact_id(
            semantic_id,
            source_digest,
            fact_type,
            value,
            "MixIssue",
            issue.evidence_identity,
            issue.issue_id,
            issue.criterion.criterion_id,
        ),
        semantic_id=semantic_id,
        source_result_digest=source_digest,
        fact_type=fact_type,
        value=value,
        source_contract="MixIssue",
        source_identity=issue.evidence_identity,
        issue_id=issue.issue_id,
        criterion_id=issue.criterion.criterion_id,
    )


def _global_fact(
    fact_id: str,
    fact_type: GroundingFactType,
    value: ScalarValue,
    source_identity: str,
    source_digest: str,
) -> GroundingFact:
    semantic_id = fact_id.removeprefix("fact.")
    return GroundingFact(
        fact_id=grounding_fact_id(
            semantic_id,
            source_digest,
            fact_type,
            value,
            "MixIntelligenceResult",
            source_identity,
            None,
            None,
        ),
        semantic_id=semantic_id,
        source_result_digest=source_digest,
        fact_type=fact_type,
        value=value,
        source_contract="MixIntelligenceResult",
        source_identity=source_identity,
    )


def _named(value: str | bool, scale: str) -> ScalarValue:
    return ScalarValue(value, UnitBasis.NAMED_SCALE, scale=scale)


def _failed_result(
    request: ReasoningRequest,
    source: MixIntelligenceResult,
    provider: ReasoningProviderIdentity,
    state: PerceptualReasoningState,
    code: ReasoningErrorCode,
    message: str,
    *,
    provider_statement_count: int = 0,
    rejected_statement_count: int = 0,
) -> PerceptualReasoningResult:
    return PerceptualReasoningResult(
        request_id=request.request_id,
        source_result_digest=request.source_result_digest,
        source_fact_set_digest=request.source_fact_set_digest,
        source_result=source,
        state=state,
        provider=provider,
        source_policy_id=request.source_policy_id,
        source_policy_version=request.source_policy_version,
        method=_method(),
        facts=request.allowed_facts,
        statements=[],
        summary=PerceptualReasoningSummary(
            provider_statement_count,
            0,
            rejected_statement_count,
        ),
        errors=[ReasoningError(code, message)],
        confidence=_confidence(),
        assumptions=["Sprint 10 transport is the authoritative source of truth."],
        limitations=["No unsupported provider statement is serialized as accepted reasoning."],
    )


def _method() -> MethodMetadata:
    return MethodMetadata(
        PERCEPTUAL_REASONING_METHOD_ID,
        PERCEPTUAL_REASONING_METHOD_VERSION,
        "Deterministic fact extraction, constrained template selection, and grounding validation.",
    )


def _confidence() -> Confidence:
    return Confidence(
        score=None,
        basis=ConfidenceBasis.UNKNOWN,
        reason=(
            "Grounding checks are deterministic; perceptual truth and model confidence are not "
            "quantified."
        ),
    )


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


__all__ = [
    "DeterministicReasoningProvider",
    "GroundingValidator",
    "PerceptualReasoningEngine",
    "extract_grounding_facts",
]
