from __future__ import annotations

from noisyne.memory import MemoryLoader
from noisyne.memory.models import MemoryBundle


def test_loader_loads_default_bundle() -> None:
    loader = MemoryLoader()
    bundle = loader.load()

    assert isinstance(bundle, MemoryBundle)
    assert bundle.version == "8.0.0"
    assert bundle.user_profile.user_id == "default"
    assert bundle.project_profile.project_id == "default"


def test_loader_loads_from_dict() -> None:
    loader = MemoryLoader()
    data = {
        "version": "8.1.0",
        "user_profile": {
            "user_id": "user-1",
            "preferred_loudness_by_platform": {"streaming": -12.0},
            "preferred_plugin_brands": ["FabFilter"],
            "preferred_genres": ["pop"],
            "preferred_processing_order": ["eq", "compressor"],
            "preferred_export_targets": ["wav", "mp3"],
        },
        "project_profile": {
            "project_id": "project-1",
            "target_platform": "streaming",
            "genre": "pop",
            "delivery_targets": ["streaming"],
        },
    }

    bundle = loader.load_from_dict(data)

    assert bundle.version == "8.1.0"
    assert bundle.user_profile.user_id == "user-1"
    assert bundle.user_profile.preferred_loudness_by_platform["streaming"] == -12.0
    assert bundle.project_profile.project_id == "project-1"


def test_loader_uses_defaults_for_missing_sections() -> None:
    loader = MemoryLoader()
    data = {
        "version": "8.0.0",
        "user_profile": {},
        "project_profile": {},
    }

    bundle = loader.load_from_dict(data)

    assert bundle.user_profile.user_id == "default"
    assert bundle.user_profile.preferred_plugin_brands == []
    assert bundle.project_profile.target_platform is None
