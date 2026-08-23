from __future__ import annotations

from phasenox.knowledge import KnowledgeLoader
from phasenox.knowledge.models import KnowledgeBundle


def test_loader_loads_default_bundle() -> None:
    loader = KnowledgeLoader()
    bundle = loader.load()

    assert isinstance(bundle, KnowledgeBundle)
    assert bundle.version == "7.0.0"
    assert bundle.engineering.mix.lufs_range == (-14.5, -9.0)


def test_loader_loads_from_dict() -> None:
    loader = KnowledgeLoader()
    data = {
        "version": "7.1.0",
        "engineering_rules": {
            "mix": {
                "lufs_range": [-16.0, -10.0],
                "dynamic_range_min": 9.0,
                "peak_max": 1.0,
                "phase_high_threshold": 0.7,
                "phase_low_threshold": 0.3,
                "stereo_width_min": 0.15,
            },
            "stem": {
                "dynamic_range_min": 9.0,
                "peak_max": 1.0,
            },
            "severity_weights": {
                "critical": 1.0,
                "high": 0.75,
                "medium": 0.5,
                "low": 0.25,
                "info": 0.1,
            },
            "category_order": {
                "fix first": 1.0,
                "fine tune": 0.6,
                "optional": 0.3,
            },
            "confidence_defaults": {
                "rule_based": 0.85,
            },
        },
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {
            "categories": {},
            "parameter_defaults": {},
            "target_to_category": {},
            "category_to_plugin_type": {},
        },
        "root_causes": {"mappings": []},
        "best_practices": {
            "processing_order": [],
            "max_chain_steps": 6,
            "explanation_templates": {},
            "safety_checks": [],
        },
    }

    bundle = loader.load_from_dict(data)

    assert bundle.version == "7.1.0"
    assert bundle.engineering.mix.lufs_range == (-16.0, -10.0)
    assert bundle.engineering.mix.dynamic_range_min == 9.0


def test_loader_uses_defaults_for_missing_sections() -> None:
    loader = KnowledgeLoader()
    data = {
        "version": "7.0.0",
        "engineering_rules": {},
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {},
        "root_causes": {},
        "best_practices": {},
    }

    bundle = loader.load_from_dict(data)

    assert bundle.engineering.mix.lufs_range == (-14.5, -9.0)
    assert bundle.engineering.mix.dynamic_range_min == 8.0
