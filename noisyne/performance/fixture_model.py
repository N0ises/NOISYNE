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

    The ONNX session uses all providers reported by the installed ONNX Runtime,
    which on a GPU-capable install will prefer CUDAExecutionProvider if it
    actually loads.
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


def _build_pytorch_cuda_inference_fn(model: Any) -> Callable[[np.ndarray], np.ndarray]:
    import torch

    model = model.cuda()
    model.eval()

    def infer(input_array: np.ndarray) -> np.ndarray:
        with torch.inference_mode():
            tensor = torch.from_numpy(input_array).float().cuda()
            output = model(tensor)
            result = output.cpu().numpy()
        torch.cuda.synchronize()
        return result

    return infer


def _build_onnx_cuda_inference_fn(session: Any) -> Callable[[np.ndarray], np.ndarray]:
    import torch

    input_name = session.get_inputs()[0].name

    def infer(input_array: np.ndarray) -> np.ndarray:
        result = session.run(None, {input_name: input_array.astype(np.float32)})[0]
        torch.cuda.synchronize()
        return result

    return infer


def _torch_cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


def _onnxruntime_cuda_available() -> bool:
    try:
        import onnxruntime

        return "CUDAExecutionProvider" in onnxruntime.get_available_providers()
    except Exception:  # noqa: BLE001
        return False


def _onnx_cuda_session_loaded(session: Any) -> bool:
    """Return True iff the session's active provider list contains CUDAExecutionProvider."""
    try:
        return "CUDAExecutionProvider" in session.get_providers()
    except Exception:  # noqa: BLE001
        return False


def build_fixture_runtimes_by_device(
    cache_dir: str = ".noisyne_performance_test_cache",
) -> dict[
    str,
    tuple[
        Callable[[np.ndarray], np.ndarray] | None,
        Callable[[np.ndarray], np.ndarray] | None,
        Any | None,
    ],
]:
    """Build PyTorch and ONNX fixture runtimes separated by target device.

    Returns a mapping ``device -> (pytorch_fn, onnx_fn, onnx_session)`` where
    ``device`` is ``"cpu"`` or ``"cuda"``.  A device entry is omitted if neither
    a PyTorch nor an ONNX runtime can be constructed for it.  The CUDA ONNX
    session is created with ``[CUDAExecutionProvider, CPUExecutionProvider]``;
    if CUDA fails to load, the active provider list will report CPU only and
    the caller can treat the session as a CPU fallback.
    """
    result: dict[
        str,
        tuple[
            Callable[[np.ndarray], np.ndarray] | None,
            Callable[[np.ndarray], np.ndarray] | None,
            Any | None,
        ],
    ] = {}
    if not _torch_available() or not _onnxruntime_available():
        return result

    os.makedirs(cache_dir, exist_ok=True)
    onnx_path = os.path.join(cache_dir, "fixture_model.onnx")
    export_fixture_onnx(onnx_path)

    # Build a fresh model for each device so device placement is stable and
    # callables remain independent.
    cpu_model = _build_torch_model()
    result["cpu"] = (
        _build_pytorch_inference_fn(cpu_model),
        _build_onnx_inference_fn(
            __import__("onnxruntime").InferenceSession(
                onnx_path,
                providers=["CPUExecutionProvider"],
            )
        ),
        None,
    )

    cuda_pytorch_fn: Callable[[np.ndarray], np.ndarray] | None = None
    if _torch_cuda_available():
        cuda_model = _build_torch_model()
        cuda_pytorch_fn = _build_pytorch_cuda_inference_fn(cuda_model)

    cuda_onnx_fn: Callable[[np.ndarray], np.ndarray] | None = None
    cuda_session: Any | None = None
    if _onnxruntime_cuda_available():
        import onnxruntime

        cuda_session = onnxruntime.InferenceSession(
            onnx_path,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        if _onnx_cuda_session_loaded(cuda_session):
            cuda_onnx_fn = _build_onnx_cuda_inference_fn(cuda_session)
        else:
            # CUDA provider is advertised but did not actually load; record
            # the session as a CPU fallback under a distinct key so tests can
            # distinguish advertised vs active CUDA.
            result["cuda_advertised_cpu_fallback"] = (
                None,
                _build_onnx_inference_fn(cuda_session),
                cuda_session,
            )

    if cuda_pytorch_fn is not None or cuda_onnx_fn is not None:
        result["cuda"] = (cuda_pytorch_fn, cuda_onnx_fn, cuda_session)

    return result


__all__ = [
    "build_fixture_runtimes",
    "build_fixture_runtimes_by_device",
    "export_fixture_onnx",
]
