from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class Provider(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique provider name.
        """

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize provider resources.
        """