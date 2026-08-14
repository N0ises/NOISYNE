from __future__ import annotations

from dataclasses import replace

from .models import (
    ParameterRecommendation,
    PluginIntelligenceResult,
    PluginIntelligenceStep,
    PluginMatch,
)
from .taxonomy import PARAMETER_RANGES


class PluginIntelligenceValidator:
    """Validate safety and consistency of plugin recommendations."""

    def validate(
        self,
        result: PluginIntelligenceResult,
    ) -> PluginIntelligenceResult:
        seen_categories: set[str] = set()
        valid_steps: list[PluginIntelligenceStep] = []

        for step in result.steps:
            if step.plugin_category in seen_categories:
                continue
            seen_categories.add(step.plugin_category)

            parameters = [
                self._clamp(parameter, step.plugin_category)
                for parameter in step.parameter_recommendations
            ]
            options = [
                option for option in step.plugin_options if option.category == step.plugin_category
            ]

            valid_steps.append(
                replace(
                    step,
                    parameter_recommendations=parameters,
                    plugin_options=options,
                )
            )

        return replace(
            result,
            steps=valid_steps,
        )

    def _clamp(
        self,
        parameter: ParameterRecommendation,
        category: str,
    ) -> ParameterRecommendation:
        ranges = PARAMETER_RANGES.get(category, {})
        if parameter.name not in ranges:
            return parameter

        min_value, max_value = ranges[parameter.name]
        value = parameter.value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            clamped = max(min_value, min(max_value, float(value)))
            return replace(parameter, value=clamped)

        return parameter

    def _option_matches_category(
        self,
        option: PluginMatch,
        category: str,
    ) -> bool:
        return option.category == category
