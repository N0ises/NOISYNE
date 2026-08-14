from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Base interface for every SoundBrain agent.
    """

    def __init__(self, name: str):

        self.name = name

    @abstractmethod
    def run(self, *args, **kwargs):
        """
        Execute the agent.
        """
        pass