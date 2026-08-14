from __future__ import annotations

"""
Legacy audio embedding models kept for backward compatibility.

This module predates the ``noisyne.audio.embeddings`` provider registry.
For new code, use the canonical provider:

    from noisyne.audio.embeddings.clap import CLAPEmbedding

CLAPAudioEmbeddingModel is preserved only because existing callers
(AudioIntelligenceAnalyzer, tests/test_intelligence.py) still import it.
Do not use it in new features.
"""

from abc import ABC, abstractmethod

import numpy as np
import torch
import torchaudio

from transformers import (
    ClapModel,
    ClapProcessor,
)

from noisyne.infrastructure.config import settings
from noisyne.runtime import ModelRuntime


class AudioEmbeddingModel(ABC):

    @abstractmethod
    def encode(
        self,
        audio,
    ) -> list[float]:
        ...


class CLAPAudioEmbeddingModel(
    AudioEmbeddingModel
):
    """
    Legacy CLAP audio embedding provider.

    Use ``noisyne.audio.embeddings.clap.CLAPEmbedding`` for new code.
    This class is preserved only for existing callers.
    """

    # Model name is owned by configuration; resolved by ModelRepository.
    MODEL_NAME = settings.models.clap.name

    TARGET_SAMPLE_RATE = 48000


    def __init__(
        self,
        device: str | None = None,
        runtime: ModelRuntime | None = None,
    ) -> None:


        self._runtime = runtime or (
            ModelRuntime(device=torch.device(device))
            if device is not None
            else ModelRuntime.shared()
        )

    @property
    def _assets(self):
        return self._runtime.load(
            model_name=self.MODEL_NAME,
            model_cls=ClapModel,
            processor_cls=ClapProcessor,
        )

    @property
    def device(self) -> str:
        return str(self._runtime.device)

    @property
    def processor(self):
        return self._assets.processor

    @property
    def model(self):
        return self._assets.model



    def _prepare_audio(
        self,
        samples,
        sample_rate: int,
    ):


        waveform = np.asarray(
            samples,
            dtype=np.float32,
        )


        if waveform.ndim > 1:

            waveform = np.mean(
                waveform,
                axis=1,
            )


        if sample_rate != self.TARGET_SAMPLE_RATE:

            tensor = torch.tensor(
                waveform,
                dtype=torch.float32,
            )


            tensor = tensor.unsqueeze(0)


            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate,
                new_freq=self.TARGET_SAMPLE_RATE,
            )


            tensor = resampler(
                tensor
            )


            waveform = (
                tensor
                .squeeze(0)
                .numpy()
            )


        return waveform



    def encode(
        self,
        audio,
    ) -> list[float]:


        waveform = self._prepare_audio(
            audio.samples,
            audio.metadata.sample_rate,
        )


        inputs = self.processor(
            audio=[
                waveform
            ],
            sampling_rate=self.TARGET_SAMPLE_RATE,
            return_tensors="pt",
        )


        inputs = {
            key: value.to(
                self.device,
                dtype=self._assets.dtype,
            )
            for key, value in inputs.items()
        }


        with torch.no_grad():

            embedding = (
                self.model.get_audio_features(
                    **inputs
                )
            )


        return (
            embedding
            .squeeze(0)
            .cpu()
            .tolist()
        )



    def encode_text(
        self,
        texts: list[str],
    ) -> list[list[float]]:


        inputs = self.processor(
            text=texts,
            return_tensors="pt",
            padding=True,
        )


        inputs = {
            key: value.to(
                self.device
            )
            for key, value in inputs.items()
        }


        with torch.no_grad():

            embeddings = (
                self.model.get_text_features(
                    **inputs
                )
            )


        return (
            embeddings
            .cpu()
            .tolist()
        )
