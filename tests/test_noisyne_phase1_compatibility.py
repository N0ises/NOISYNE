from __future__ import annotations

import importlib
import io
from contextlib import redirect_stdout
from pathlib import Path

from brain.application.soundbrain_service import SoundBrainService

from phasenox.application.noisyne_service import (
    NoisyneService,
)
from phasenox.application.noisyne_service import (
    PhasenoxService as CanonicalService,
)
from phasenox.reference.models import ReferenceComparison, ReferenceReport
from phasenox.reference.report_builder import ReferenceReportBuilder
from phasenox.runtime.engine_registry import registry


class TestNoisyneServiceAlias:
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

    def test_soundbrain_service_import_path_still_works(self):
        from brain.application.soundbrain_service import (
            AnalysisRequest,
            AnalysisResponse,
            SoundBrainService,
        )

        assert SoundBrainService is CanonicalService
        assert AnalysisRequest is not None
        assert AnalysisResponse is not None

    def test_noisyne_service_import_path_works(self):
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


class TestEngineRegistryAliases:
    """Both `noisyne` and `soundbrain` engine keys resolve to the canonical service."""

    def test_noisyne_engine_registered(self):
        assert registry.exists("noisyne")

    def test_soundbrain_engine_still_registered(self):
        assert registry.exists("soundbrain")

    def test_both_keys_resolve_to_same_factory(self):
        assert registry.get("noisyne") is registry.get("soundbrain")


class TestCliIdentity:
    """Only the canonical ``phasenox`` CLI remains installed after R3."""

    @staticmethod
    def _capture_help(args: list[str]) -> str:
        from main import main

        captured = io.StringIO()
        try:
            with redirect_stdout(captured):
                main(args)
        except SystemExit as exc:
            assert exc.code == 0
        return captured.getvalue()

    def test_help_shows_product_identity(self):
        output = self._capture_help(["--help"])
        assert "PHASENØX" in output

    def test_top_level_usage_uses_phasenox(self):
        output = self._capture_help(["--help"])
        assert "usage: phasenox" in output

    def test_analyze_help_uses_phasenox(self):
        output = self._capture_help(["analyze", "--help"])
        assert "usage: phasenox analyze" in output

    def test_pyproject_has_only_phasenox_entry_point(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        scripts = text.split("[project.scripts]", maxsplit=1)[1].split("[", maxsplit=1)[0]
        assert scripts.strip() == 'phasenox = "phasenox.cli:main"'


class TestReportIdentity:
    """Generated reference reports use the current PHASENØX product identity."""

    def _minimal_report(self) -> ReferenceReport:
        comparison = ReferenceComparison(
            similarity=88.0,
            confidence=0.95,
            frequency_score=88.0,
            dynamic_score=88.0,
            stereo_score=88.0,
            loudness_score=88.0,
            transient_score=88.0,
            phase_score=88.0,
            tonal_score=88.0,
            semantic_score=88.0,
            band_differences=[],
            engineer_decisions=[],
            metrics=[],
        )
        return ReferenceReport(
            comparison=comparison,
            summary="test",
            strengths=[],
            weaknesses=[],
            priorities=[],
            next_actions=[],
        )

    def test_markdown_title_uses_noisyne(self):
        report = self._minimal_report()
        markdown = ReferenceReportBuilder().build_markdown(report)
        assert markdown.startswith("# PHASENØX Reference Report")


class TestNamespaceCompatibility:
    """The canonical namespace is ``noisyne`` and ``brain`` remains compatible."""

    def test_noisyne_namespace_importable(self):
        import phasenox

        assert phasenox.__name__ == "phasenox"

    def test_brain_namespace_importable(self):
        import brain

        assert brain.__name__ == "brain"

    def test_noisyne_service_module_under_brain_is_canonical(self):
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
