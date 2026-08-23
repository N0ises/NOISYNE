from __future__ import annotations

from phasenox.infrastructure.container.container import (
    Container,
    container,
)

from phasenox.infrastructure.container.service_collection import (
    ServiceCollection,
)

from phasenox.infrastructure.container.service_descriptor import (
    ServiceDescriptor,
)

from phasenox.infrastructure.container.lifetime import (
    ServiceLifetime,
)

__all__ = [
    "Container",
    "container",
    "ServiceCollection",
    "ServiceDescriptor",
    "ServiceLifetime",
]