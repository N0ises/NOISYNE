from __future__ import annotations

import pytest

from noisyne.knowledge import KnowledgeLoader, KnowledgeResolver


@pytest.fixture
def resolver() -> KnowledgeResolver:
    bundle = KnowledgeLoader().load()
    return KnowledgeResolver(bundle)


def test_resolver_returns_engineering_thresholds(resolver: KnowledgeResolver) -> None:
    assert resolver.mix_lufs_range() == (-14.5, -9.0)
    assert resolver.dynamic_range_min(is_full_mix=True) == 8.0
    assert resolver.dynamic_range_min(is_full_mix=False) == 8.0
    assert resolver.peak_max(is_full_mix=True) == 1.0
    assert resolver.phase_high_threshold() == 0.7
    assert resolver.phase_low_threshold() == 0.3
    assert resolver.stereo_width_min() == 0.10


def test_resolver_returns_weights(resolver: KnowledgeResolver) -> None:
    assert resolver.severity_weight("high") == 0.75
    assert resolver.severity_weight("unknown") == 0.3
    assert resolver.category_weight("fix first") == 1.0
    assert resolver.category_weight("unknown") == 0.3


def test_resolver_returns_genre_profiles(resolver: KnowledgeResolver) -> None:
    pop = resolver.genre_profile("pop")
    assert pop is not None
    assert pop.name == "pop"
    assert "streaming" in pop.target_loudness_by_platform


def test_resolver_returns_none_for_unknown_genre(resolver: KnowledgeResolver) -> None:
    assert resolver.genre_profile("unknown") is None
    assert resolver.genre_profile(None) is None


def test_resolver_returns_platform_profiles(resolver: KnowledgeResolver) -> None:
    streaming = resolver.platform_profile("streaming")
    assert streaming is not None
    assert streaming.target_lufs == -14.0
    assert streaming.true_peak_max == -1.0


def test_resolver_target_lufs_priority(resolver: KnowledgeResolver) -> None:
    # Genre-specific platform target
    assert resolver.target_lufs("streaming", "pop") == -9.0
    # Platform default when no genre
    assert resolver.target_lufs("streaming", None) == -14.0
    # Fallback when nothing is provided
    assert resolver.target_lufs(None, None) == -14.0


def test_resolver_plugin_mappings(resolver: KnowledgeResolver) -> None:
    assert resolver.plugin_category_for_target("frequency_balance") == "eq"
    assert resolver.plugin_category_for_target("unknown_target") == "utility"
    assert resolver.plugin_type_for_category("compressor") == "Compressor"
    assert resolver.plugin_type_for_category("unknown") == "Utility"


def test_resolver_parameter_spec(resolver: KnowledgeResolver) -> None:
    spec = resolver.parameter_spec("eq", "frequency")
    assert spec.range_min == 20.0
    assert spec.range_max == 20000.0
    assert spec.default == 3000.0


def test_resolver_parameter_defaults(resolver: KnowledgeResolver) -> None:
    defaults = resolver.parameter_defaults("compressor")
    assert "threshold" in defaults
    assert defaults["threshold"].range_min == -60.0


def test_resolver_defensive_parameter_fallback(resolver: KnowledgeResolver) -> None:
    spec = resolver.parameter_spec("unknown_category", "unknown_param")
    assert spec.range_min == 0.0
    assert spec.range_max == 1.0
    assert spec.default == 0.0


def test_resolver_root_cause_lookup(resolver: KnowledgeResolver) -> None:
    mapping = resolver.root_cause_for("harsh high end")
    assert mapping is not None
    assert "excessive 2–5 kHz energy" in mapping.likely_causes


def test_resolver_root_cause_unknown(resolver: KnowledgeResolver) -> None:
    assert resolver.root_cause_for("completely unknown symptom") is None


def test_resolver_best_practices(resolver: KnowledgeResolver) -> None:
    assert resolver.max_chain_steps() == 6
    assert "eq" in resolver.processing_order()
    assert "clip" in resolver.safety_checks()
    template = resolver.explanation_template("score_explanation")
    assert "{score" in template and "{issue_count" in template
