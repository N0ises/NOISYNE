from __future__ import annotations

from phasenox.infrastructure.container import ServiceCollection

from phasenox.services import (
    LLMService,
    MemoryService,
    PromptService,
    RAGService,
    ReasoningService,
)


def register_services(
    services: ServiceCollection,
) -> None:

    if not services.contains(LLMService):
        services.add_singleton(LLMService)

    if not services.contains(RAGService):
        services.add_singleton(RAGService)

    if not services.contains(MemoryService):
        services.add_singleton(MemoryService)

    if not services.contains(PromptService):
        services.add_singleton(PromptService)

    if not services.contains(ReasoningService):
        services.add_singleton(ReasoningService)