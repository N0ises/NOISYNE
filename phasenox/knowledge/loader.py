from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    BestPracticeKnowledge,
    EngineeringRuleBase,
    GenreProfile,
    KnowledgeBundle,
    MixRules,
    ParameterSpec,
    PlatformProfile,
    PluginCapabilityKnowledge,
    PluginCategoryKnowledge,
    RootCauseKnowledge,
    RootCauseMapping,
    StemRules,
)


class KnowledgeLoader:
    """Load a KnowledgeBundle from YAML files or an inline dictionary."""

    def __init__(self, root: str | Path = "configs/knowledge") -> None:
        self._root = Path(root)

    def load(self) -> KnowledgeBundle:
        """Load the default knowledge bundle from ``root/knowledge_bundle.yaml``."""
        return self.load_from_path(self._root / "knowledge_bundle.yaml")

    def load_from_path(self, path: str | Path) -> KnowledgeBundle:
        """Load a knowledge bundle from a master YAML file."""
        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError(f"Knowledge bundle must be a mapping: {path}")
        return self._parse_bundle(data, path.parent)

    def load_from_dict(self, data: dict[str, Any]) -> KnowledgeBundle:
        """Load a knowledge bundle from a fully populated dictionary."""
        if not isinstance(data, dict):
            raise TypeError("Knowledge bundle must be a mapping")
        return self._parse_bundle(data, None)

    def _parse_bundle(
        self,
        data: dict[str, Any],
        base_dir: Path | None,
    ) -> KnowledgeBundle:
        version = str(data.get("version", "0.0.0"))

        engineering = self._load_section("engineering_rules", data, base_dir, default_factory=dict)
        genres = self._load_section("genre_profiles", data, base_dir, default_factory=dict)
        platforms = self._load_section("platform_profiles", data, base_dir, default_factory=dict)
        plugin = self._load_section("plugin_knowledge", data, base_dir, default_factory=dict)
        root_causes = self._load_section("root_causes", data, base_dir, default_factory=dict)
        best_practices = self._load_section("best_practices", data, base_dir, default_factory=dict)

        return KnowledgeBundle(
            version=version,
            engineering=self._parse_engineering(engineering),
            genres=self._parse_genres(genres),
            platforms=self._parse_platforms(platforms),
            plugin_capabilities=self._parse_plugin_capabilities(plugin),
            root_causes=self._parse_root_causes(root_causes),
            best_practices=self._parse_best_practices(best_practices),
        )

    def _load_section(
        self,
        name: str,
        data: dict[str, Any],
        base_dir: Path | None,
        default_factory: Any = None,
    ) -> Any:
        """Resolve a section either inline or from a referenced YAML file."""
        value = data.get(name, default_factory() if default_factory else None)
        if isinstance(value, str) and base_dir is not None:
            section_path = base_dir / value
            section_data = yaml.safe_load(section_path.read_text(encoding="utf-8"))
            if isinstance(section_data, dict) and name in section_data:
                return section_data[name]
            return section_data
        return value

    def _parse_engineering(self, data: dict[str, Any]) -> EngineeringRuleBase:
        mix = data.get("mix", {})
        stem = data.get("stem", {})
        return EngineeringRuleBase(
            mix=MixRules(
                lufs_range=tuple(mix.get("lufs_range", [-14.5, -9.0])),
                dynamic_range_min=float(mix.get("dynamic_range_min", 8.0)),
                peak_max=float(mix.get("peak_max", 1.0)),
                phase_high_threshold=float(mix.get("phase_high_threshold", 0.7)),
                phase_low_threshold=float(mix.get("phase_low_threshold", 0.3)),
                stereo_width_min=float(mix.get("stereo_width_min", 0.10)),
            ),
            stem=StemRules(
                dynamic_range_min=float(stem.get("dynamic_range_min", 8.0)),
                peak_max=float(stem.get("peak_max", 1.0)),
            ),
            severity_weights=dict(
                data.get(
                    "severity_weights",
                    {
                        "critical": 1.0,
                        "high": 0.75,
                        "medium": 0.5,
                        "low": 0.25,
                        "info": 0.1,
                    },
                )
            ),
            category_order=dict(
                data.get(
                    "category_order",
                    {
                        "fix first": 1.0,
                        "fine tune": 0.6,
                        "optional": 0.3,
                    },
                )
            ),
            confidence_defaults=dict(
                data.get(
                    "confidence_defaults",
                    {
                        "rule_based": 0.85,
                        "measurement": 0.90,
                    },
                )
            ),
        )

    def _parse_genres(self, data: dict[str, Any]) -> dict[str, GenreProfile]:
        result: dict[str, GenreProfile] = {}
        for key, value in data.items():
            range_val = value.get("expected_spectral_centroid_range")
            if range_val is not None:
                range_val = tuple(range_val)
            result[key] = GenreProfile(
                name=value.get("name", key),
                description=value.get("description", ""),
                expected_spectral_centroid_range=range_val,
                expected_dynamic_range_min=value.get("expected_dynamic_range_min"),
                typical_stereo_width_min=value.get("typical_stereo_width_min"),
                target_loudness_by_platform=dict(value.get("target_loudness_by_platform", {})),
                common_issues=list(value.get("common_issues", [])),
                common_chain=list(value.get("common_chain", [])),
            )
        return result

    def _parse_platforms(self, data: dict[str, Any]) -> dict[str, PlatformProfile]:
        result: dict[str, PlatformProfile] = {}
        for key, value in data.items():
            result[key] = PlatformProfile(
                name=value.get("name", key),
                target_lufs=float(value.get("target_lufs", -14.0)),
                true_peak_max=float(value.get("true_peak_max", -1.0)),
                format_requirements=list(value.get("format_requirements", [])),
                loudness_standard=value.get("loudness_standard", ""),
                recommended_dynamic_range_min=value.get("recommended_dynamic_range_min"),
                notes=list(value.get("notes", [])),
            )
        return result

    def _parse_plugin_capabilities(self, data: dict[str, Any]) -> PluginCapabilityKnowledge:
        categories: dict[str, PluginCategoryKnowledge] = {}
        for key, value in data.get("categories", {}).items():
            categories[key] = PluginCategoryKnowledge(
                name=value.get("name", key),
                family=value.get("family", ""),
                typical_use=value.get("typical_use", ""),
                safe_order=int(value.get("safe_order", 0)),
                parameter_order=list(value.get("parameter_order", [])),
            )

        parameter_defaults: dict[str, dict[str, ParameterSpec]] = {}
        for cat_key, params in data.get("parameter_defaults", {}).items():
            parameter_defaults[cat_key] = {}
            for param_key, spec in params.items():
                parameter_defaults[cat_key][param_key] = ParameterSpec(
                    range_min=float(spec.get("range_min", 0.0)),
                    range_max=float(spec.get("range_max", 1.0)),
                    default=float(spec.get("default", 0.0)),
                    unit=spec.get("unit"),
                    step=spec.get("step"),
                )

        return PluginCapabilityKnowledge(
            categories=categories,
            parameter_defaults=parameter_defaults,
            target_to_category=dict(data.get("target_to_category", {})),
            category_to_plugin_type=dict(data.get("category_to_plugin_type", {})),
        )

    def _parse_root_causes(self, data: dict[str, Any]) -> RootCauseKnowledge:
        mappings: list[RootCauseMapping] = []
        for mapping in data.get("mappings", []):
            mappings.append(
                RootCauseMapping(
                    symptom_keywords=list(mapping.get("symptom_keywords", [])),
                    likely_causes=list(mapping.get("likely_causes", [])),
                    priority=mapping.get("priority", "medium"),
                    confidence=float(mapping.get("confidence", 0.80)),
                    required_measurements=list(mapping.get("required_measurements", [])),
                )
            )
        return RootCauseKnowledge(mappings=mappings)

    def _parse_best_practices(self, data: dict[str, Any]) -> BestPracticeKnowledge:
        return BestPracticeKnowledge(
            processing_order=list(data.get("processing_order", [])),
            max_chain_steps=int(data.get("max_chain_steps", 6)),
            explanation_templates=dict(data.get("explanation_templates", {})),
            safety_checks=list(data.get("safety_checks", [])),
        )
