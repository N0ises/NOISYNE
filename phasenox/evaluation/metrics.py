from __future__ import annotations

from typing import Any

from phasenox.audio.mix.models import MixIntelligenceResult
from phasenox.audio.plugin.models import PluginIntelligenceResult
from phasenox.report.models import SoundBrainReport

from .models import EvaluationMetric


class AnalysisQualityMetrics:
    """Evaluate the structural quality of a SoundBrainReport."""

    def evaluate(self, report: SoundBrainReport) -> EvaluationMetric:
        score = 0.5
        details: dict[str, Any] = {
            "report_score": report.score,
            "report_confidence": report.confidence,
            "issue_count": len(report.issues),
            "recommendation_count": len(report.recommendations),
        }

        if 0.0 <= report.score <= 100.0:
            score += 0.1
        else:
            score -= 0.2

        if 0.0 <= report.confidence <= 1.0:
            score += 0.1
        else:
            score -= 0.1

        # Reward a calibrated score rather than degenerate 0/100 extremes.
        if report.issues:
            if 0 < report.score < 100:
                score += 0.1
        else:
            if report.score == 100.0:
                score += 0.1
            elif report.score == 0.0:
                score -= 0.3
            else:
                score -= 0.1

        if report.issues and all(issue.title and issue.description for issue in report.issues):
            score += 0.1

        if report.recommendations:
            score += 0.1

        severities = {issue.severity.lower() for issue in report.issues}
        details["severities"] = sorted(severities)
        if len(severities) <= 1 and report.issues:
            score -= 0.1

        score = max(0.0, min(1.0, score))
        return EvaluationMetric(
            name="analysis_quality",
            score=score,
            weight=0.25,
            details=details,
        )


class RecommendationConsistencyMetrics:
    """Check that recommendations are linked to detected issues."""

    def evaluate(self, report: SoundBrainReport) -> EvaluationMetric:
        if not report.recommendations:
            return EvaluationMetric(
                name="recommendation_consistency",
                score=0.5,
                weight=0.15,
                details={"reason": "no recommendations provided"},
            )

        issue_titles = {issue.title.lower() for issue in report.issues if issue.title}
        matched = 0
        for recommendation in report.recommendations:
            rec_lower = recommendation.lower()
            if any(title in rec_lower or rec_lower in title for title in issue_titles):
                matched += 1

        score = matched / len(report.recommendations)
        return EvaluationMetric(
            name="recommendation_consistency",
            score=score,
            weight=0.15,
            details={
                "matched": matched,
                "total": len(report.recommendations),
            },
        )


class ConfidenceEvaluationMetrics:
    """Evaluate whether confidence values are valid and varied."""

    def evaluate(
        self,
        report: SoundBrainReport,
        mix_intelligence: MixIntelligenceResult | None,
        plugin_intelligence: PluginIntelligenceResult | None,
    ) -> EvaluationMetric:
        values: list[float] = []
        values.extend(report.confidence_scores.values())
        values.extend(issue.confidence for issue in report.issues)

        if mix_intelligence is not None:
            values.extend(mix_intelligence.confidence_scores.values())
            values.extend(issue.confidence for issue in mix_intelligence.prioritized_issues)

        if plugin_intelligence is not None:
            values.extend(plugin_intelligence.confidence_scores.values())
            values.extend(step.confidence for step in plugin_intelligence.steps)

        details: dict[str, Any] = {
            "confidence_value_count": len(values),
            "unique_values": len(set(values)),
        }

        if not values:
            return EvaluationMetric(
                name="confidence_evaluation",
                score=0.5,
                weight=0.15,
                details=details,
            )

        if any(v < 0.0 or v > 1.0 for v in values):
            details["invalid_range"] = True
            return EvaluationMetric(
                name="confidence_evaluation",
                score=0.0,
                weight=0.15,
                details=details,
            )

        score = 0.5
        unique_values = len(set(values))
        if unique_values > 1:
            score += 0.25
        if all(v == 0.85 for v in values):
            score -= 0.25
        if min(values) > 0.0:
            score += 0.25

        score = max(0.0, min(1.0, score))
        details["min_confidence"] = min(values)
        details["max_confidence"] = max(values)
        return EvaluationMetric(
            name="confidence_evaluation",
            score=score,
            weight=0.15,
            details=details,
        )


class ReferenceMatchingMetrics:
    """Evaluate the quality of a reference comparison output."""

    def evaluate(self, comparison: Any | None) -> EvaluationMetric:
        if comparison is None:
            return EvaluationMetric(
                name="reference_matching",
                score=0.0,
                weight=0.15,
                applicable=False,
                details={"reason": "no comparison provided"},
            )

        details: dict[str, Any] = {
            "similarity": getattr(comparison, "similarity", None),
            "metric_count": len(getattr(comparison, "metrics", [])),
            "decision_count": len(getattr(comparison, "engineer_decisions", [])),
        }

        score = 0.0
        similarity = getattr(comparison, "similarity", None)
        if isinstance(similarity, (int, float)) and 0.0 <= similarity <= 100.0:
            score += 0.3

        metrics = getattr(comparison, "metrics", [])
        if metrics:
            passed = sum(1 for m in metrics if getattr(m, "passed", False))
            details["passed_metrics"] = passed
            if passed / len(metrics) > 0.5:
                score += 0.2

        decisions = getattr(comparison, "engineer_decisions", [])
        if decisions:
            types = {getattr(d, "decision_type", None) for d in decisions}
            if len(types) >= 2:
                score += 0.3
            details["decision_types"] = sorted(str(t) for t in types if t)

        score = max(0.0, min(1.0, score + 0.2))
        return EvaluationMetric(
            name="reference_matching",
            score=score,
            weight=0.15,
            details=details,
        )


class PluginRecommendationMetrics:
    """Evaluate the structural quality of plugin intelligence output."""

    def evaluate(self, plugin_intelligence: PluginIntelligenceResult | None) -> EvaluationMetric:
        if plugin_intelligence is None:
            return EvaluationMetric(
                name="plugin_recommendation",
                score=0.0,
                weight=0.15,
                applicable=False,
                details={"reason": "no plugin intelligence provided"},
            )

        steps = plugin_intelligence.steps
        details: dict[str, Any] = {
            "step_count": len(steps),
        }

        if not steps:
            return EvaluationMetric(
                name="plugin_recommendation",
                score=0.0,
                weight=0.15,
                details=details,
            )

        score = 0.0
        if len(steps) <= 6:
            score += 0.2
        if all(step.plugin_category and step.plugin_type for step in steps):
            score += 0.2

        valid_params = 0
        total_params = 0
        for step in steps:
            for param in step.parameter_recommendations:
                total_params += 1
                range_min = param.range_min
                range_max = param.range_max
                if (
                    range_min is not None
                    and range_max is not None
                    and range_min <= range_max
                    and range_min <= param.value <= range_max
                ):
                    valid_params += 1
        details["valid_parameters"] = valid_params
        details["total_parameters"] = total_params
        if total_params and valid_params / total_params > 0.8:
            score += 0.3

        if all(0.0 <= step.confidence <= 1.0 for step in steps):
            score += 0.3

        score = max(0.0, min(1.0, score))
        return EvaluationMetric(
            name="plugin_recommendation",
            score=score,
            weight=0.15,
            details=details,
        )


class KnowledgeResolutionMetrics:
    """Sanity-check the Knowledge layer through a resolver interface."""

    def evaluate(self, knowledge_resolver: Any | None) -> EvaluationMetric:
        if knowledge_resolver is None:
            return EvaluationMetric(
                name="knowledge_resolution",
                score=0.0,
                weight=0.15,
                applicable=False,
                details={"reason": "no knowledge resolver provided"},
            )

        details: dict[str, Any] = {}
        score = 0.0

        try:
            lufs = knowledge_resolver.target_lufs("streaming", None)
            details["streaming_target_lufs"] = lufs
            if -20.0 <= lufs <= -5.0:
                score += 0.25
        except (AttributeError, TypeError, ValueError, KeyError, IndexError) as exc:
            details["target_lufs_error"] = str(exc)

        try:
            order = knowledge_resolver.processing_order()
            details["processing_order"] = order
            if order:
                score += 0.25
        except (AttributeError, TypeError, ValueError, KeyError, IndexError) as exc:
            details["processing_order_error"] = str(exc)

        try:
            category = knowledge_resolver.plugin_category_for_target("frequency_balance")
            details["frequency_balance_category"] = category
            if category and category != "utility":
                score += 0.25
        except (AttributeError, TypeError, ValueError, KeyError, IndexError) as exc:
            details["plugin_category_error"] = str(exc)

        try:
            lufs_range = knowledge_resolver.mix_lufs_range()
            details["mix_lufs_range"] = lufs_range
            if lufs_range[0] < lufs_range[1]:
                score += 0.25
        except (AttributeError, TypeError, ValueError, KeyError, IndexError) as exc:
            details["lufs_range_error"] = str(exc)

        score = max(0.0, min(1.0, score))
        return EvaluationMetric(
            name="knowledge_resolution",
            score=score,
            weight=0.15,
            details=details,
        )
