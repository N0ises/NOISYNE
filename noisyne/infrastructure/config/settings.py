from __future__ import annotations

from noisyne.infrastructure.config.models import (
    AppConfig,
    AudioConfig,
    ChromaConfig,
    EmbeddingConfig,
    LLMConfig,
    LoggingConfig,
    ModelsConfig,
    RuntimeConfig,
)


DEFAULT_SETTINGS = AppConfig(
    runtime=RuntimeConfig(),
    logging=LoggingConfig(),
    audio=AudioConfig(),
    models=ModelsConfig(),
    llm=LLMConfig(),
    embedding=EmbeddingConfig(),
    chroma=ChromaConfig(),
)