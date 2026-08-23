from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Base interface for every PHASENOX agent.
    """

    def __init__(self, name: str):

        self.name = name

    @abstractmethod
    def run(self, *args, **kwargs):
        """
        Execute the agent.
        """
