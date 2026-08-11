from __future__ import annotations

import re

from brain.audio.context.models import AudioContext

from .models import PrioritizedIssue, ProcessingStep, RootCauseResult


class ProcessingChainRecommender:
    """
    Map prioritized issues to a non-destructive processing chain.

    Sprint 5 uses high-level plugin-type suggestions only. No models are loaded.
    """

    # Exact title mapping for the V1 rule-engine issue titles.
    _TITLE_TO_TARGET: dict[str, str] = {
        "loudness too quiet": "loudness",
        "loudness too loud": "gain_reduction",
        "dynamic range": "dynamics",
        "dynamics": "dynamics",
        "clipping": "clipping",
        "phase correlation": "stereo_image",
        "stereo width": "stereo_image",
    }

    def recommend(
        self,
        root_causes: RootCauseResult,
        prioritized_issues: list[PrioritizedIssue],
        context: AudioContext,
    ) -> list[ProcessingStep]:
        steps: list[ProcessingStep] = []
        seen_targets: set[str] = set()

        for issue in prioritized_issues:
            if len(steps) >= 6:
                break

            target = self._target(issue.title)
            if target in seen_targets:
                continue
            seen_targets.add(target)

            plugin_type = self._plugin_type(target)
            suggestion = self._suggestion(issue, root_causes)
            impact = self._impact(issue.category, issue.severity)

            steps.append(
                ProcessingStep(
                    order=issue.user_action_order,
                    target=target,
                    plugin_type=plugin_type,
                    suggestion=suggestion,
                    estimated_impact=impact,
                    confidence=issue.confidence,
                )
            )

        return steps

    def _target(self, title: str) -> str:
        normalized = title.lower().strip()
        if normalized in self._TITLE_TO_TARGET:
            return self._TITLE_TO_TARGET[normalized]

        # Whole-word fallback for legacy / descriptive titles.
        if self._whole_word(normalized, ("harsh", "sibilance", "brightness")):
            return "frequency_balance"

        if self._whole_word(normalized, ("loudness", "lufs")):
            return "loudness"

        if self._whole_word(normalized, ("dynamic", "dynamics", "compression", "punch", "flat")):
            return "dynamics"

        if self._whole_word(normalized, ("stereo", "width", "phase", "mono")):
            return "stereo_image"

        if self._whole_word(normalized, ("transient", "attack", "smack")):
            return "transients"

        return "tonal_balance"

    @staticmethod
    def _whole_word(text: str, words: tuple[str, ...]) -> bool:
        return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)

    def _plugin_type(self, target: str) -> str:
        mapping = {
            "frequency_balance": "EQ",
            "loudness": "Limiter",
            "gain_reduction": "Gain Utility",
            "dynamics": "Compressor",
            "clipping": "Gain Utility",
            "stereo_image": "Imager",
            "transients": "Transient Shaper",
            "tonal_balance": "EQ",
        }
        return mapping.get(target, "Utility")

    def _suggestion(
        self,
        issue: PrioritizedIssue,
        root_causes: RootCauseResult,
    ) -> str:
        for cause in root_causes.causes:
            if (
                issue.title.lower() in cause.symptom.lower()
                or cause.symptom.lower() in issue.title.lower()
            ):
                return (
                    f"Address {issue.title}: likely due to "
                    f"{cause.likely_causes[0]}. Recommended action: {issue.recommendation}"
                )

        return f"Address {issue.title}: {issue.recommendation}"

    def _impact(self, category: str, severity: str) -> str:
        if category == "fix first" or severity.lower() in ("critical", "high"):
            return "high"

        if category == "fine tune" or severity.lower() == "medium":
            return "medium"

        return "low"
