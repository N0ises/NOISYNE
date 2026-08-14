from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class LLMConfig:

    provider: str = "qwen"

    model: str = "local-model"

    base_url: str = "http://127.0.0.1:1234/v1"

    api_key: str = "lm-studio"

    temperature: float = 0.0

    top_p: float = 0.9

    max_tokens: int = 1024


@dataclass(slots=True)
class EmbeddingConfig:

    model_path: Path = Path("models/Qwen3-Embedding-0.6B")

    device: str = "auto"


@dataclass(slots=True)
class ChromaConfig:

    path: Path = Path("data/chroma")

    collection: str = "soundbrain"


@dataclass(slots=True)
class RuntimeConfig:

    device: str = "auto"

    dtype: str = "auto"

    lazy_load: bool = True

    # Root directory used by ModelRepository to resolve local model folders.
    model_root: Path = Path("models")

    model_cache_dir: Path = Path("data/cache/models")

    cache_dir: Path = Path("data/cache")

    log_dir: Path = Path("logs")

    report_dir: Path = Path("reports")


@dataclass(slots=True)
class LoggingConfig:

    level: str = "INFO"

    format: str = "text"


@dataclass(slots=True)
class AudioConfig:

    sample_rate: int = 48000

    clap_target_sample_rate: int = 48000

    max_duration_seconds: int = 300

    n_fft: int = 2048

    hop_length: int = 512

    n_mels: int = 128

    n_mfcc: int = 13

    n_chroma: int = 12


@dataclass(slots=True)
class ModelEntry:

    name: str

    backend: str = "transformers"

    revision: str | None = None

    trust_remote_code: bool = False


@dataclass(slots=True)
class ModelsConfig:

    clap: ModelEntry = field(default_factory=lambda: ModelEntry(name="clap-htsat-unfused"))

    qwen: ModelEntry = field(
        default_factory=lambda: ModelEntry(name="lmstudio-community/Qwen2.5-7B-Instruct")
    )

    bge_reranker: ModelEntry = field(default_factory=lambda: ModelEntry(name="bge-reranker-v2-m3"))

    text_embedding: ModelEntry = field(
        default_factory=lambda: ModelEntry(name="Qwen3-Embedding-0.6B")
    )


@dataclass(slots=True)
class AppConfig:

    runtime: RuntimeConfig

    logging: LoggingConfig

    audio: AudioConfig

    models: ModelsConfig

    llm: LLMConfig

    embedding: EmbeddingConfig

    chroma: ChromaConfig
