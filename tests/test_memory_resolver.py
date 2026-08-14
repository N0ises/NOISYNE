from __future__ import annotations

import pytest

from noisyne.knowledge import KnowledgeLoader, KnowledgeResolver
from noisyne.memory import MemoryLoader, MemoryResolver
from noisyne.memory.models import MemoryBundle, ProjectProfile, UserProfile


@pytest.fixture
def knowledge_resolver() -> KnowledgeResolver:
    bundle = KnowledgeLoader().load()
    return KnowledgeResolver(bundle)


@pytest.fixture
def empty_memory_resolver() -> MemoryResolver:
    bundle = MemoryLoader().load()
    return MemoryResolver(bundle)


def test_resolver_returns_memory_overrides_for_loudness(
    knowledge_resolver: KnowledgeResolver,
) -> None:
    memory = MemoryBundle(
        version="8.0.0",
        user_profile=UserProfile(preferred_loudness_by_platform={"streaming": -10.0}),
        project_profile=ProjectProfile(),
    )
    resolver = MemoryResolver(memory, knowledge_resolver)

    # Memory override wins.
    assert resolver.target_lufs("streaming", None) == -10.0
    # No memory for club, falls back to knowledge.
    assert resolver.target_lufs("club", None) == -8.0


def test_resolver_falls_back_to_knowledge_without_memory(
    knowledge_resolver: KnowledgeResolver,
) -> None:
    memory = MemoryLoader().load_from_dict(
        {
            "version": "8.0.0",
            "user_profile": {},
            "project_profile": {},
        }
    )
    resolver = MemoryResolver(memory, knowledge_resolver)

    assert resolver.target_lufs("streaming", None) == -14.0
    assert resolver.true_peak_max("streaming") == -1.0
    assert resolver.processing_order() == knowledge_resolver.processing_order()


def test_resolver_returns_safe_defaults_without_knowledge(
    empty_memory_resolver: MemoryResolver,
) -> None:
    assert empty_memory_resolver.target_lufs(None, None) == -14.0
    assert empty_memory_resolver.true_peak_max(None) == -1.0
    assert empty_memory_resolver.mix_lufs_range() == (-14.5, -9.0)
    assert empty_memory_resolver.dynamic_range_min(True) == 8.0


def test_resolver_returns_memory_processing_order(
    knowledge_resolver: KnowledgeResolver,
) -> None:
    memory = MemoryBundle(
        version="8.0.0",
        user_profile=UserProfile(preferred_processing_order=["limiter", "eq", "compressor"]),
        project_profile=ProjectProfile(),
    )
    resolver = MemoryResolver(memory, knowledge_resolver)

    assert resolver.processing_order() == ["limiter", "eq", "compressor"]


def test_resolver_returns_memory_preferences() -> None:
    memory = MemoryBundle(
        version="8.0.0",
        user_profile=UserProfile(
            preferred_plugin_brands=["FabFilter", "iZotope"],
            preferred_genres=["pop", "electronic"],
            preferred_export_targets=["wav", "flac"],
        ),
        project_profile=ProjectProfile(),
    )
    resolver = MemoryResolver(memory)

    assert resolver.preferred_plugin_brands() == ["FabFilter", "iZotope"]
    assert resolver.preferred_genres() == ["pop", "electronic"]
    assert resolver.preferred_export_targets() == ["wav", "flac"]


def test_resolver_returns_project_context() -> None:
    memory = MemoryBundle(
        version="8.0.0",
        user_profile=UserProfile(),
        project_profile=ProjectProfile(
            target_platform="streaming",
            genre="pop",
            delivery_targets=["streaming", "radio"],
            reference_paths=["ref.wav"],
        ),
    )
    resolver = MemoryResolver(memory)

    assert resolver.project_target_platform() == "streaming"
    assert resolver.project_genre() == "pop"
    assert resolver.project_delivery_targets() == ["streaming", "radio"]
    assert resolver.project_reference_paths() == ["ref.wav"]


def test_resolver_exposes_underlying_knowledge_resolver(
    knowledge_resolver: KnowledgeResolver,
) -> None:
    memory = MemoryLoader().load_from_dict(
        {
            "version": "8.0.0",
            "user_profile": {},
            "project_profile": {},
        }
    )
    resolver = MemoryResolver(memory, knowledge_resolver)

    assert resolver.knowledge_resolver() is knowledge_resolver
