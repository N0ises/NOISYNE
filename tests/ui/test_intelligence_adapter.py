from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from phasenox.ui.adapters.v2 import V2ApplicationAdapter
from phasenox.ui.contracts import AnalysisCommand


class FakeIntelligenceService:
    def analyze(self, request):
        issue = SimpleNamespace(
            title="Harsh upper mids",
            severity="medium",
            description="Upper-mid energy is elevated.",
            recommendation="Review the upper-mid balance.",
            confidence=0.81,
        )
        engineering = SimpleNamespace(
            strengths=["Stable stereo image"],
            issues=[issue],
            recommendations=[
                SimpleNamespace(
                    title="Reduce harshness",
                    reason="The upper mids are elevated.",
                    action="Evaluate a small upper-mid reduction.",
                    confidence=0.79,
                )
            ],
        )
        mix = SimpleNamespace(
            root_causes=[
                SimpleNamespace(
                    symptom="Harsh upper mids",
                    likely_causes=["Dense guitars", "Vocal presence boost"],
                    priority="high",
                    confidence=0.76,
                )
            ],
            prioritized_issues=[
                SimpleNamespace(
                    title="Upper-mid balance",
                    severity="medium",
                    priority_score=0.9,
                    user_action_order=1,
                    category="frequency",
                    description="Energy is elevated.",
                    recommendation="Review 2-4 kHz balance.",
                    confidence=0.82,
                )
            ],
            processing_chain=[
                SimpleNamespace(
                    order=1,
                    target="Upper mids",
                    plugin_type="equalizer",
                    suggestion="Consider a narrow reduction.",
                    estimated_impact="medium",
                    confidence=0.8,
                )
            ],
            explanations=["The recommendation follows the detected balance issue."],
        )
        parameter = SimpleNamespace(
            name="gain",
            value=-1.25,
            unit="dB",
            confidence=0.77,
            reason="Reduce upper-mid prominence.",
        )
        goal = SimpleNamespace(
            description="Reduce upper-mid prominence",
            target="Upper mids",
            root_cause="Dense guitars",
            action="Evaluate an equalizer adjustment.",
        )
        plugin = SimpleNamespace(
            steps=[
                SimpleNamespace(
                    order=1,
                    goal=goal,
                    plugin_category="equalizer",
                    plugin_type="parametric_eq",
                    parameter_recommendations=[parameter],
                    plugin_options=[SimpleNamespace(brand="Example", name="EQ")],
                    suggestion="Consider a parametric equalizer.",
                    estimated_impact="medium",
                    confidence=0.78,
                )
            ],
            explanations=[],
        )
        report = SimpleNamespace(
            audio_type="full_mix",
            score=84.0,
            ai_summary="Reasoning returned by the configured provider.",
            issues=[issue],
        )
        return SimpleNamespace(
            report=report,
            analysis=SimpleNamespace(),
            engineering=engineering,
            comparison=None,
            mix_intelligence=mix,
            plugin_intelligence=plugin,
            status="ok",
            warnings=[],
        )


def test_v2_adapter_maps_real_intelligence_without_executing_actions(product_metadata) -> None:
    adapter = V2ApplicationAdapter(
        metadata=product_metadata,
        service_factory=FakeIntelligenceService,
    )

    result = adapter.analyze(
        AnalysisCommand(
            Path("mix.wav"),
            include_reasoning=True,
            include_mix_intelligence=True,
            include_plugin_intelligence=True,
        )
    )

    intelligence = result.intelligence
    assert intelligence.engineering[1].finding == "Harsh upper mids"
    assert intelligence.engineering[2].proposed_action == ("Evaluate a small upper-mid reduction.")
    assert intelligence.mix[0].explanations == ("Dense guitars", "Vocal presence boost")
    assert intelligence.mix[1].recommendation == "Review 2-4 kHz balance."
    assert intelligence.plugin[0].proposed_action == "Evaluate an equalizer adjustment."
    assert intelligence.plugin[0].parameters[0].value == -1.25
    assert intelligence.plugin[0].parameters[0].unit == "dB"
    assert intelligence.reasoning == "Reasoning returned by the configured provider."


def test_reasoning_is_not_claimed_when_it_was_not_requested(product_metadata) -> None:
    adapter = V2ApplicationAdapter(
        metadata=product_metadata,
        service_factory=FakeIntelligenceService,
    )

    result = adapter.analyze(AnalysisCommand(Path("mix.wav")))

    assert result.intelligence.reasoning == ""


def test_user_intent_is_not_mislabeled_as_failed_reasoning(product_metadata) -> None:
    class FailedReasoningService(FakeIntelligenceService):
        def analyze(self, request):
            response = super().analyze(request)
            response.report.ai_summary = request.intent
            response.status = "degraded"
            response.warnings = ["Reasoning failed: provider unavailable"]
            return response

    adapter = V2ApplicationAdapter(
        metadata=product_metadata,
        service_factory=FailedReasoningService,
    )

    result = adapter.analyze(
        AnalysisCommand(
            Path("mix.wav"),
            intent="mastering review",
            include_reasoning=True,
        )
    )

    assert result.intelligence.reasoning == ""
    assert result.warnings == ("Reasoning failed: provider unavailable",)
