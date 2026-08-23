from __future__ import annotations

from phasenox.orchestration.models import Plan
from phasenox.orchestration.state import State


class Planner:

    def plan(self, state: State) -> State:

        q = state.question.lower()

        plan = Plan()

        # ----------------------------------------------------
        # Always enabled
        # ----------------------------------------------------

        plan.use_memory = True
        plan.use_rag = True

        # ----------------------------------------------------
        # Audio
        # ----------------------------------------------------

        audio_keywords = [
            "audio",
            "voice",
            "vocal",
            "vocals",
            "mix",
            "mixing",
            "master",
            "mastering",
            "stem",
            "wav",
            "mp3",
        ]

        if any(word in q for word in audio_keywords):
            plan.use_audio = True

        # ----------------------------------------------------
        # Vision
        # ----------------------------------------------------

        vision_keywords = [
            "image",
            "photo",
            "picture",
            "screen",
            "screenshot",
            "compressor",
            "plugin",
            "eq",
            "ui",
        ]

        if any(word in q for word in vision_keywords):
            plan.use_vision = True

        # ----------------------------------------------------
        # Tool Calling
        # ----------------------------------------------------

        tool_keywords = [
            "bpm",
            "pitch",
            "key",
            "lufs",
            "spectrum",
        ]

        if any(word in q for word in tool_keywords):
            plan.use_tools = True

        # ----------------------------------------------------
        # Recommendation
        # ----------------------------------------------------

        recommendation_keywords = [
            "recommend",
            "suggest",
            "best",
        ]

        if any(word in q for word in recommendation_keywords):
            plan.use_recommendation = True

        # ----------------------------------------------------
        # Report
        # ----------------------------------------------------

        report_keywords = [
            "report",
            "analysis",
            "analyze",
        ]

        if any(word in q for word in report_keywords):
            plan.use_report = True

        # ----------------------------------------------------
        # Reasoning
        # ----------------------------------------------------

        reasoning_keywords = [
            "why",
            "difference",
            "compare",
            "versus",
            "vs",
        ]

        if any(word in q for word in reasoning_keywords):
            plan.use_reasoning = True

        state.plan = plan

        return state