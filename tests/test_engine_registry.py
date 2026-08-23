from __future__ import annotations

from phasenox.runtime.engine_registry import EngineRegistry, registry


def test_engine_registry_register_and_get():
    r = EngineRegistry()

    def factory():
        return "engine"

    r.register("test_engine", factory)
    assert r.get("test_engine") is factory


def test_engine_registry_get_missing_returns_none():
    r = EngineRegistry()
    assert r.get("missing") is None


def test_engine_registry_list_sorted():
    r = EngineRegistry()
    r.register("beta", lambda: None)
    r.register("alpha", lambda: None)
    r.register("gamma", lambda: None)

    assert r.list() == ["alpha", "beta", "gamma"]


def test_engine_registry_contains():
    r = EngineRegistry()
    r.register("exists", lambda: None)

    assert "exists" in r
    assert "missing" not in r


def test_global_registry_has_v1_engines():
    assert registry.get("audio_review") is not None
    assert registry.get("reference_comparison") is not None
    assert registry.get("soundbrain") is not None

    names = registry.list()
    assert "audio_review" in names
    assert "reference_comparison" in names
    assert "soundbrain" in names
