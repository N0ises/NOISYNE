from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CapabilityStatus(str, Enum):
    PLANNED = "planned"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


@dataclass(frozen=True, slots=True)
class Capability:
    """
    Describes one runtime capability.
    """

    name: str
    description: str
    status: CapabilityStatus
    requirements: str = ""
    dependencies: tuple[str, ...] = ()
    reason_unavailable: str | None = None
    tested_in_freeze: bool = False


class CapabilityRegistry:
    """
    Registry of Runtime capabilities.

    This registry is intentionally independent from ModelRuntime.
    Runtime will consume it in the next step.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.name] = capability

    def unregister(self, name: str) -> None:
        self._capabilities.pop(name, None)

    def exists(self, name: str) -> bool:
        return name in self._capabilities

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def all(self) -> tuple[Capability, ...]:
        return tuple(
            sorted(
                self._capabilities.values(),
                key=lambda capability: capability.name,
            )
        )

    def names(self) -> tuple[str, ...]:
        return tuple(capability.name for capability in self.all())

    def clear(self) -> None:
        self._capabilities.clear()

    def __contains__(self, name: str) -> bool:
        return self.exists(name)

    def __len__(self) -> int:
        return len(self._capabilities)

    def __iter__(self):
        return iter(self.all())


registry = CapabilityRegistry()

registry.register(
    Capability(
        name="runtime",
        description="Shared model runtime",
        status=CapabilityStatus.PRODUCTION,
    )
)

registry.register(
    Capability(
        name="model_loading",
        description="Lazy model loading",
        status=CapabilityStatus.PRODUCTION,
    )
)

registry.register(
    Capability(
        name="model_cache",
        description="Runtime cache",
        status=CapabilityStatus.PRODUCTION,
    )
)

registry.register(
    Capability(
        name="repository",
        description="Model repository resolution",
        status=CapabilityStatus.PRODUCTION,
    )
)

registry.register(
    Capability(
        name="transformers_backend",
        description="Transformers backend strategy",
        status=CapabilityStatus.PRODUCTION,
    )
)

registry.register(
    Capability(
        name="sentence_transformers_backend",
        description="SentenceTransformers backend strategy",
        status=CapabilityStatus.PRODUCTION,
    )
)

# ---------------------------------------------------------------------------
# V1 NØISYNE capabilities
# ---------------------------------------------------------------------------

registry.register(
    Capability(
        name="audio_loading",
        description="Load and validate audio files via AudioIOService",
        status=CapabilityStatus.PRODUCTION,
        requirements="soundfile, librosa, numpy",
        dependencies=("soundfile", "librosa", "numpy"),
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="dsp_analysis",
        description="Deterministic DSP analysis (loudness, spectrum, dynamics, stereo, tempo, key)",
        status=CapabilityStatus.PRODUCTION,
        requirements="librosa, pyloudnorm, numpy, scipy",
        dependencies=("librosa", "pyloudnorm", "numpy", "scipy"),
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="auditory_frontend",
        description="Deterministic channel-preserving spectral and ERB-rate frontend",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Validated AudioData and NumPy; no model assets or calibration required",
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="loudness_foundation",
        description="Explicit acoustic calibration and loudness evidence foundation",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Existing NumPy/pyloudnorm dependencies; explicit calibration for pressure. "
            "No psychoacoustic loudness algorithm is included."
        ),
        dependencies=("numpy", "pyloudnorm"),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="audio_context",
        description="Rule-based audio context and source classification (full mix vs stem, delivery target)",
        status=CapabilityStatus.PRODUCTION,
        requirements="Deterministic rules over AudioContext features",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="engineering_analysis",
        description="Engineering rule engine that produces scores, issues, and recommendations",
        status=CapabilityStatus.PRODUCTION,
        requirements="Deterministic rule engine; no external models",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="clap_embedding",
        description="CLAP-based audio-text semantic embeddings",
        status=CapabilityStatus.VERIFIED,
        requirements="Local CLAP model folder or HuggingFace download; transformers, torch, torchaudio",
        dependencies=("transformers", "torch", "torchaudio", "local CLAP model"),
        reason_unavailable="Model is not bundled with the wheel; must be present at runtime model_root",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="reference_comparison",
        description="Reference versus current mix comparison and reasoned report",
        status=CapabilityStatus.PRODUCTION,
        requirements="Deterministic metric comparator; optional reasoning",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="rag_retrieval",
        description="RAG document retrieval for knowledge-backed answers",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="chromadb, sentence-transformers/BGE, configured corpus",
        dependencies=("chromadb", "sentence-transformers", "BGE reranker model"),
        reason_unavailable="Known V2-preflight issues: score=1-distance under squared-L2, duplicate ids on re-ingest, CWD-relative persistence, redundant retrieve/rerank",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="llm_reasoning",
        description="LLM-based reasoning over analysis and context",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="OpenAI-compatible LLM endpoint (default LM Studio local server)",
        dependencies=("openai", "accessible LLM provider"),
        reason_unavailable="Default provider points to 127.0.0.1:1234; no bundled LLM model",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="report_generation",
        description="Structured JSON report generation",
        status=CapabilityStatus.PRODUCTION,
        requirements="Pydantic report models; deterministic JSON export. Reference comparison additionally emits Markdown via ReferenceReportBuilder.",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="service_facade",
        description="V1 NoisyneService unified entry point",
        status=CapabilityStatus.PRODUCTION,
        requirements="All deterministic subsystems wired through NoisyneService",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="engine_registry",
        description="Named engine registry for routing runtime workflows",
        status=CapabilityStatus.PRODUCTION,
        requirements="In-memory registry; no external dependencies",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="orchestration",
        description="Planner/Router/Executor orchestration layer",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="In-memory orchestration; not exercised by V1 CLI freeze path",
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="audio_intelligence",
        description="Sprint 4+ semantic audio intelligence",
        status=CapabilityStatus.PLANNED,
        requirements="Broader semantic audio tasks beyond CLAP embeddings",
        reason_unavailable="Semantic embeddings are verified, but broader audio intelligence remains V2 scope",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="mix_intelligence",
        description="Sprint 5+ mix-aware engineering intelligence",
        status=CapabilityStatus.PRODUCTION,
        requirements="Deterministic mix analysis, priority, root cause, processing chain",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="plugin_intelligence",
        description="Sprint 6+ plugin and preset recommendation",
        status=CapabilityStatus.PRODUCTION,
        requirements="Deterministic plugin taxonomy and parameter generation",
        tested_in_freeze=True,
    )
)

registry.register(
    Capability(
        name="memory_learning",
        description="Sprint 7+ long-term memory and continuous learning",
        status=CapabilityStatus.PLANNED,
        requirements="Persistent user/memory configuration and learning loop",
        reason_unavailable="Not implemented for V1; empty-profile fallback bug documented as V2-preflight blocker",
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="daw_integration",
        description="Sprint 8+ DAW plugin and automation integration",
        status=CapabilityStatus.PLANNED,
        requirements="DAW-specific adapters and automation APIs",
        reason_unavailable="No runtime DAW integration implemented in V1",
        tested_in_freeze=False,
    )
)

__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CapabilityStatus",
    "registry",
]


if __name__ == "__main__":
    for capability in registry:
        print(f"{capability.name}: {capability.status.value}")
