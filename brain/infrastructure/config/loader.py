from __future__ import annotations

import os
import re
import sys
from importlib import resources
from pathlib import Path
from typing import Any

from brain.infrastructure.config.models import (
    AppConfig,
    AudioConfig,
    ChromaConfig,
    EmbeddingConfig,
    LLMConfig,
    LoggingConfig,
    ModelEntry,
    ModelsConfig,
    RuntimeConfig,
)
from brain.infrastructure.config.settings import DEFAULT_SETTINGS

try:
    import yaml
except (
    ImportError,
    ModuleNotFoundError,
):  # pragma: no cover - PyYAML is optional in some test envs
    yaml = None


_ENV_ROOT = "SOUNDBRAIN_ROOT"


def _application_root() -> Path:
    """Return the application root used to resolve relative config paths.

    Resolution order:

    1. The ``SOUNDBRAIN_ROOT`` environment variable, if set.
    2. The directory containing ``pyproject.toml`` or ``configs/`` when running
       from a source checkout.
    3. The parent directory of the installed ``brain`` package (e.g.
       ``site-packages`` for a wheel install).

    This keeps runtime paths stable regardless of the current working directory.
    """
    env_root = os.environ.get(_ENV_ROOT)
    if env_root:
        return Path(env_root).expanduser().resolve()

    config_module = sys.modules.get("brain.infrastructure.config")
    if config_module is None:
        raise RuntimeError(
            "Cannot determine SoundBrain application root: "
            "brain.infrastructure.config has not been imported."
        )
    config_file = getattr(config_module, "__file__", None)
    if config_file is None:
        raise RuntimeError(
            "Cannot determine SoundBrain application root from the packaged "
            f"configuration location. Set the {_ENV_ROOT} environment variable."
        )
    config_dir = Path(config_file).resolve().parent

    for parent in config_dir.parents:
        if (parent / "pyproject.toml").is_file() or (parent / "configs").is_dir():
            return parent

    # Installed wheel: the packaged config lives under
    # .../site-packages/brain/infrastructure/config. The parent of the ``brain``
    # package (.../site-packages or the project root) is the stable root.
    return config_dir.parents[2].parent


def _load_yaml(name: str) -> dict[str, Any]:
    """Load a packaged YAML resource, returning an empty dict if it is empty.

    Raises yaml.YAMLError if the file exists but contains invalid YAML so that
    configuration problems fail fast instead of silently falling back to defaults.
    """
    if yaml is None:
        raise RuntimeError("PyYAML is required to load SoundBrain configuration.")
    resource = resources.files("brain.infrastructure.config").joinpath(
        "resources", f"{name}.yaml"
    )
    if not resource.is_file():
        raise FileNotFoundError(
            f"Required SoundBrain configuration resource is missing: {name}.yaml"
        )
    text = resource.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def _deep_update(
    base: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    """Recursively merge overlay into base."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _expand_path(value: str | Path | None, root: Path) -> Path | None:
    """Resolve a config path relative to the application root."""
    if value is None:
        return None
    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    return (root / path).resolve()


def _model_entry(data: dict[str, Any] | None, default: ModelEntry) -> ModelEntry:
    if not data:
        return default
    entry = ModelEntry(
        name=data.get("name", default.name),
        backend=data.get("backend", default.backend),
        revision=data.get("revision", default.revision),
        trust_remote_code=data.get(
            "trust_remote_code",
            default.trust_remote_code,
        ),
    )
    if entry.trust_remote_code and not re.fullmatch(
        r"[0-9a-fA-F]{40}", entry.revision or ""
    ):
        raise ValueError(
            f"Model '{entry.name}' enables trust_remote_code but does not specify "
            "a 40-character immutable commit revision."
        )
    return entry


def load_settings() -> AppConfig:
    """Load packaged configuration and return a populated AppConfig.

    Missing configuration files fail fast so an installed release cannot
    silently run with defaults that differ from its declared configuration.
    """
    root = _application_root()

    merged: dict[str, Any] = {}
    for name in ("runtime", "models", "audio"):
        merged = _deep_update(merged, _load_yaml(name))

    runtime_data = merged.get("runtime", {})
    logging_data = merged.get("logging", {})
    llm_data = merged.get("llm", {})
    audio_data = merged.get("audio", {})
    models_data = merged.get("models", {})

    default_runtime = DEFAULT_SETTINGS.runtime
    default_logging = DEFAULT_SETTINGS.logging
    default_audio = DEFAULT_SETTINGS.audio
    default_models = DEFAULT_SETTINGS.models
    default_llm = DEFAULT_SETTINGS.llm

    text_embedding_entry = _model_entry(
        models_data.get("text_embedding"),
        default_models.text_embedding,
    )

    return AppConfig(
        runtime=RuntimeConfig(
            device=runtime_data.get("device", default_runtime.device),
            dtype=runtime_data.get("dtype", default_runtime.dtype),
            lazy_load=runtime_data.get("lazy_load", default_runtime.lazy_load),
            model_root=_expand_path(
                runtime_data.get("model_root", default_runtime.model_root),
                root,
            ),
            model_cache_dir=_expand_path(
                runtime_data.get("model_cache_dir", default_runtime.model_cache_dir),
                root,
            ),
            cache_dir=_expand_path(
                runtime_data.get("cache_dir", default_runtime.cache_dir),
                root,
            ),
            log_dir=_expand_path(
                runtime_data.get("log_dir", default_runtime.log_dir),
                root,
            ),
            report_dir=_expand_path(
                runtime_data.get("report_dir", default_runtime.report_dir),
                root,
            ),
        ),
        logging=LoggingConfig(
            level=logging_data.get("level", default_logging.level),
            format=logging_data.get("format", default_logging.format),
        ),
        audio=AudioConfig(
            sample_rate=audio_data.get("sample_rate", default_audio.sample_rate),
            clap_target_sample_rate=audio_data.get(
                "clap_target_sample_rate",
                default_audio.clap_target_sample_rate,
            ),
            max_duration_seconds=audio_data.get(
                "max_duration_seconds",
                default_audio.max_duration_seconds,
            ),
            n_fft=audio_data.get("n_fft", default_audio.n_fft),
            hop_length=audio_data.get("hop_length", default_audio.hop_length),
            n_mels=audio_data.get("n_mels", default_audio.n_mels),
            n_mfcc=audio_data.get("n_mfcc", default_audio.n_mfcc),
            n_chroma=audio_data.get("n_chroma", default_audio.n_chroma),
        ),
        models=ModelsConfig(
            clap=_model_entry(
                models_data.get("clap"),
                default_models.clap,
            ),
            qwen=_model_entry(
                models_data.get("qwen"),
                default_models.qwen,
            ),
            bge_reranker=_model_entry(
                models_data.get("bge_reranker"),
                default_models.bge_reranker,
            ),
            text_embedding=text_embedding_entry,
        ),
        llm=LLMConfig(
            provider=llm_data.get("provider", default_llm.provider),
            model=llm_data.get("model", default_llm.model),
            base_url=llm_data.get("base_url", default_llm.base_url),
            api_key=llm_data.get("api_key", default_llm.api_key),
            temperature=llm_data.get("temperature", default_llm.temperature),
            top_p=llm_data.get("top_p", default_llm.top_p),
            max_tokens=llm_data.get("max_tokens", default_llm.max_tokens),
        ),
        embedding=EmbeddingConfig(
            # Model names are kept as-is so ModelRepository can resolve
            # local folders under models/ or fall back to HuggingFace IDs.
            model_path=Path(text_embedding_entry.name),
            device=runtime_data.get(
                "embedding_device",
                DEFAULT_SETTINGS.embedding.device,
            ),
        ),
        chroma=ChromaConfig(
            path=_expand_path(
                runtime_data.get("chroma_path", DEFAULT_SETTINGS.chroma.path),
                root,
            ),
            collection=runtime_data.get(
                "chroma_collection",
                DEFAULT_SETTINGS.chroma.collection,
            ),
        ),
    )
