from __future__ import annotations

from phasenox.knowledge import KnowledgeValidator
from phasenox.knowledge.loader import KnowledgeLoader


def test_validator_passes_default_bundle() -> None:
    bundle = KnowledgeLoader().load()
    errors = KnowledgeValidator().validate(bundle)

    assert errors == []
    assert KnowledgeValidator().is_valid(bundle)


def test_validator_rejects_empty_version() -> None:
    data = {
        "version": "",
        "engineering_rules": {},
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {},
        "root_causes": {},
        "best_practices": {},
    }
    bundle = KnowledgeLoader().load_from_dict(data)
    errors = KnowledgeValidator().validate(bundle)

    assert any("version" in error.lower() for error in errors)


def test_validator_rejects_invalid_lufs_range() -> None:
    data = {
        "version": "7.0.0",
        "engineering_rules": {
            "mix": {
                "lufs_range": [-9.0, -14.5],
                "dynamic_range_min": 8.0,
                "peak_max": 1.0,
                "phase_high_threshold": 0.7,
                "phase_low_threshold": 0.3,
                "stereo_width_min": 0.10,
            },
            "stem": {
                "dynamic_range_min": 8.0,
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
            "confidence_defaults": {},
        },
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {},
        "root_causes": {},
        "best_practices": {
            "processing_order": [],
            "max_chain_steps": 6,
        },
    }
    bundle = KnowledgeLoader().load_from_dict(data)
    errors = KnowledgeValidator().validate(bundle)

    assert any("lufs_range" in error for error in errors)


def test_validator_rejects_missing_severity_weights() -> None:
    data = {
        "version": "7.0.0",
        "engineering_rules": {
            "mix": {
                "lufs_range": [-14.5, -9.0],
                "dynamic_range_min": 8.0,
                "peak_max": 1.0,
                "phase_high_threshold": 0.7,
                "phase_low_threshold": 0.3,
                "stereo_width_min": 0.10,
            },
            "stem": {
                "dynamic_range_min": 8.0,
                "peak_max": 1.0,
            },
            "severity_weights": {
                "high": 0.75,
            },
            "category_order": {
                "fix first": 1.0,
                "fine tune": 0.6,
                "optional": 0.3,
            },
            "confidence_defaults": {},
        },
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {},
        "root_causes": {},
        "best_practices": {
            "processing_order": [],
            "max_chain_steps": 6,
        },
    }
    bundle = KnowledgeLoader().load_from_dict(data)
    errors = KnowledgeValidator().validate(bundle)

    assert any("severity_weights" in error for error in errors)


def test_validator_rejects_invalid_parameter_range() -> None:
    data = {
        "version": "7.0.0",
        "engineering_rules": {
            "mix": {
                "lufs_range": [-14.5, -9.0],
                "dynamic_range_min": 8.0,
                "peak_max": 1.0,
                "phase_high_threshold": 0.7,
                "phase_low_threshold": 0.3,
                "stereo_width_min": 0.10,
            },
            "stem": {
                "dynamic_range_min": 8.0,
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
            "confidence_defaults": {},
        },
        "genre_profiles": {},
        "platform_profiles": {},
        "plugin_knowledge": {
            "categories": {
                "eq": {
                    "name": "eq",
                    "family": "tone",
                },
            },
            "parameter_defaults": {
                "eq": {
                    "frequency": {
                        "range_min": 20000.0,
                        "range_max": 20.0,
                        "default": 1000.0,
                    },
                },
            },
            "target_to_category": {},
            "category_to_plugin_type": {},
        },
        "root_causes": {},
        "best_practices": {
            "processing_order": [],
            "max_chain_steps": 6,
        },
    }
    bundle = KnowledgeLoader().load_from_dict(data)
    errors = KnowledgeValidator().validate(bundle)

    assert any("range is invalid" in error for error in errors)


def test_validator_checks_version_spec() -> None:
    bundle = KnowledgeLoader().load()
    validator = KnowledgeValidator()

    assert validator.require_version(bundle, ">=7.0")
    assert not validator.require_version(bundle, ">=8.0")
