from __future__ import annotations

from noisyne.infrastructure.container import Container


class Application:

    def __init__(
        self,
        container: Container,
    ):

        self._container = container

    @property
    def container(
        self,
    ) -> Container:

        return self._container