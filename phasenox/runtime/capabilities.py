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
# V1 PHASENOX capabilities
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
        name="frequency_masking_foundation",
        description=(
            "Deterministic pairwise common-gain relative simultaneous-excitation evidence"
        ),
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Existing NumPy auditory frontend; caller-declared sample alignment and common "
            "digital gain relationship. No absolute threshold or full-mix source attribution."
        ),
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="perceptual_descriptors_foundation",
        description="Scientific descriptor taxonomy and truthful executable-state foundation",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Lightweight contracts; standardized descriptors remain unavailable until their "
            "complete prerequisite models and validation materials exist."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="brightness_correlate",
        description="Power-spectral-centroid correlate of timbral brightness in hertz",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Existing NumPy auditory frontend and positive spectral power; no SPL calibration. "
            "Not a universal perceived-brightness score."
        ),
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="playback_profile_foundation",
        description="Versioned playback transfer identity, provenance, and evidence contracts",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Caller-supplied, versioned measurement/reference/user evidence with explicit "
            "acoustic scope and normalization. No generic device-category presets."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="playback_linear_transfer",
        description="Deterministic channel-preserving transfer by explicit real FIR convolution",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Validated AudioData and caller-supplied float64 read-only FIR at the exact audio "
            "sample rate. No clipping, normalization, resampling, downmix, or nonlinear model."
        ),
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="translation_evidence_foundation",
        description="Deterministic objective evidence for an explicit playback FIR transfer",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Sprint 2/5 analysis and an explicit Sprint 6 impulse-response transfer. Reports "
            "brightness-correlate, ERB-power, programme-energy, and sample-peak changes only."
        ),
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="policy_conditioned_translation_risk",
        description="Boolean evaluation of explicit provenance-backed translation criteria",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "A versioned caller/project/reference/validated-model policy with dimension- and "
            "unit-matched thresholds. No universal thresholds, normalized score, or aggregation."
        ),
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="perceptual_context_foundation",
        description="Provenance-backed literal context claims and deterministic conflict resolution",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Explicit caller/project/workflow/specification declarations or fully described "
            "listening-SPL measurements. No classification, inference, profiling, or DSP."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="context_policy_binding",
        description="Exact deterministic selection of supplied translation-risk policies",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "A resolved conflict-free context, explicit versioned binding, and exact supplied "
            "Sprint 7 policy identity/version. No policy or threshold generation."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="perceptual_reference_foundation",
        description="Stable reference identity, provenance, and evidence transport contracts",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Caller-supplied logical reference identity and explicit comparison mode. References "
            "are examples, not ground truth or quality targets."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="reference_objective_comparison",
        description="Whole-programme objective source-minus-reference evidence",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Validated AudioData and existing Sprint 2/5 analysis. ERB comparison requires exact "
            "channel and band compatibility; no temporal alignment or aggregate match score."
        ),
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="reference_embedding_contract",
        description="Identified embedding-provider transport and raw cosine comparison contract",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Exact provider/model/checkpoint/preprocessing identity and finite runtime vectors. "
            "No live provider, model asset, or embedding is bundled by this capability."
        ),
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="perceptual_mix_intelligence_foundation",
        description="Structured issues from explicit policy criteria and precomputed evidence",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Caller-supplied versioned policy, declared priorities, and supported Sprint 4/7/8/9 "
            "evidence. No universal thresholds, quality score, recommendations, DSP, or LLM."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="mix_policy_evaluation",
        description="Deterministic unit-safe evaluation of declared mix issue criteria",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Exact evidence source/dimension and unit or scale match; priority is policy-declared."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="perceptual_reasoning_foundation",
        description="Grounded explanations rendered from validated Sprint 10 facts",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "A valid MixIntelligenceResult and an available constrained provider. The "
            "deterministic provider is offline; no live model is required."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="grounded_reasoning_validation",
        description="Deterministic fact, issue, criterion, template, and cross-reference validation",
        status=CapabilityStatus.IMPLEMENTED,
        requirements=(
            "Provider output must select whitelisted fact IDs and approved templates; free-form "
            "provider text is rejected."
        ),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="deterministic_reasoning",
        description="Offline canonical explanation and neutral review-suggestion rendering",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Validated Sprint 10 triggered issues; no DSP, RAG, memory, or LLM.",
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
        description="V1 PhasenoxService unified entry point",
        status=CapabilityStatus.PRODUCTION,
        requirements="All deterministic subsystems wired through PhasenoxService",
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

registry.register(
    Capability(
        name="knowledge_memory_foundation",
        description="Sprint 13 deterministic provenance-preserving memory/knowledge taxonomy and contracts",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Sprint 13 contracts and backend-neutral storage protocol",
        dependencies=(),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="personalization_foundation",
        description="Sprint 13 bounded personalization policy with explicit allowed/prohibited effects",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Sprint 13 PersonalizationPolicy contract",
        dependencies=(),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="knowledge_retrieval_contract",
        description="Sprint 13 backend-neutral knowledge retrieval contract with explicit score semantics",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Sprint 13 KnowledgeQuery/KnowledgeRetrievalResult contracts",
        dependencies=(),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="performance_benchmark_foundation",
        description="Sprint 14 truthful performance baseline and benchmark contract foundation",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Sprint 14 performance contracts, environment snapshot, and benchmark methodology",
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="runtime_selection_foundation",
        description="Sprint 14 deterministic runtime selection with equivalence-gated optimization",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Sprint 14 RuntimeSelectionPolicy/RuntimeSelectionResult and equivalence validation",
        dependencies=("numpy",),
        tested_in_freeze=False,
    )
)

registry.register(
    Capability(
        name="onnx_runtime_optimization",
        description="Sprint 14 ONNX Runtime evaluation boundary for PyTorch model optimization candidates",
        status=CapabilityStatus.IMPLEMENTED,
        requirements="Optional onnxruntime; tiny fixture model export and equivalence comparison only",
        dependencies=("onnxruntime",),
        reason_unavailable="Production ONNX export not attempted; only framework-level fixture evaluation exists",
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
