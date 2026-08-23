from __future__ import annotations

from phasenox.audio.context.models import AudioContext

from .models import ReasoningRules


class ReasoningGuard:

    def apply(
        self,
        context: AudioContext | None,
    ) -> ReasoningRules:

        rules = ReasoningRules()


        if context is None:

            return rules


        # -------------------------
        # Stem Rules
        # -------------------------

        if not context.is_full_mix:

            rules.allow_mastering = False

            rules.allow_mix_advice = False

            rules.allow_stem_advice = True

            rules.context_warning = (
                "This is an isolated audio element. "
                "Do not provide mastering or full mix recommendations."
            )


        # -------------------------
        # Full Mix Rules
        # -------------------------

        else:

            rules.allow_mastering = True

            rules.allow_mix_advice = True

            rules.allow_stem_advice = True


        return rules