from phasenox.agents.base_agent import BaseAgent


class AudioAgent(BaseAgent):
    """
    Base class for audio-related agents.
    """

    def __init__(self):

        super().__init__("Audio Agent")

    def run(self, *args, **kwargs):

        raise NotImplementedError(
            "AudioAgent has not been implemented yet."
        )