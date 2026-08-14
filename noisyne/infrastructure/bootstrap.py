from __future__ import annotations

from noisyne.infrastructure.application import Application
from noisyne.infrastructure.container import container

from noisyne.services.registration import (
    register_services,
)


def create_application() -> Application:

    register_services(
        container.services,
    )

    return Application(container)