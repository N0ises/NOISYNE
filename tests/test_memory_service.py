from __future__ import annotations

from phasenox.knowledge import KnowledgeService
from phasenox.memory import MemoryService


def test_service_loads_default_bundle() -> None:
    service = MemoryService()
    service.resolver()  # trigger lazy load

    assert service.is_loaded()
    assert service.version() == "8.0.0"


def test_service_with_knowledge_service() -> None:
    knowledge = KnowledgeService()
    service = MemoryService(knowledge_service=knowledge)
    resolver = service.resolver()

    # Memory is empty, so loudness falls back to knowledge.
    assert resolver.target_lufs("streaming", None) == -14.0
    assert resolver.knowledge_resolver() is knowledge.resolver()


def test_service_resolver_is_cached() -> None:
    service = MemoryService()
    r1 = service.resolver()
    r2 = service.resolver()

    assert r1 is r2


def test_service_reload() -> None:
    service = MemoryService()
    original = service.resolver()
    service.reload()
    reloaded = service.resolver()

    assert reloaded.target_lufs(None, None) == original.target_lufs(None, None)
    assert service.version() == "8.0.0"


def test_service_bundle_accessor() -> None:
    service = MemoryService()
    bundle = service.bundle()

    assert bundle.version == "8.0.0"
    assert bundle.user_profile.user_id == "default"
