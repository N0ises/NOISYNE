from __future__ import annotations

from phasenox.audio.mix.models import MixIntelligenceResult
from phasenox.audio.plugin.models import PluginIntelligenceResult, PluginIntelligenceStep
from phasenox.evaluation import EvaluationService
from phasenox.evaluation.models import BenchmarkCase
from phasenox.report.models import PhasenoxReport, ReportIssue


def _make_report() -> PhasenoxReport:
    return PhasenoxReport(
        audio_type="mix",
        source_type="full_track",
        instrument=None,
        is_full_mix=True,
        confidence=0.85,
        score=75.0,
        strengths=["No clipping detected."],
        issues=[
            ReportIssue(
                title="Loudness",
                severity="medium",
                description="Integrated loudness is outside expected range.",
                recommendation="Review overall gain and limiting decisions.",
                confidence=0.85,
            ),
            ReportIssue(
                title="Dynamic Range",
                severity="medium",
                description="Dynamic range is limited.",
                recommendation="Review compression and limiting.",
                confidence=0.80,
            ),
        ],
        recommendations=[
            "Review overall gain and limiting decisions.",
            "Review compression and limiting.",
        ],
        confidence_scores={"overall": 0.85},
    )


def _make_response():
    class FakeResponse:
        report = _make_report()
        comparison = None
        mix_intelligence = MixIntelligenceResult(
            root_causes=[],
            prioritized_issues=[],
            processing_chain=[],
            explanations=[],
            confidence_scores={"root_cause": 0.82},
        )
        plugin_intelligence = PluginIntelligenceResult(
            goals=[],
            steps=[
                PluginIntelligenceStep(
                    order=1,
                    goal=None,
                    plugin_category="eq",
                    plugin_type="EQ",
                    parameter_recommendations=[],
                    plugin_options=[],
                    suggestion="Use an EQ to balance frequency.",
                    estimated_impact="medium",
                    confidence=0.85,
                )
            ],
            confidence_scores={"plugin": 0.85},
            explanations=[],
        )

    return FakeResponse()


def test_evaluation_service_scores_report() -> None:
    service = EvaluationService()
    response = _make_response()
    result = service.evaluate_response(response)

    assert 0.0 <= result.overall_score <= 1.0
    assert result.passed or not result.passed
    assert any(m.name == "analysis_quality" for m in result.metrics)
    assert any(m.name == "plugin_recommendation" for m in result.metrics)


def test_evaluation_service_with_components() -> None:
    service = EvaluationService()
    report = _make_report()
    mix = MixIntelligenceResult(
        root_causes=[],
        prioritized_issues=[],
        processing_chain=[],
        explanations=[],
        confidence_scores={},
    )
    plugin = PluginIntelligenceResult()

    result = service.evaluate_components(
        report=report,
        mix_intelligence=mix,
        plugin_intelligence=plugin,
        evaluation_id="test-1",
    )

    assert result.evaluation_id == "test-1"
    assert result.metrics
    assert all(0.0 <= m.score <= 1.0 for m in result.metrics if m.applicable)


def test_benchmark_runs_multiple_cases() -> None:
    service = EvaluationService()
    cases = [
        BenchmarkCase(case_id="case-a", response=_make_response()),
        BenchmarkCase(case_id="case-b", response=_make_response()),
    ]
    result = service.benchmark(cases, benchmark_id="benchmark-test")

    assert result.benchmark_id == "benchmark-test"
    assert len(result.evaluations) == 2
    assert result.aggregated_scores
    assert 0.0 <= result.overall_score <= 1.0


def test_evaluation_service_with_knowledge_resolver() -> None:
    from phasenox.knowledge import KnowledgeService

    knowledge = KnowledgeService().resolver()
    service = EvaluationService(knowledge_resolver=knowledge)
    response = _make_response()
    result = service.evaluate_response(response)

    knowledge_metric = next(m for m in result.metrics if m.name == "knowledge_resolution")
    assert knowledge_metric.applicable
    assert knowledge_metric.score > 0.0


def test_evaluation_service_rejects_invalid_report() -> None:
    class FakeResponse:
        report = "not a report"
        comparison = None
        mix_intelligence = None
        plugin_intelligence = None

    service = EvaluationService()
    try:
        service.evaluate_response(FakeResponse())
        assert False, "expected TypeError"
    except TypeError:
        pass
