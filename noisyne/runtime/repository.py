from __future__ import annotations

from pathlib import Path


class ModelRepository:
    """
    Resolves local model paths.

    Layout:

    models/
        clap-htsat-unfused/
        whisper-large-v3/
        ...
    """

    def __init__(self, root: str | Path = "models") -> None:
        self.root = Path(root).expanduser()

    def resolve(
        self,
        model_name: str,
    ) -> tuple[str, bool]:

        requested_path = Path(model_name).expanduser()
        if requested_path.is_dir():
            return str(requested_path.resolve()), True

        local_name = model_name.replace("\\", "/").rstrip("/").split("/")[-1]

        local_path = (self.root / local_name).resolve()

        if local_path.is_dir():
            return str(local_path), True

        return model_name, False
