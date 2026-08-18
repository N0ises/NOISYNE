from __future__ import annotations

import os
import platform
import sys
from typing import Any

from .contracts import PerformanceEnvironment


def _safe_import(module_name: str) -> Any:
    try:
        return __import__(module_name)
    except Exception:  # noqa: BLE001
        return None


def _torch_version() -> str | None:
    torch = _safe_import("torch")
    if torch is None:
        return None
    try:
        return str(torch.__version__)
    except Exception:  # noqa: BLE001
        return None


def _onnxruntime_version_and_providers() -> tuple[str | None, list[str]]:
    ort = _safe_import("onnxruntime")
    if ort is None:
        return None, []
    try:
        version = str(ort.__version__)
    except Exception:  # noqa: BLE001
        version = None
    try:
        providers = list(ort.get_available_providers())
    except Exception:  # noqa: BLE001
        providers = []
    return version, providers


def _cpu_brand() -> str:
    brand = platform.processor()
    if brand and brand.strip():
        return brand.strip()
    return "unknown"


def _logical_cores() -> int | None:
    try:
        count = os.cpu_count()
        return count if count is not None else None
    except Exception:  # noqa: BLE001
        return None


def _total_ram_bytes() -> int | None:
    psutil = _safe_import("psutil")
    if psutil is None:
        return None
    try:
        return int(psutil.virtual_memory().total)
    except Exception:  # noqa: BLE001
        return None


def _gpu_info() -> tuple[bool, str | None, int | None, str | None]:
    torch = _safe_import("torch")
    if torch is None:
        return False, None, None, None
    try:
        available = bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        available = False

    name: str | None = None
    vram_bytes: int | None = None
    cuda_version: str | None = None

    if available:
        try:
            name = str(torch.cuda.get_device_name(0))
        except Exception:  # noqa: BLE001
            name = None
        try:
            vram_bytes = int(torch.cuda.get_device_properties(0).total_memory)
        except Exception:  # noqa: BLE001
            vram_bytes = None
        try:
            version = torch.version.cuda
            cuda_version = str(version) if version is not None else None
        except Exception:  # noqa: BLE001
            cuda_version = None

    return available, name, vram_bytes, cuda_version


def capture_environment() -> PerformanceEnvironment:
    """Return a truthful snapshot of the current benchmarking environment."""
    onnx_version, onnx_providers = _onnxruntime_version_and_providers()
    cuda_available, gpu_name, gpu_vram, cuda_version = _gpu_info()
    return PerformanceEnvironment(
        os_name=platform.system(),
        os_version=platform.release(),
        architecture=platform.machine() or "unknown",
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        cpu_brand=_cpu_brand(),
        logical_cores=_logical_cores(),
        total_ram_bytes=_total_ram_bytes(),
        gpu_name=gpu_name,
        gpu_total_vram_bytes=gpu_vram,
        cuda_available=cuda_available,
        cuda_version=cuda_version,
        torch_version=_torch_version(),
        onnxruntime_version=onnx_version,
        onnxruntime_providers=onnx_providers,
    )


__all__ = ["capture_environment"]
