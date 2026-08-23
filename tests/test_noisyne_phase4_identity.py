from pathlib import Path
from types import SimpleNamespace

from phasenox.audio.analysis.report import AnalysisReport
from phasenox.audio.engineer.report import EngineerReport
from phasenox.infrastructure.config.models import ChromaConfig
from phasenox.memory.vector.config import DEFAULT_COLLECTION
from phasenox.prompt.prompt_builder import PromptBuilder
from phasenox.reasoning.prompts import SYSTEM_PROMPT
from phasenox.runtime.engine_registry import registry

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_current_generated_identity_is_noisyne():
    analysis = SimpleNamespace(
        tempo=120.0,
        pitch="A4",
        key="A minor",
        lufs=-14.0,
        peak=-1.0,
        rms=-18.0,
        dynamic_range=10.0,
        crest_factor=8.0,
        stereo_width=0.8,
        phase=0.9,
        spectral_centroid=1000.0,
        spectral_bandwidth=2000.0,
        spectral_rolloff=4000.0,
        spectral_flatness=0.1,
        spectral_contrast=10.0,
        zero_crossing_rate=0.05,
        mfcc=[],
        chroma=[],
        onset_count=0,
    )
    engineer = SimpleNamespace(score=100.0, strengths=[], issues=[], recommendations=[])

    assert "NØISYNE Analysis" in AnalysisReport().build(analysis)
    assert "NØISYNE Engineer" in EngineerReport().build(engineer)
    assert "You are NØISYNE." in PromptBuilder.SYSTEM_PROMPT
    assert "You are NØISYNE." in SYSTEM_PROMPT


def test_persisted_vector_identity_remains_legacy_compatible():
    assert DEFAULT_COLLECTION == "soundbrain"
    assert ChromaConfig().collection == "soundbrain"


def test_engine_identity_preserves_canonical_and_legacy_lookup():
    assert registry.get("noisyne") is registry.get("soundbrain")


def test_developer_scripts_do_not_require_soundbrain_repository_basename():
    for relative_path in ("scripts/ingest.py", "scripts/test_embedding.py"):
        text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "E:\\SoundBrain" not in text
        assert "Path(__file__).resolve().parent.parent" in text


def test_project_export_uses_canonical_identity():
    text = (PROJECT_ROOT / "scripts" / "export_project.py").read_text(encoding="utf-8")
    assert "NOISYNE PROJECT EXPORT" in text
    assert "SOUNDBRAIN PROJECT EXPORT" not in text
