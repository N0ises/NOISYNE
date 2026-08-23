from __future__ import annotations

from phasenox.infrastructure.application import Application
from phasenox.infrastructure.container import container

from phasenox.services.registration import (
    register_services,
)


def create_application() -> Application:

    register_services(
        container.services,
    )

    return Application(container)