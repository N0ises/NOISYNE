from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Callable

from phasenox.infrastructure.container.lifetime import ServiceLifetime


@dataclass(slots=True)
class ServiceDescriptor:

    service_type: type

    implementation_type: type | None = None

    factory: Callable[..., Any] | None = None

    instance: Any | None = None

    lifetime: ServiceLifetime = ServiceLifetime.TRANSIENT