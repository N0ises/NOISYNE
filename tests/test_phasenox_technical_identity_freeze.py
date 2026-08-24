from __future__ import annotations

import ast
import importlib
import re
import tomllib
from pathlib import Path

import pytest

from phasenox.application import (
    NoisyneService,
    PhasenoxService,
    PhasenoxV2Service,
    SoundBrainService,
)
from phasenox.application.noisyne_service import (
    NoisyneService as ModuleNoisyneService,
)
from phasenox.application.phasenox_service import (
    PhasenoxService as CanonicalService,
)
from phasenox.application.service import NoisyneV2Service
from phasenox.application.soundbrain_service import (
    SoundBrainService as ModuleSoundBrainService,
)
from phasenox.infrastructure.config.loader import get_application_root
from phasenox.infrastructure.config.models import ChromaConfig
from phasenox.memory.vector.config import DEFAULT_COLLECTION
from phasenox.perception.validation_fixtures import (
    NoisyneValidationFixtureProvider,
    PhasenoxValidationFixtureProvider,
)
from phasenox.report import PhasenoxReport, SoundBrainReport
from phasenox.runtime.engine_registry import registry
from phasenox.ui.branding import DESKTOP_APPLICATION_ID
from phasenox.ui.data_location import (
    CANONICAL_DESKTOP_IDENTITY,
    LEGACY_DESKTOP_IDENTITY,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DOCUMENT = PROJECT_ROOT / "docs" / "PHASENOX_TECHNICAL_IDENTITY_FREEZE.md"

PRODUCTION_ROOTS = (
    PROJECT_ROOT / "phasenox",
    PROJECT_ROOT / "brain",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "tools",
)

CURRENT_FACING_IDENTITY_FILES = (
    PROJECT_ROOT / "phasenox" / "audio" / "analysis" / "report.py",
    PROJECT_ROOT / "phasenox" / "audio" / "engineer" / "report.py",
    PROJECT_ROOT / "phasenox" / "prompt" / "prompt_builder.py",
    PROJECT_ROOT / "phasenox" / "reasoning" / "prompts.py",
    PROJECT_ROOT / "scripts" / "export_project.py",
)

LEGACY_PRODUCT_TOKENS = (
    "noisyne",
    "Noisyne",
    "NOISYNE",
    "soundbrain",
    "SoundBrain",
    "SOUNDBRAIN",
)

EXPECTED_SERIALIZED_IDENTIFIERS = frozenset(
    {
        "noisyne.auditory_frontend",
        "noisyne.brightness_power_spectral_centroid_correlate",
        "noisyne.calibrated_loudness_foundation",
        "noisyne.context_policy_binding",
        "noisyne.descriptor.roughness",
        "noisyne.descriptor.sharpness",
        "noisyne.deterministic_reasoning",
        "noisyne.digital_programme_energy_sum",
        "noisyne.explicit_linear_playback_transfer",
        "noisyne.grounded_perceptual_reasoning_foundation",
        "noisyne.in_memory_memory_store",
        "noisyne.knowledge_memory_foundation",
        "noisyne.knowledge_retrieval_contract",
        "noisyne.mix_intelligence_canonical_json_sha256",
        "noisyne.perceptual_context_foundation",
        "noisyne.perceptual_mix_intelligence_foundation",
        "noisyne.perceptual_reference_foundation",
        "noisyne.personalization_foundation",
        "noisyne.policy_conditioned_translation_risk",
        "noisyne.reference_embedding_cosine",
        "noisyne.reference_erb_programme_power_delta",
        "noisyne.reference_programme_energy_delta",
        "noisyne.reference_sample_peak_delta",
        "noisyne.relative_simultaneous_masking_foundation",
        "noisyne.sprint2_erb_programme_power_delta",
        "noisyne.translation_evidence_foundation",
        "noisyne.v1.integrated_programme_loudness",
    }
)

SERIALIZED_IDENTIFIER_PATTERN = re.compile(r"\bnoisyne\.[A-Za-z0-9_.:-]+")


def _production_python_files() -> list[Path]:
    files = [path for root in PRODUCTION_ROOTS for path in root.rglob("*.py")]
    main_module = PROJECT_ROOT / "main.py"
    if main_module.is_file():
        files.append(main_module)
    return sorted(files)


def _is_legacy_package_name(name: str) -> bool:
    return name == "noisyne" or name.startswith("noisyne.")


def _dynamic_import_literal(node: ast.Call) -> str | None:
    function_name = None
    if isinstance(node.func, ast.Name):
        function_name = node.func.id
    elif isinstance(node.func, ast.Attribute):
        function_name = node.func.attr

    if function_name not in {"__import__", "import_module"} or not node.args:
        return None
    first_argument = node.args[0]
    if isinstance(first_argument, ast.Constant) and isinstance(first_argument.value, str):
        return first_argument.value
    return None


def test_production_has_no_legacy_noisyne_package_dependency() -> None:
    violations: list[str] = []

    assert not (PROJECT_ROOT / "noisyne").exists()

    for path in _production_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_legacy_package_name(alias.name):
                        violations.append(f"{path}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if _is_legacy_package_name(node.module):
                    violations.append(f"{path}:{node.lineno}: from {node.module}")
            elif isinstance(node, ast.Call):
                module_name = _dynamic_import_literal(node)
                if module_name and _is_legacy_package_name(module_name):
                    violations.append(f"{path}:{node.lineno}: dynamic import {module_name}")
            elif isinstance(node, ast.Subscript):
                value = node.value
                if not (
                    isinstance(value, ast.Attribute)
                    and isinstance(value.value, ast.Name)
                    and value.value.id == "sys"
                    and value.attr == "modules"
                ):
                    continue
                key = node.slice
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and _is_legacy_package_name(key.value)
                ):
                    violations.append(f"{path}:{node.lineno}: sys.modules[{key.value!r}]")

    assert violations == []


def test_distribution_exposes_only_canonical_cli() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["name"] == "phasenox"
    assert project["scripts"] == {"phasenox": "phasenox.cli:main"}


def test_canonical_public_classes_and_compatibility_aliases_are_frozen() -> None:
    assert PhasenoxService is CanonicalService
    assert CanonicalService.__module__ == "phasenox.application.phasenox_service"
    assert NoisyneService is ModuleNoisyneService is CanonicalService
    assert SoundBrainService is ModuleSoundBrainService is CanonicalService
    assert NoisyneV2Service is PhasenoxV2Service
    assert SoundBrainReport is PhasenoxReport
    assert NoisyneValidationFixtureProvider is PhasenoxValidationFixtureProvider


def test_application_root_remains_canonical_first(tmp_path: Path, monkeypatch) -> None:
    canonical_root = tmp_path / "canonical"
    noisyne_root = tmp_path / "legacy-noisyne"
    soundbrain_root = tmp_path / "legacy-soundbrain"
    monkeypatch.setenv("PHASENOX_ROOT", str(canonical_root))
    monkeypatch.setenv("NOISYNE_ROOT", str(noisyne_root))
    monkeypatch.setenv("SOUNDBRAIN_ROOT", str(soundbrain_root))

    with pytest.warns(RuntimeWarning, match="PHASENOX_ROOT=.*takes precedence"):
        assert get_application_root() == canonical_root.resolve()


def test_persistence_and_engine_compatibility_identities_are_frozen() -> None:
    assert DEFAULT_COLLECTION == "soundbrain"
    assert ChromaConfig().collection == "soundbrain"
    assert registry.get("noisyne") is registry.get("soundbrain")


def test_desktop_identity_and_migration_compatibility_are_frozen() -> None:
    assert DESKTOP_APPLICATION_ID == CANONICAL_DESKTOP_IDENTITY == "phasenox.desktop"
    assert LEGACY_DESKTOP_IDENTITY == "soundbrain.desktop"

    approved_legacy_files = {
        PROJECT_ROOT / "phasenox" / "ui" / "data_location.py",
    }
    active_legacy_files = {
        path
        for path in (PROJECT_ROOT / "phasenox" / "ui").rglob("*.py")
        if "soundbrain.desktop" in path.read_text(encoding="utf-8")
    }
    assert active_legacy_files == approved_legacy_files


def test_serialized_identity_allowlist_is_unchanged() -> None:
    discovered: set[str] = set()
    for path in (PROJECT_ROOT / "phasenox").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                discovered.update(SERIALIZED_IDENTIFIER_PATTERN.findall(node.value))

    assert discovered == EXPECTED_SERIALIZED_IDENTIFIERS


def test_brain_namespace_resolves_to_canonical_module_objects() -> None:
    canonical = importlib.import_module("phasenox.reference.models")
    legacy = importlib.import_module("brain.reference.models")
    brain_application = importlib.import_module("brain.application")

    assert legacy is canonical
    assert brain_application.PhasenoxService is CanonicalService
    assert brain_application.NoisyneService is CanonicalService
    assert brain_application.SoundBrainService is CanonicalService


def test_selected_current_facing_surfaces_use_only_phasenox_identity() -> None:
    for path in CURRENT_FACING_IDENTITY_FILES:
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in LEGACY_PRODUCT_TOKENS), path
        assert "PHASENOX" in text or "PHASENØX" in text


def test_freeze_document_records_the_canonical_and_compatibility_matrix() -> None:
    text = FREEZE_DOCUMENT.read_text(encoding="utf-8")

    for required in (
        "| Public brand | PHASENØX |",
        "| ASCII product identity | PHASENOX |",
        "| Python namespace | `phasenox` |",
        "| Canonical service module | `phasenox.application.phasenox_service` |",
        "| CLI | `phasenox` |",
        "| Canonical application-root environment variable | `PHASENOX_ROOT` |",
        "| Desktop application identifier | `phasenox.desktop` |",
        "The former `soundbrain.desktop` identity remains approved",
        "`brain.*`, resolving to the same canonical `phasenox.*` module objects",
        "| Persisted vector collection | `soundbrain` |",
        "| Engine compatibility keys | `noisyne`, `soundbrain` |",
        "| Repository identity | `N0ises/PHASENOX` |",
    ):
        assert required in text
