from __future__ import annotations

import numpy as np
import torch
import torchaudio
from transformers import (
    ClapAudioModelWithProjection,
    ClapModel,
    ClapProcessor,
)

from phasenox.audio.embeddings.base import AudioEmbeddingModel
from phasenox.audio.embeddings.models import EmbeddingCapability
from phasenox.audio.embeddings.tasks import EmbeddingTask
from phasenox.audio.io.models import AudioData
from phasenox.infrastructure.config import settings
from phasenox.runtime import ModelRuntime


class CLAPEmbedding(AudioEmbeddingModel):
    """
    Canonical CLAP audio embedding provider for NØISYNE.

    New code should use this class. The legacy ``CLAPAudioEmbeddingModel`` in
    ``phasenox.audio.intelligence.embeddings`` is kept for backward compatibility
    with existing callers but should not be used in new features.
    """

    # Model name is owned by configuration.
    MODEL_NAME = settings.models.clap.name

    def __init__(self, runtime: ModelRuntime | None = None) -> None:
        self._runtime = runtime or ModelRuntime.shared()

    @property
    def _audio_assets(self):
        return self._runtime.load(
            model_name=self.MODEL_NAME,
            model_cls=ClapAudioModelWithProjection,
            processor_cls=ClapProcessor,
        )

    @property
    def _text_assets(self):
        return self._runtime.load(
            model_name=self.MODEL_NAME,
            model_cls=ClapModel,
            processor_cls=ClapProcessor,
        )

    @property
    def name(self) -> str:

        return "clap"

    @property
    def dimension(self) -> int:

        return 512

    @property
    def capability(self) -> EmbeddingCapability:

        return EmbeddingCapability(
            backend="transformers",
            device=str(self._runtime.device),
        )

    @torch.inference_mode()
    def encode_audio(
        self,
        audio: AudioData,
        task: EmbeddingTask | None = None,
    ) -> np.ndarray:

        processor = self._audio_assets.processor

        model = self._audio_assets.model

        target_sample_rate = settings.audio.clap_target_sample_rate
        samples = audio.samples
        sample_rate = audio.metadata.sample_rate

        waveform = (
            samples.squeeze() if hasattr(samples, "squeeze") else np.asarray(samples).squeeze()
        )
        waveform = np.asarray(waveform, dtype=np.float32)

        # CLAP expects a mono signal regardless of input channel count.
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)

        if sample_rate != target_sample_rate:
            tensor = torch.tensor(waveform, dtype=torch.float32).unsqueeze(0)
            tensor = torchaudio.transforms.Resample(
                orig_freq=sample_rate,
                new_freq=target_sample_rate,
            )(tensor)
            waveform = tensor.squeeze(0).numpy()
            sample_rate = target_sample_rate

        samples = waveform

        inputs = processor(
            audio=samples,
            sampling_rate=sample_rate,
            return_tensors="pt",
        )

        inputs = {
            k: v.to(
                self._audio_assets.device,
                dtype=self._audio_assets.model.dtype,
            )
            for k, v in inputs.items()
        }

        outputs = model(**inputs)

        embedding = torch.nn.functional.normalize(
            outputs.audio_embeds,
            dim=-1,
        )

        return embedding.squeeze(0).float().cpu().numpy()

    @torch.inference_mode()
    def encode_text(
        self,
        text: str | list[str],
    ) -> np.ndarray:

        if isinstance(text, str):
            text = [text]

        processor = self._text_assets.processor

        model = self._text_assets.model

        inputs = processor(
            text=text,
            return_tensors="pt",
            padding=True,
        )

        inputs = {
            k: v.to(
                self._text_assets.device,
                dtype=self._text_assets.model.dtype,
            )
            for k, v in inputs.items()
        }

        outputs = model.get_text_features(**inputs)

        outputs = torch.nn.functional.normalize(
            outputs,
            dim=-1,
        )

        return outputs.squeeze(0).float().cpu().numpy()

    def encode(
        self,
        audio: AudioData,
        task: EmbeddingTask | None = None,
    ) -> np.ndarray:

        return self.encode_audio(
            audio,
            task=task,
        )
