from __future__ import annotations

from phasenox.audio.plugin.models import (
    ParameterRecommendation,
    PluginIntelligenceResult,
    PluginIntelligenceStep,
    PluginMatch,
    ProcessingGoal,
)
from phasenox.audio.plugin.validator import PluginIntelligenceValidator


def _make_step(value: float, category: str = "eq") -> PluginIntelligenceStep:
    goal = ProcessingGoal(
        id="g1",
        description="test",
        target="test",
        root_cause=None,
        action="test",
        confidence=0.85,
    )
    return PluginIntelligenceStep(
        order=1,
        goal=goal,
        plugin_category=category,
        plugin_type="EQ",
        parameter_recommendations=[
            ParameterRecommendation(
                name="gain",
                value=value,
                unit="dB",
                range_min=-24.0,
                range_max=24.0,
                confidence=0.8,
                reason="test",
            )
        ],
        plugin_options=[PluginMatch("A", "X", category=category)],
        suggestion="test",
        estimated_impact="medium",
        confidence=0.85,
    )


def test_validator_clamps_out_of_range_parameter():
    step = _make_step(0.0)
    step.parameter_recommendations[0].value = 50.0

    result = PluginIntelligenceValidator().validate(PluginIntelligenceResult(steps=[step]))

    assert result.steps[0].parameter_recommendations[0].value == 24.0


def test_validator_deduplicates_categories():
    step1 = _make_step(0.0)
    step2 = _make_step(0.0)
    step2.order = 2

    result = PluginIntelligenceValidator().validate(PluginIntelligenceResult(steps=[step1, step2]))

    assert len(result.steps) == 1


def test_validator_removes_mismatched_plugin_options():
    step = _make_step(0.0, category="eq")
    step.plugin_options = [
        PluginMatch("A", "X", category="eq"),
        PluginMatch("B", "Y", category="compressor"),
    ]

    result = PluginIntelligenceValidator().validate(PluginIntelligenceResult(steps=[step]))

    assert len(result.steps[0].plugin_options) == 1
    assert result.steps[0].plugin_options[0].category == "eq"


def test_validator_keeps_in_range_parameter():
    step = _make_step(0.0)
    step.parameter_recommendations[0].value = -5.0

    result = PluginIntelligenceValidator().validate(PluginIntelligenceResult(steps=[step]))

    assert result.steps[0].parameter_recommendations[0].value == -5.0
