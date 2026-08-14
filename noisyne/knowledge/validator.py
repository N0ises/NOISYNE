from __future__ import annotations

from typing import ClassVar

from .models import (
    EngineeringRuleBase,
    GenreProfile,
    KnowledgeBundle,
    PlatformProfile,
    PluginCapabilityKnowledge,
    RootCauseKnowledge,
)


class KnowledgeValidator:
    """Validate a KnowledgeBundle for required keys and sensible ranges."""

    _REQUIRED_SEVERITY_WEIGHTS: ClassVar[set[str]] = frozenset(
        {"critical", "high", "medium", "low", "info"}
    )
    _REQUIRED_CATEGORY_ORDER: ClassVar[set[str]] = frozenset({"fix first", "fine tune", "optional"})

    def validate(self, bundle: KnowledgeBundle) -> list[str]:
        """Return a list of validation error messages. Empty means valid."""
        errors: list[str] = []
        if not bundle.version:
            errors.append("version is required")
        else:
            errors.extend(self._validate_version(bundle.version))

        errors.extend(self._validate_engineering(bundle.engineering))
        errors.extend(self._validate_genres(bundle.genres))
        errors.extend(self._validate_platforms(bundle.platforms))
        errors.extend(self._validate_plugin_capabilities(bundle.plugin_capabilities))
        errors.extend(self._validate_root_causes(bundle.root_causes))
        errors.extend(self._validate_best_practices(bundle.best_practices))
        return errors

    def is_valid(self, bundle: KnowledgeBundle) -> bool:
        return not self.validate(bundle)

    def require_version(self, bundle: KnowledgeBundle, spec: str) -> bool:
        """
        Check whether ``bundle.version`` satisfies a simple spec.

        Supported spec format: ``>=MAJOR.MINOR`` (e.g. ``>=7.0``).
        """
        bundle_version = self._parse_version(bundle.version)
        required_version = self._parse_version(spec.lstrip(">=").strip())
        if bundle_version is None or required_version is None:
            return False
        return bundle_version >= required_version

    def _validate_version(self, version: str) -> list[str]:
        errors: list[str] = []
        parsed = self._parse_version(version)
        if parsed is None:
            errors.append(f"version '{version}' is not a valid semantic version")
        elif parsed[0] < 7:
            errors.append(f"version {version} is below the minimum supported major version 7")
        return errors

    def _validate_engineering(self, engineering: EngineeringRuleBase) -> list[str]:
        errors: list[str] = []
        mix = engineering.mix
        if mix.lufs_range[0] >= mix.lufs_range[1]:
            errors.append("engineering.mix.lufs_range min must be less than max")
        if mix.peak_max < 0.0:
            errors.append("engineering.mix.peak_max must be non-negative")
        if mix.phase_high_threshold <= mix.phase_low_threshold:
            errors.append(
                "engineering.mix.phase_high_threshold must be greater than " "phase_low_threshold"
            )
        if mix.stereo_width_min < 0.0 or mix.stereo_width_min > 1.0:
            errors.append("engineering.mix.stereo_width_min must be between 0 and 1")

        missing_severity = self._REQUIRED_SEVERITY_WEIGHTS - set(engineering.severity_weights)
        if missing_severity:
            errors.append(f"engineering.severity_weights missing: {sorted(missing_severity)}")

        missing_category = self._REQUIRED_CATEGORY_ORDER - set(engineering.category_order)
        if missing_category:
            errors.append(f"engineering.category_order missing: {sorted(missing_category)}")
        return errors

    def _validate_genres(self, genres: dict[str, GenreProfile]) -> list[str]:
        errors: list[str] = []
        for key, profile in genres.items():
            if profile.expected_spectral_centroid_range is not None:
                r = profile.expected_spectral_centroid_range
                if r[0] >= r[1] or r[0] < 0:
                    errors.append(f"genre '{key}' expected_spectral_centroid_range is invalid")
            if profile.typical_stereo_width_min is not None and (
                profile.typical_stereo_width_min < 0.0 or profile.typical_stereo_width_min > 1.0
            ):
                errors.append(f"genre '{key}' typical_stereo_width_min must be between 0 and 1")
        return errors

    def _validate_platforms(self, platforms: dict[str, PlatformProfile]) -> list[str]:
        errors: list[str] = []
        for key, profile in platforms.items():
            if profile.target_lufs > 0.0:
                errors.append(f"platform '{key}' target_lufs is unexpectedly positive")
            if profile.true_peak_max > 0.0:
                errors.append(f"platform '{key}' true_peak_max is unexpectedly positive")
        return errors

    def _validate_plugin_capabilities(self, plugin: PluginCapabilityKnowledge) -> list[str]:
        errors: list[str] = []
        for target, category in plugin.target_to_category.items():
            if category not in plugin.categories:
                errors.append(
                    f"plugin target_to_category '{target}' -> '{category}' "
                    f"references unknown category"
                )
        for category in plugin.category_to_plugin_type:
            if category not in plugin.categories:
                errors.append(
                    f"plugin category_to_plugin_type '{category}' references " f"unknown category"
                )
        for cat_key, params in plugin.parameter_defaults.items():
            if cat_key not in plugin.categories:
                errors.append(f"plugin parameter_defaults '{cat_key}' references unknown category")
            for param_name, spec in params.items():
                if spec.range_min >= spec.range_max:
                    errors.append(f"plugin parameter '{cat_key}.{param_name}' range is invalid")
                if spec.default < spec.range_min or spec.default > spec.range_max:
                    errors.append(
                        f"plugin parameter '{cat_key}.{param_name}' default is " f"outside range"
                    )
        return errors

    def _validate_root_causes(self, root_causes: RootCauseKnowledge) -> list[str]:
        errors: list[str] = []
        for idx, mapping in enumerate(root_causes.mappings):
            if not mapping.symptom_keywords:
                errors.append(f"root_cause mapping {idx} has no symptom_keywords")
            if not mapping.likely_causes:
                errors.append(f"root_cause mapping {idx} has no likely_causes")
            if not 0.0 <= mapping.confidence <= 1.0:
                errors.append(f"root_cause mapping {idx} confidence must be between 0 and 1")
        return errors

    def _validate_best_practices(self, best_practices) -> list[str]:
        errors: list[str] = []
        if best_practices.max_chain_steps <= 0:
            errors.append("best_practices.max_chain_steps must be positive")
        return errors

    @staticmethod
    def _parse_version(version: str) -> tuple[int, int, int] | None:
        """Parse a simple ``major.minor.patch`` version string."""
        try:
            parts = [int(p) for p in version.split(".")[:3]]
            if len(parts) < 2:
                return None
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts)  # type: ignore[return-value]
        except (ValueError, AttributeError):
            return None
