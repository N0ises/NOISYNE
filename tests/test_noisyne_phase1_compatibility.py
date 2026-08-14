from __future__ import annotations

import importlib
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest
from brain.application.soundbrain_service import SoundBrainService

from noisyne.application.noisyne_service import NoisyneService as CanonicalService
from noisyne.reference.models import ReferenceComparison, ReferenceReport
from noisyne.reference.report_builder import ReferenceReportBuilder
from noisyne.runtime.engine_registry import registry


class TestNoisyneServiceAlias:
    """NoisyneService is the canonical facade; SoundBrainService remains an alias."""

    def test_noisyne_service_is_canonical(self):
        assert CanonicalService is not None

    def test_soundbrain_service_is_alias(self):
        assert SoundBrainService is CanonicalService

    def test_application_module_exports_both(self):
        from noisyne.application import NoisyneService, SoundBrainService

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
        from noisyne.application.noisyne_service import (
            AnalysisRequest,
            AnalysisResponse,
            NoisyneService,
        )

        assert NoisyneService is CanonicalService
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


class TestCliAliases:
    """The canonical `noisyne` CLI and the legacy `soundbrain` alias share behavior."""

    @staticmethod
    def _capture_help(command: str, args: list[str]) -> str:
        from main import main

        old_argv0 = sys.argv[0] if sys.argv else ""
        sys.argv[0] = command
        try:
            captured = io.StringIO()
            try:
                with redirect_stdout(captured):
                    main(args)
            except SystemExit as exc:
                assert exc.code == 0
            return captured.getvalue()
        finally:
            sys.argv[0] = old_argv0

    @pytest.mark.parametrize("command", ["noisyne", "soundbrain"])
    def test_help_shows_product_identity(self, command):
        output = self._capture_help(command, ["--help"])
        assert "NØISYNE" in output

    @pytest.mark.parametrize("command", ["noisyne", "soundbrain"])
    def test_top_level_usage_uses_invoked_command(self, command):
        output = self._capture_help(command, ["--help"])
        assert f"usage: {command}" in output

    @pytest.mark.parametrize("command", ["noisyne", "soundbrain"])
    def test_analyze_help_uses_invoked_command(self, command):
        output = self._capture_help(command, ["analyze", "--help"])
        assert f"usage: {command} analyze" in output

    def test_pyproject_has_both_entry_points(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        assert 'noisyne = "noisyne.cli:main"' in text
        assert 'soundbrain = "noisyne.cli:main"' in text


class TestReportIdentity:
    """Generated reference reports use the current NØISYNE product identity."""

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
        assert markdown.startswith("# NØISYNE Reference Report")


class TestNamespaceCompatibility:
    """The canonical namespace is ``noisyne`` and ``brain`` remains compatible."""

    def test_noisyne_namespace_importable(self):
        import noisyne

        assert noisyne.__name__ == "noisyne"

    def test_brain_namespace_importable(self):
        import brain

        assert brain.__name__ == "brain"

    def test_noisyne_service_module_under_brain_is_canonical(self):
        legacy_module = importlib.import_module("brain.application.noisyne_service")
        canonical_module = importlib.import_module("noisyne.application.noisyne_service")

        assert legacy_module is canonical_module
        assert legacy_module.NoisyneService is CanonicalService

    def test_legacy_application_exports_canonical_service(self):
        from brain.application import NoisyneService as LegacyNoisyneService

        assert LegacyNoisyneService is CanonicalService
