from __future__ import annotations

from collections.abc import Sequence

from .context import PerceptualContext
from .context_contracts import (
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
    ResolvedContextDimension,
    context_value_key,
)
from .translation_contracts import TranslationRiskPolicy


class PerceptualContextResolver:
    """Combine literal declarations without inference, normalization, or precedence."""

    def resolve(
        self,
        context: PerceptualContext | None = None,
        claims: Sequence[ContextClaim] = (),
        *,
        context_provenance: ContextProvenance = ContextProvenance.USER_DECLARED,
        context_source: str = "PerceptualContext supplied by caller",
        context_source_version: str | None = None,
    ) -> ContextResolutionResult:
        if context is not None and not isinstance(context, PerceptualContext):
            raise TypeError("context must be a PerceptualContext")
        if not isinstance(context_provenance, ContextProvenance):
            raise TypeError("context_provenance must be a ContextProvenance")
        supplied = list(claims)
        if any(not isinstance(claim, ContextClaim) for claim in supplied):
            raise TypeError("claims must contain ContextClaim values")
        identifiers = [claim.claim_id for claim in supplied]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("claim_id values must be unique")
        if context is not None:
            supplied = (
                self._context_claims(
                    context,
                    context_provenance,
                    context_source,
                    context_source_version,
                )
                + supplied
            )
            identifiers = [claim.claim_id for claim in supplied]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError("generated and supplied claim_id values must be unique")

        dimensions: list[ResolvedContextDimension] = []
        for dimension in ContextDimension:
            matching = [claim for claim in supplied if claim.context_dimension is dimension]
            if not matching:
                continue
            distinct = []
            keys = []
            for claim in matching:
                key = context_value_key(claim.value)
                if key not in keys:
                    keys.append(key)
                    distinct.append(claim.value)
            status = (
                ContextResolutionStatus.RESOLVED
                if len(distinct) == 1 or dimension is ContextDimension.LISTENER_PREFERENCE
                else ContextResolutionStatus.CONFLICT
            )
            dimensions.append(
                ResolvedContextDimension(
                    context_dimension=dimension,
                    status=status,
                    values=distinct,
                    claims=matching,
                )
            )

        status = ContextResolutionStatus.INSUFFICIENT_EVIDENCE
        if dimensions:
            status = (
                ContextResolutionStatus.CONFLICT
                if any(item.status is ContextResolutionStatus.CONFLICT for item in dimensions)
                else ContextResolutionStatus.RESOLVED
            )
        return ContextResolutionResult(status=status, dimensions=dimensions)

    @staticmethod
    def _context_claims(
        context: PerceptualContext,
        provenance: ContextProvenance,
        source: str,
        source_version: str | None,
    ) -> list[ContextClaim]:
        values = (
            (ContextDimension.GENRE, context.genre),
            (ContextDimension.STYLE, context.style),
            (ContextDimension.ARTISTIC_INTENT, context.artistic_intent),
            (ContextDimension.DELIVERY_TARGET, context.delivery_target),
            (ContextDimension.PLAYBACK_EXPECTATION, context.playback_expectation),
            (ContextDimension.LISTENING_LEVEL_QUALITATIVE, context.listening_level),
            (ContextDimension.LISTENING_LEVEL_DB_SPL, context.listening_level_db_spl),
            (ContextDimension.MONO_COMPATIBILITY, context.mono_compatibility),
            (ContextDimension.LISTENER_USE_CASE, context.listener_use_case),
        )
        claims = [
            ContextClaim(
                claim_id=f"perceptual_context.{dimension.value}",
                context_dimension=dimension,
                value=value,
                provenance=provenance,
                source=source,
                source_version=source_version,
                assumptions=list(context.assumptions),
                limitations=["Literal Sprint 1 declaration; no inference or engineering target."],
            )
            for dimension, value in values
            if value is not None
        ]
        claims.extend(
            ContextClaim(
                claim_id=f"perceptual_context.listener_preference.{index}",
                context_dimension=ContextDimension.LISTENER_PREFERENCE,
                value=value,
                provenance=provenance,
                source=source,
                source_version=source_version,
                assumptions=list(context.assumptions),
                limitations=["Literal preference declaration; no psychoacoustic inference."],
            )
            for index, value in enumerate(context.listener_preferences)
        )
        return claims


class ContextPolicySelector:
    """Select one supplied Sprint 7 policy through exact, versioned bindings."""

    def select(
        self,
        resolution: ContextResolutionResult,
        bindings: Sequence[ContextPolicyBinding],
        policies: Sequence[TranslationRiskPolicy],
    ) -> ContextPolicySelectionResult:
        if not isinstance(resolution, ContextResolutionResult):
            raise TypeError("resolution must be a ContextResolutionResult")
        binding_values = list(bindings)
        policy_values = list(policies)
        if any(not isinstance(item, ContextPolicyBinding) for item in binding_values):
            raise TypeError("bindings must contain ContextPolicyBinding values")
        if any(not isinstance(item, TranslationRiskPolicy) for item in policy_values):
            raise TypeError("policies must contain TranslationRiskPolicy values")
        binding_ids = [item.binding_id for item in binding_values]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("binding_id values must be unique")
        policy_ids = [(item.policy_id, item.version) for item in policy_values]
        if len(policy_ids) != len(set(policy_ids)):
            raise ValueError("policy identity and version pairs must be unique")

        if resolution.status is ContextResolutionStatus.CONFLICT:
            return ContextPolicySelectionResult(
                status=ContextPolicySelectionStatus.CONFLICT,
                resolution=resolution,
                reason="Context contains conflicting literal declarations; no precedence was supplied.",
            )

        matched = [
            binding
            for binding in binding_values
            if all(self._requirement_matches(resolution, item) for item in binding.requirements)
        ]
        matched_ids = [item.binding_id for item in matched]
        if not matched:
            return ContextPolicySelectionResult(
                status=ContextPolicySelectionStatus.NO_MATCH,
                resolution=resolution,
                reason="No exact context-policy binding matched.",
            )
        if len(matched) > 1:
            return ContextPolicySelectionResult(
                status=ContextPolicySelectionStatus.AMBIGUOUS,
                resolution=resolution,
                matched_binding_ids=matched_ids,
                reason="Multiple exact bindings matched; hidden ranking is prohibited.",
            )

        binding = matched[0]
        policy = next(
            (
                item
                for item in policy_values
                if item.policy_id == binding.policy_id and item.version == binding.policy_version
            ),
            None,
        )
        if policy is None:
            return ContextPolicySelectionResult(
                status=ContextPolicySelectionStatus.UNRESOLVED,
                resolution=resolution,
                matched_binding_ids=matched_ids,
                reason="Binding matched but its exact policy identity and version were not supplied.",
            )
        return ContextPolicySelectionResult(
            status=ContextPolicySelectionStatus.SELECTED,
            resolution=resolution,
            matched_binding_ids=matched_ids,
            selected_binding=binding,
            selected_policy=policy,
        )

    @staticmethod
    def _requirement_matches(
        resolution: ContextResolutionResult, requirement: ContextRequirement
    ) -> bool:
        dimension = resolution.dimension(requirement.context_dimension)
        if requirement.operator is ContextRequirementOperator.PRESENT:
            return dimension is not None and dimension.status is ContextResolutionStatus.RESOLVED
        if requirement.operator is ContextRequirementOperator.ABSENT:
            return dimension is None
        return (
            dimension is not None
            and dimension.status is ContextResolutionStatus.RESOLVED
            and context_value_key(requirement.expected_value)
            in [context_value_key(value) for value in dimension.values]
        )


__all__ = ["ContextPolicySelector", "PerceptualContextResolver"]
