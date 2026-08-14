from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from noisyne.orchestration.state import State


class Stage(ABC):

    @abstractmethod
    def run(
        self,
        state: State,
    ) -> State:
        pass