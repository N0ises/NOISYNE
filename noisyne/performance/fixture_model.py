from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import numpy as np


def _torch_available() -> bool:
    try:
        import torch  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _onnxruntime_available() -> bool:
    try:
        import onnxruntime  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _onnx_package_available() -> bool:
    try:
        import onnx  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def _build_torch_model(seed: int = 42) -> Any:
    if not _torch_available():
        raise RuntimeError("PyTorch is not available; cannot build fixture model")
    import torch
    from torch import nn

    torch.manual_seed(seed)

    class TinyFixtureModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.linear1 = nn.Linear(64, 32)
            self.activation = nn.ReLU()
            self.linear2 = nn.Linear(32, 8)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.linear2(self.activation(self.linear1(x)))

    return TinyFixtureModel().eval()


def _build_pytorch_inference_fn(model: Any) -> Callable[[np.ndarray], np.ndarray]:
    import torch

    def infer(input_array: np.ndarray) -> np.ndarray:
        with torch.inference_mode():
            tensor = torch.from_numpy(input_array).float()
            output = model(tensor)
            return output.numpy()

    return infer


def _build_onnx_inference_fn(session: Any) -> Callable[[np.ndarray], np.ndarray]:
    def infer(input_array: np.ndarray) -> np.ndarray:
        input_name = session.get_inputs()[0].name
        return session.run(None, {input_name: input_array.astype(np.float32)})[0]

    return infer


def export_fixture_onnx(path: str, *, opset_version: int = 17, seed: int = 42) -> Any:
    """Export the tiny fixture model to ONNX and return the InferenceSession.

    Returns ``None`` if PyTorch, ONNX, or ONNX Runtime is unavailable.
    """
    if not _torch_available():
        return None
    if not _onnx_package_available():
        return None
    if not _onnxruntime_available():
        return None
    import onnxruntime
    import torch

    model = _build_torch_model(seed)
    dummy_input = torch.randn(1, 64)
    torch.onnx.export(
        model,
        dummy_input,
        path,
        dynamo=False,
        opset_version=opset_version,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "output": {0: "batch_size"},
        },
    )
    return onnxruntime.InferenceSession(
        path,
        providers=onnxruntime.get_available_providers(),
    )


def build_fixture_runtimes(
    cache_dir: str,
) -> tuple[
    Callable[[np.ndarray], np.ndarray] | None, Callable[[np.ndarray], np.ndarray] | None, Any | None
]:
    """Build PyTorch and ONNX inference callables for the tiny fixture model.

    Returns ``(pytorch_fn, onnx_fn, onnx_session)``.  Missing runtimes are ``None``.
    """
    pytorch_fn = None
    onnx_fn = None
    onnx_session = None

    if _torch_available():
        model = _build_torch_model()
        pytorch_fn = _build_pytorch_inference_fn(model)

    if _torch_available() and _onnxruntime_available():
        os.makedirs(cache_dir, exist_ok=True)
        onnx_path = os.path.join(cache_dir, "fixture_model.onnx")
        onnx_session = export_fixture_onnx(onnx_path)
        if onnx_session is not None:
            onnx_fn = _build_onnx_inference_fn(onnx_session)

    return pytorch_fn, onnx_fn, onnx_session


__all__ = [
    "build_fixture_runtimes",
    "export_fixture_onnx",
]
