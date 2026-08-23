from __future__ import annotations

from functools import lru_cache

import torch


class DeviceManager:
    """
    Shared device manager for every AI model.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def detect() -> torch.device:

        if torch.cuda.is_available():
            return torch.device("cuda")

        if (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            return torch.device("mps")

        return torch.device("cpu")