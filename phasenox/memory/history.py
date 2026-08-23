from __future__ import annotations

from collections import deque


MAX_HISTORY = 10


class History:

    def __init__(self):

        self.messages = deque(maxlen=MAX_HISTORY)

    def add(
        self,
        role: str,
        content: str,
    ) -> None:

        self.messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    def get(self):

        return list(self.messages)

    def clear(self):

        self.messages.clear()