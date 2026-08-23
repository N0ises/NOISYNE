from __future__ import annotations

from phasenox.audio.plugin.models import (
    ParameterRecommendation,
    PluginIntelligenceResult,
    PluginIntelligenceStep,
)
from phasenox.evaluation.metrics import (
    AnalysisQualityMetrics,
    ConfidenceEvaluationMetrics,
    PluginRecommendationMetrics,
    RecommendationConsistencyMetrics,
)
from phasenox.report.models import ReportIssue, SoundBrainReport


def _report(
    score: float = 75.0,
    confidence: float = 0.85,
    issues: list[ReportIssue] | None = None,
    recommendations: list[str] | None = None,
) -> SoundBrainReport:
    return SoundBrainReport(
        audio_type="mix",
        source_type="full_track",
        instrument=None,
        is_full_mix=True,
        confidence=confidence,
        score=score,
        issues=issues or [],
        recommendations=recommendations or [],
    )


def test_analysis_quality_rewards_valid_report() -> None:
    report = _report(
        score=75.0,
        issues=[
            ReportIssue(
                title="Loudness",
                severity="medium",
                description="Too quiet.",
                recommendation="Add gain.",
                confidence=0.85,
            )
        ],
        recommendations=["Add gain."],
    )
    metric = AnalysisQualityMetrics().evaluate(report)

    assert metric.name == "analysis_quality"
    assert metric.score > 0.5


def test_analysis_quality_penalizes_degenerate_score() -> None:
    report = _report(score=0.0, issues=[])
    metric = AnalysisQualityMetrics().evaluate(report)

    assert metric.score < 0.5


def test_recommendation_consistency_matches_issues() -> None:
    report = _report(
        issues=[
            ReportIssue(
                title="Loudness",
                severity="medium",
                description="Too quiet.",
                recommendation="Add gain.",
                confidence=0.85,
            )
        ],
        recommendations=["Add gain to fix loudness."],
    )
    metric = RecommendationConsistencyMetrics().evaluate(report)

    assert metric.score == 1.0


def test_confidence_evaluation_penalizes_uniform_confidence() -> None:
    report = _report(
        issues=[
            ReportIssue(
                title="Loudness",
                severity="medium",
                description="Too quiet.",
                recommendation="Add gain.",
                confidence=0.85,
            ),
            ReportIssue(
                title="Dynamics",
                severity="medium",
                description="Flat.",
                recommendation="Reduce compression.",
                confidence=0.85,
            ),
        ]
    )
    metric = ConfidenceEvaluationMetrics().evaluate(
        report,
        mix_intelligence=None,
        plugin_intelligence=None,
    )

    assert metric.score < 1.0


def test_confidence_evaluation_rewards_varied_confidence() -> None:
    report = _report(
        issues=[
            ReportIssue(
                title="Loudness",
                severity="medium",
                description="Too quiet.",
                recommendation="Add gain.",
                confidence=0.95,
            ),
            ReportIssue(
                title="Dynamics",
                severity="medium",
                description="Flat.",
                recommendation="Reduce compression.",
                confidence=0.70,
            ),
        ]
    )
    metric = ConfidenceEvaluationMetrics().evaluate(
        report,
        mix_intelligence=None,
        plugin_intelligence=None,
    )

    assert metric.score > 0.5


def test_plugin_recommendation_evaluates_steps() -> None:
    step = PluginIntelligenceStep(
        order=1,
        goal=None,
        plugin_category="eq",
        plugin_type="EQ",
        parameter_recommendations=[
            ParameterRecommendation(
                name="frequency",
                value=3000.0,
                range_min=20.0,
                range_max=20000.0,
                confidence=0.85,
            )
        ],
        plugin_options=[],
        suggestion="Cut harsh highs.",
        estimated_impact="medium",
        confidence=0.85,
    )
    plugin = PluginIntelligenceResult(steps=[step])
    metric = PluginRecommendationMetrics().evaluate(plugin)

    assert metric.name == "plugin_recommendation"
    assert metric.score > 0.5


def test_plugin_recommendation_skipped_when_none() -> None:
    metric = PluginRecommendationMetrics().evaluate(None)

    assert not metric.applicable
    assert metric.score == 0.0
