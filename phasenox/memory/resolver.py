from __future__ import annotations

from typing import TYPE_CHECKING

from .models import MemoryBundle, ProjectProfile, UserProfile

if TYPE_CHECKING:
    from phasenox.knowledge.resolver import KnowledgeResolver


class MemoryResolver:
    """
    Read-only resolver that overlays user/project memory on top of Knowledge.

    Memory only overrides Knowledge when an explicit preference exists.
    All other queries fall back to the injected ``KnowledgeResolver`` or to
    safe global defaults.
    """

    def __init__(
        self,
        memory_bundle: MemoryBundle,
        knowledge_resolver: KnowledgeResolver | None = None,
    ) -> None:
        self._memory = memory_bundle
        self._knowledge = knowledge_resolver

    @property
    def memory_bundle(self) -> MemoryBundle:
        return self._memory

    @property
    def user_profile(self) -> UserProfile:
        return self._memory.user_profile

    @property
    def project_profile(self) -> ProjectProfile:
        return self._memory.project_profile

    # ------------------------------------------------------------------
    # Loudness overrides
    # ------------------------------------------------------------------

    def target_lufs(self, platform: str | None, genre: str | None) -> float:
        """Return user-preferred loudness for a platform, or ask Knowledge."""
        if platform is not None:
            platform_key = platform.lower()
            if platform_key in self._memory.user_profile.preferred_loudness_by_platform:
                return self._memory.user_profile.preferred_loudness_by_platform[platform_key]
        if self._knowledge is not None:
            return self._knowledge.target_lufs(platform, genre)
        return -14.0

    def true_peak_max(self, platform: str | None) -> float:
        """Return user-preferred true peak, or ask Knowledge."""
        if self._memory.user_profile.preferred_true_peak_max is not None:
            return self._memory.user_profile.preferred_true_peak_max
        if self._knowledge is not None:
            return self._knowledge.true_peak_max(platform)
        return -1.0

    def recommended_dynamic_range_min(self, platform: str | None) -> float | None:
        """Return user-preferred dynamic range minimum, or ask Knowledge."""
        if self._memory.user_profile.preferred_dynamic_range_min is not None:
            return self._memory.user_profile.preferred_dynamic_range_min
        if self._knowledge is not None:
            return self._knowledge.recommended_dynamic_range_min(platform)
        return None

    # ------------------------------------------------------------------
    # Processing order override
    # ------------------------------------------------------------------

    def processing_order(self) -> list[str]:
        """Return user-preferred processing order, or ask Knowledge."""
        if self._memory.user_profile.preferred_processing_order:
            return list(self._memory.user_profile.preferred_processing_order)
        if self._knowledge is not None:
            return self._knowledge.processing_order()
        return []

    # ------------------------------------------------------------------
    # Memory-only preferences
    # ------------------------------------------------------------------

    def preferred_plugin_brands(self) -> list[str]:
        return list(self._memory.user_profile.preferred_plugin_brands)

    def preferred_genres(self) -> list[str]:
        return list(self._memory.user_profile.preferred_genres)

    def preferred_export_targets(self) -> list[str]:
        return list(self._memory.user_profile.preferred_export_targets)

    # ------------------------------------------------------------------
    # Project context
    # ------------------------------------------------------------------

    def project_target_platform(self) -> str | None:
        return self._memory.project_profile.target_platform

    def project_genre(self) -> str | None:
        return self._memory.project_profile.genre

    def project_delivery_targets(self) -> list[str]:
        return list(self._memory.project_profile.delivery_targets)

    def project_reference_paths(self) -> list[str]:
        return list(self._memory.project_profile.reference_paths)

    # ------------------------------------------------------------------
    # Knowledge delegation helpers
    # ------------------------------------------------------------------

    def knowledge_resolver(self) -> KnowledgeResolver | None:
        """Expose the underlying KnowledgeResolver for non-overridden queries."""
        return self._knowledge

    def mix_lufs_range(self) -> tuple[float, float]:
        if self._knowledge is not None:
            return self._knowledge.mix_lufs_range()
        return (-14.5, -9.0)

    def dynamic_range_min(self, is_full_mix: bool) -> float:
        if self._knowledge is not None:
            return self._knowledge.dynamic_range_min(is_full_mix)
        return 8.0
