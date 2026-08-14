from __future__ import annotations

from .request import BrainRequest
from .response import BrainResponse


class BrainRouter:
    """
    High-level AI router.

    This class will become the single entry point
    for all AI capabilities in SoundBrain.
    """

    def route(
        self,
        request: BrainRequest,
    ) -> BrainResponse:

        raise NotImplementedError(
            "Routing is not connected yet."
        )