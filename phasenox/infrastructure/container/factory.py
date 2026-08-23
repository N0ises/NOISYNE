from __future__ import annotations

from phasenox.infrastructure.container.container import container


def resolve(
    service: type,
):

    return container.resolve(service)