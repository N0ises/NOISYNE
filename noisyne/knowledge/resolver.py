from __future__ import annotations

from .models import (
    GenreProfile,
    KnowledgeBundle,
    ParameterSpec,
    PlatformProfile,
    PluginCategoryKnowledge,
    RootCauseMapping,
)


class KnowledgeResolver:
    """
    Read-only query interface over a validated KnowledgeBundle.

    All methods return defensive defaults when a requested key is missing so
    that future consumers can degrade gracefully.
    """

    def __init__(self, bundle: KnowledgeBundle) -> None:
        self._bundle = bundle

    # ------------------------------------------------------------------
    # Engineering
    # ------------------------------------------------------------------

    def mix_lufs_range(self) -> tuple[float, float]:
        return self._bundle.engineering.mix.lufs_range

    def dynamic_range_min(self, is_full_mix: bool) -> float:
        if is_full_mix:
            return self._bundle.engineering.mix.dynamic_range_min
        return self._bundle.engineering.stem.dynamic_range_min

    def peak_max(self, is_full_mix: bool) -> float:
        if is_full_mix:
            return self._bundle.engineering.mix.peak_max
        return self._bundle.engineering.stem.peak_max

    def phase_high_threshold(self) -> float:
        return self._bundle.engineering.mix.phase_high_threshold

    def phase_low_threshold(self) -> float:
        return self._bundle.engineering.mix.phase_low_threshold

    def stereo_width_min(self) -> float:
        return self._bundle.engineering.mix.stereo_width_min

    def severity_weight(self, severity: str) -> float:
        return self._bundle.engineering.severity_weights.get(severity.lower(), 0.3)

    def category_weight(self, category: str) -> float:
        return self._bundle.engineering.category_order.get(category.lower(), 0.3)

    def confidence_default(self, key: str) -> float:
        return self._bundle.engineering.confidence_defaults.get(key, 0.85)

    # ------------------------------------------------------------------
    # Genre / Platform
    # ------------------------------------------------------------------

    def genre_profile(self, genre: str | None) -> GenreProfile | None:
        if genre is None:
            return None
        return self._bundle.genres.get(genre.lower())

    def platform_profile(self, platform: str | None) -> PlatformProfile | None:
        if platform is None:
            return None
        return self._bundle.platforms.get(platform.lower())

    def target_lufs(self, platform: str | None, genre: str | None) -> float:
        """
        Resolve target loudness.

        Genre-specific platform targets take precedence, then platform
        defaults, then the global fallback of -14 LUFS.
        """
        if genre is not None and platform is not None:
            genre_profile = self.genre_profile(genre)
            if genre_profile is not None:
                platform_key = platform.lower()
                if platform_key in genre_profile.target_loudness_by_platform:
                    return genre_profile.target_loudness_by_platform[platform_key]

        profile = self.platform_profile(platform)
        if profile is not None:
            return profile.target_lufs

        return -14.0

    def true_peak_max(self, platform: str | None) -> float:
        profile = self.platform_profile(platform)
        if profile is not None:
            return profile.true_peak_max
        return -1.0

    def recommended_dynamic_range_min(self, platform: str | None) -> float | None:
        profile = self.platform_profile(platform)
        if profile is not None:
            return profile.recommended_dynamic_range_min
        return None

    # ------------------------------------------------------------------
    # Plugin capabilities
    # ------------------------------------------------------------------

    def plugin_categories(self) -> dict[str, PluginCategoryKnowledge]:
        return dict(self._bundle.plugin_capabilities.categories)

    def plugin_category_for_target(self, target: str) -> str:
        return self._bundle.plugin_capabilities.target_to_category.get(target, "utility")

    def plugin_type_for_category(self, category: str) -> str:
        return self._bundle.plugin_capabilities.category_to_plugin_type.get(category, "Utility")

    def parameter_spec(self, category: str, parameter: str) -> ParameterSpec:
        defaults = self._bundle.plugin_capabilities.parameter_defaults.get(category, {})
        return defaults.get(
            parameter,
            ParameterSpec(range_min=0.0, range_max=1.0, default=0.0),
        )

    def parameter_defaults(self, category: str) -> dict[str, ParameterSpec]:
        return dict(self._bundle.plugin_capabilities.parameter_defaults.get(category, {}))

    def plugin_parameter_order(self, category: str) -> list[str]:
        cat = self._bundle.plugin_capabilities.categories.get(category)
        if cat is None:
            return []
        return list(cat.parameter_order)

    def plugin_family(self, category: str) -> str:
        cat = self._bundle.plugin_capabilities.categories.get(category)
        if cat is None:
            return ""
        return cat.family

    # ------------------------------------------------------------------
    # Root causes
    # ------------------------------------------------------------------

    def root_cause_mappings(self) -> list[RootCauseMapping]:
        return list(self._bundle.root_causes.mappings)

    def root_cause_for(self, symptom: str) -> RootCauseMapping | None:
        symptom_lower = symptom.lower()
        for mapping in self._bundle.root_causes.mappings:
            if any(keyword in symptom_lower for keyword in mapping.symptom_keywords):
                return mapping
        return None

    # ------------------------------------------------------------------
    # Best practices
    # ------------------------------------------------------------------

    def processing_order(self) -> list[str]:
        return list(self._bundle.best_practices.processing_order)

    def max_chain_steps(self) -> int:
        return self._bundle.best_practices.max_chain_steps

    def explanation_template(self, key: str) -> str:
        return self._bundle.best_practices.explanation_templates.get(key, "")

    def safety_checks(self) -> list[str]:
        return list(self._bundle.best_practices.safety_checks)
