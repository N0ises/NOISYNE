from __future__ import annotations

import re
from typing import ClassVar

from phasenox.audio.engineer.models import EngineerResult, Issue

from .models import PrioritizedIssue, RootCauseResult


class PriorityEngine:
    """
    Rank engineering issues by urgency and user action order.

    Sprint 5 uses deterministic heuristics. No models are loaded.
    """

    _SEVERITY_WEIGHT: ClassVar[dict[str, float]] = {
        "critical": 1.0,
        "high": 0.75,
        "medium": 0.5,
        "low": 0.25,
        "info": 0.1,
    }

    _CATEGORY_ORDER: ClassVar[dict[str, float]] = {
        "fix first": 1.0,
        "fine tune": 0.6,
        "optional": 0.3,
    }

    # Exact title mapping for the V1 rule-engine issue titles.
    _TITLE_TO_CATEGORY: dict[str, str] = {
        "loudness too quiet": "fix first",
        "loudness too loud": "fix first",
        "dynamic range": "fix first",
        "dynamics": "fix first",
        "clipping": "fix first",
        "phase correlation": "fine tune",
        "stereo width": "fine tune",
    }

    def prioritize(
        self,
        engineer: EngineerResult,
        root_causes: RootCauseResult,
    ) -> list[PrioritizedIssue]:
        causes_by_title = {cause.symptom.lower(): cause for cause in root_causes.causes}

        scored: list[tuple[float, PrioritizedIssue]] = []
        for issue in engineer.issues:
            category = self._category(issue)
            severity_weight = self._severity_weight(issue.severity)
            category_weight = self._CATEGORY_ORDER.get(category, 0.3)
            confidence = issue.confidence
            cause = causes_by_title.get(issue.title.lower())
            if cause is not None:
                confidence = (confidence + cause.confidence) / 2.0

            priority_score = severity_weight * category_weight * confidence

            prioritized = PrioritizedIssue(
                title=issue.title,
                severity=issue.severity,
                priority_score=priority_score,
                user_action_order=0,
                category=category,
                description=issue.description,
                recommendation=issue.recommendation,
                confidence=confidence,
            )
            scored.append((priority_score, prioritized))

        scored.sort(key=lambda item: item[0], reverse=True)

        result: list[PrioritizedIssue] = []
        for order, (score, issue) in enumerate(scored, start=1):
            issue.user_action_order = order
            result.append(issue)

        return result

    def _category(self, issue: Issue) -> str:
        title = issue.title.lower().strip()
        if title in self._TITLE_TO_CATEGORY:
            return self._TITLE_TO_CATEGORY[title]

        # Whole-word fallback to avoid substring collisions like "required" -> "eq".
        if self._whole_word(title, ("clip", "phase", "mono", "inversion")):
            return "fix first"

        if self._whole_word(title, ("loudness", "lufs", "limit", "dynamic", "dynamics")):
            return "fix first"

        if self._whole_word(title, ("frequency", "eq", "balance", "harsh", "sibilance")):
            return "fine tune"

        if self._whole_word(title, ("stereo", "width", "ambience")):
            return "fine tune"

        return "optional"

    @staticmethod
    def _whole_word(text: str, words: tuple[str, ...]) -> bool:
        return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)

    def _severity_weight(self, severity: str) -> float:
        return self._SEVERITY_WEIGHT.get(severity.lower(), 0.3)
