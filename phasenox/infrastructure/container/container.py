from __future__ import annotations

from phasenox.infrastructure.container.lifetime import ServiceLifetime
from phasenox.infrastructure.container.service_collection import ServiceCollection


class Container:

    def __init__(self):

        self._services = ServiceCollection()

    @property
    def services(self) -> ServiceCollection:

        return self._services

    def resolve(
        self,
        service: type,
    ):

        descriptor = self._services.get(service)

        if (
            descriptor.lifetime
            == ServiceLifetime.SINGLETON
        ):

            if descriptor.instance is None:

                descriptor.instance = (
                    descriptor.implementation_type()
                )

            return descriptor.instance

        return descriptor.implementation_type()


container = Container()