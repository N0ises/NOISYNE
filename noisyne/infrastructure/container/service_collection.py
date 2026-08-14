from __future__ import annotations

from noisyne.infrastructure.container.lifetime import ServiceLifetime
from noisyne.infrastructure.container.service_descriptor import ServiceDescriptor


class ServiceCollection:

    def __init__(self):

        self._services: dict[type, ServiceDescriptor] = {}

    def add_singleton(
        self,
        service: type,
        implementation: type | None = None,
    ):

        self._services[service] = ServiceDescriptor(
            service_type=service,
            implementation_type=implementation or service,
            lifetime=ServiceLifetime.SINGLETON,
        )

    def add_transient(
        self,
        service: type,
        implementation: type | None = None,
    ):

        self._services[service] = ServiceDescriptor(
            service_type=service,
            implementation_type=implementation or service,
            lifetime=ServiceLifetime.TRANSIENT,
        )

    def get(
        self,
        service: type,
    ) -> ServiceDescriptor:

        return self._services[service]

    def contains(
        self,
        service: type,
    ) -> bool:

        return service in self._services