from __future__ import annotations

from noisyne.infrastructure.container.container import container


def resolve(
    service: type,
):

    return container.resolve(service)