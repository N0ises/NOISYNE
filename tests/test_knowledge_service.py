from __future__ import annotations

from phasenox.knowledge import KnowledgeService


def test_service_loads_default_bundle() -> None:
    service = KnowledgeService()
    service.resolver()  # trigger lazy load

    assert service.is_loaded()
    assert service.version() == "7.0.0"

    resolver = service.resolver()
    assert resolver.mix_lufs_range() == (-14.5, -9.0)


def test_service_resolver_is_cached() -> None:
    service = KnowledgeService()
    r1 = service.resolver()
    r2 = service.resolver()

    assert r1 is r2


def test_service_reload() -> None:
    service = KnowledgeService()
    original = service.resolver()
    service.reload()
    reloaded = service.resolver()

    assert reloaded.mix_lufs_range() == original.mix_lufs_range()
    assert service.version() == "7.0.0"


def test_service_bundle_accessor() -> None:
    service = KnowledgeService()
    bundle = service.bundle()

    assert bundle.version == "7.0.0"
    assert "streaming" in bundle.platforms
