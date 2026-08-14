from __future__ import annotations

from noisyne.audio.context.models import AudioContext
from noisyne.audio.mix.models import (
    MixIntelligenceResult,
    PrioritizedIssue,
    RootCause,
)

from .models import (
    PluginIntelligenceResult,
    PluginIntelligenceStep,
    ProcessingGoal,
)
from .parameter_generator import ParameterGenerator
from .selector import PluginSelector
from .taxonomy import (
    CATEGORY_CLIP,
    CATEGORY_COMPRESSOR,
    CATEGORY_EQ,
    CATEGORY_GAIN,
    CATEGORY_IMAGER,
    CATEGORY_LIMITER,
    CATEGORY_SATURATION,
    CATEGORY_TO_TYPE,
    CATEGORY_TRANSIENT_SHAPER,
    CATEGORY_UTILITY,
)


class PluginChainBuilder:
    """Transform Mix Intelligence results into a plugin-aware processing chain."""

    def __init__(
        self,
        parameter_generator: ParameterGenerator | None = None,
        selector: PluginSelector | None = None,
    ) -> None:
        if parameter_generator is None:
            self._parameter_generator = ParameterGenerator()
        else:
            self._parameter_generator = parameter_generator

        if selector is None:
            self._selector = PluginSelector()
        else:
            self._selector = selector

    def build(
        self,
        mix_result: MixIntelligenceResult,
        context: AudioContext,
    ) -> PluginIntelligenceResult:
        goals = self._build_goals(mix_result)
        steps: list[PluginIntelligenceStep] = []
        seen_keys: set[tuple[str, str]] = set()
        order = 1

        for goal in goals:
            category = self._category_for_goal(goal)
            # Deduplicate by (category, target) so distinct issues in the same
            # category are preserved, but identical duplicates are dropped.
            key = (category, goal.target)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            plugin_type = CATEGORY_TO_TYPE.get(category, "Utility")
            parameters = self._parameter_generator.generate(goal, category)
            options = self._selector.select(category, limit=3)

            steps.append(
                PluginIntelligenceStep(
                    order=order,
                    goal=goal,
                    plugin_category=category,
                    plugin_type=plugin_type,
                    parameter_recommendations=parameters,
                    plugin_options=options,
                    suggestion=f"Use a {plugin_type} to {goal.description}",
                    estimated_impact=self._impact(goal.confidence),
                    confidence=goal.confidence,
                )
            )
            order += 1

            if len(steps) >= 6:
                break

        return PluginIntelligenceResult(
            goals=goals,
            steps=steps,
            confidence_scores=mix_result.confidence_scores,
            explanations=[
                f"Step {step.order}: {step.plugin_type} for {step.goal.description}"
                for step in steps
            ],
        )

    def _build_goals(
        self,
        mix_result: MixIntelligenceResult,
    ) -> list[ProcessingGoal]:
        goals: list[ProcessingGoal] = []
        for issue in mix_result.prioritized_issues[:6]:
            cause = self._find_matching_cause(issue, mix_result.root_causes)
            goals.append(
                ProcessingGoal(
                    id=f"goal_{issue.user_action_order}",
                    description=issue.description or issue.title,
                    target=issue.title,
                    root_cause=cause.symptom if cause else None,
                    action=issue.recommendation,
                    confidence=issue.confidence,
                )
            )
        return goals

    def _find_matching_cause(
        self,
        issue: PrioritizedIssue,
        causes: list[RootCause],
    ) -> RootCause | None:
        title = issue.title.lower()
        for cause in causes:
            if title in cause.symptom.lower() or cause.symptom.lower() in title:
                return cause
        return None

    # Exact title mapping for V1 rule-engine issue titles.
    _TITLE_TO_CATEGORY: dict[str, str] = {
        "loudness too quiet": CATEGORY_LIMITER,
        "loudness too loud": CATEGORY_GAIN,
        "dynamic range": CATEGORY_COMPRESSOR,
        "dynamics": CATEGORY_COMPRESSOR,
        "clipping": CATEGORY_CLIP,
        "phase correlation": CATEGORY_IMAGER,
        "stereo width": CATEGORY_IMAGER,
        "harsh high end": CATEGORY_EQ,
        "sibilance": CATEGORY_EQ,
        "harsh highs": CATEGORY_EQ,
    }

    def _category_for_goal(self, goal: ProcessingGoal) -> str:
        target = goal.target.lower().strip()
        if target in self._TITLE_TO_CATEGORY:
            return self._TITLE_TO_CATEGORY[target]

        description = goal.description.lower().strip()
        text = f"{target} {description}"

        # Whole-word fallback to avoid substring collisions (e.g. "required" -> "eq").
        if self._whole_word(text, ("harsh", "sibilance", "brightness", "frequency", "eq")):
            return CATEGORY_EQ
        if self._whole_word(text, ("loudness", "lufs")):
            return CATEGORY_LIMITER
        if self._whole_word(text, ("dynamic", "dynamics", "compression", "punch", "flat")):
            return CATEGORY_COMPRESSOR
        if self._whole_word(text, ("stereo", "width", "phase", "mono")):
            return CATEGORY_IMAGER
        if self._whole_word(text, ("transient", "attack", "smack")):
            return CATEGORY_TRANSIENT_SHAPER
        if self._whole_word(text, ("warmth", "saturation", "harmonic")):
            return CATEGORY_SATURATION

        return CATEGORY_UTILITY

    @staticmethod
    def _whole_word(text: str, words: tuple[str, ...]) -> bool:
        import re

        return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)

    def _impact(self, confidence: float) -> str:
        if confidence >= 0.85:
            return "high"
        if confidence >= 0.65:
            return "medium"
        return "low"
