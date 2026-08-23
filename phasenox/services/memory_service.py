from __future__ import annotations

from phasenox.memory.history import History


class MemoryService:
    """
    Public API for conversation memory.

    Pipeline stages should never access memory modules directly.
    Always use MemoryService.
    """

    def __init__(self):

        self.history = History()

    def add(
        self,
        role: str,
        content: str,
    ) -> None:

        self.history.add(
            role=role,
            content=content,
        )

    def get(self):

        return self.history.get()

    def clear(self):

        self.history.clear()