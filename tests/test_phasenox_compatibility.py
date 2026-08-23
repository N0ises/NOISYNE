from __future__ import annotations

import importlib

from phasenox.application.noisyne_service import NoisyneService
from phasenox.application.phasenox_service import PhasenoxService as CanonicalService
from phasenox.application.soundbrain_service import SoundBrainService
from phasenox.runtime.engine_registry import registry


class TestLegacyServiceAliases:
    """PhasenoxService is canonical; legacy service names remain aliases."""

    def test_phasenox_service_is_canonical(self):
        assert CanonicalService is not None

    def test_legacy_services_are_aliases(self):
        assert NoisyneService is CanonicalService
        assert SoundBrainService is CanonicalService

    def test_application_module_exports_canonical_and_legacy_names(self):
        from phasenox.application import (
            NoisyneService,
            PhasenoxService,
            SoundBrainService,
        )

        assert PhasenoxService is CanonicalService
        assert NoisyneService is CanonicalService
        assert SoundBrainService is CanonicalService

    def test_legacy_soundbrain_service_import_paths_still_work(self):
        from brain.application.soundbrain_service import (
            AnalysisRequest,
            AnalysisResponse,
        )
        from brain.application.soundbrain_service import (
            SoundBrainService as BrainSoundBrainService,
        )

        from phasenox.application.soundbrain_service import (
            SoundBrainService as ModuleSoundBrainService,
        )

        assert BrainSoundBrainService is CanonicalService
        assert ModuleSoundBrainService is CanonicalService
        assert AnalysisRequest is not None
        assert AnalysisResponse is not None

    def test_legacy_noisyne_service_import_path_works(self):
        from phasenox.application.noisyne_service import (
            AnalysisRequest,
            AnalysisResponse,
            NoisyneService,
            PhasenoxService,
        )

        assert NoisyneService is CanonicalService
        assert PhasenoxService is CanonicalService
        assert AnalysisRequest is not None
        assert AnalysisResponse is not None

    def test_legacy_v2_service_name_is_canonical_alias(self):
        from phasenox.application import NoisyneV2Service, PhasenoxV2Service

        assert NoisyneV2Service is PhasenoxV2Service

    def test_legacy_report_name_is_canonical_alias(self):
        from phasenox.report.models import PhasenoxReport, SoundBrainReport

        assert SoundBrainReport is PhasenoxReport

    def test_legacy_fixture_provider_name_is_canonical_alias(self):
        from phasenox.perception.validation_fixtures import (
            NoisyneValidationFixtureProvider,
            PhasenoxValidationFixtureProvider,
        )

        assert NoisyneValidationFixtureProvider is PhasenoxValidationFixtureProvider


class TestEngineRegistryAliases:
    """Both `noisyne` and `soundbrain` engine keys resolve to the canonical service."""

    def test_noisyne_engine_registered(self):
        assert registry.exists("noisyne")

    def test_soundbrain_engine_still_registered(self):
        assert registry.exists("soundbrain")

    def test_both_keys_resolve_to_same_factory(self):
        assert registry.get("noisyne") is registry.get("soundbrain")


class TestNamespaceCompatibility:
    """The canonical namespace is ``phasenox`` and ``brain`` remains compatible."""

    def test_phasenox_namespace_importable(self):
        import phasenox

        assert phasenox.__name__ == "phasenox"

    def test_brain_namespace_importable(self):
        import brain

        assert brain.__name__ == "brain"

    def test_legacy_noisyne_service_module_under_brain_is_canonical(self):
        legacy_module = importlib.import_module("brain.application.noisyne_service")
        canonical_module = importlib.import_module("phasenox.application.noisyne_service")

        assert legacy_module is canonical_module
        assert legacy_module.PhasenoxService is CanonicalService
        assert legacy_module.NoisyneService is CanonicalService

    def test_legacy_application_exports_canonical_service(self):
        from brain.application import NoisyneService as LegacyNoisyneService
        from brain.application import PhasenoxService as LegacyPhasenoxService
        from brain.application import SoundBrainService as LegacySoundBrainService

        assert LegacyPhasenoxService is CanonicalService
        assert LegacyNoisyneService is CanonicalService
        assert LegacySoundBrainService is CanonicalService
