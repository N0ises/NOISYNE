from __future__ import annotations

import importlib
import pickle
import subprocess
import sys
from importlib import resources


def test_legacy_modules_are_canonical_module_objects() -> None:
    module_names = (
        "application.noisyne_service",
        "memory.errors",
        "reference.models",
        "runtime.engine_registry",
    )

    for suffix in module_names:
        canonical = importlib.import_module(f"noisyne.{suffix}")
        legacy = importlib.import_module(f"brain.{suffix}")
        assert legacy is canonical
        assert legacy.__name__ == f"noisyne.{suffix}"


def test_representative_public_type_identity() -> None:
    from brain.application import NoisyneService as LegacyNoisyneService
    from brain.application import SoundBrainService as LegacySoundBrainService
    from brain.application.noisyne_service import AnalysisRequest as LegacyAnalysisRequest
    from brain.memory.errors import MemoryConfigurationError as LegacyMemoryConfigurationError
    from brain.reference.models import Severity as LegacySeverity

    from noisyne.application import NoisyneService, SoundBrainService
    from noisyne.application.noisyne_service import AnalysisRequest
    from noisyne.memory.errors import MemoryConfigurationError
    from noisyne.reference.models import Severity

    assert LegacyNoisyneService is NoisyneService
    assert LegacySoundBrainService is SoundBrainService is NoisyneService
    assert LegacyAnalysisRequest is AnalysisRequest
    assert LegacySeverity is Severity
    assert LegacyMemoryConfigurationError is MemoryConfigurationError


def test_legacy_first_import_order_preserves_identity() -> None:
    code = """
import importlib
legacy = importlib.import_module('brain.reference.models')
canonical = importlib.import_module('noisyne.reference.models')
assert legacy is canonical
assert legacy.Severity is canonical.Severity
assert legacy.__name__ == 'noisyne.reference.models'
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_legacy_pickle_module_path_resolves_to_canonical_type() -> None:
    from noisyne.reference.models import Severity

    canonical_payload = pickle.dumps(Severity.LOW, protocol=0)
    legacy_payload = canonical_payload.replace(
        b"cnoisyne.reference.models\nSeverity\n",
        b"cbrain.reference.models\nSeverity\n",
    )

    assert legacy_payload != canonical_payload
    assert pickle.loads(legacy_payload) is Severity.LOW


def test_legacy_resource_package_resolves_canonical_resources() -> None:
    canonical = resources.files("noisyne.infrastructure.config").joinpath("resources")
    legacy = resources.files("brain.infrastructure.config").joinpath("resources")

    for name in ("audio.yaml", "models.yaml", "runtime.yaml"):
        assert legacy.joinpath(name).read_bytes() == canonical.joinpath(name).read_bytes()


def test_root_imports_remain_lightweight() -> None:
    code = """
import sys
import noisyne
import brain
assert 'torch' not in sys.modules
assert 'transformers' not in sys.modules
assert 'sentence_transformers' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)
