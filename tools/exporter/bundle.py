"""Clean output API for a single export run."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from .writer import write_json, write_text


@dataclass(frozen=True, slots=True)
class ExportArtifact:
    path: str
    bytes: int


class ExportBundle:
    """Writes and records every artifact generated during one export."""

    def __init__(self, directory: Path, project: Path, generated_at: str) -> None:
        self.directory = directory
        self.project = project
        self.generated_at = generated_at
        self._artifacts: list[ExportArtifact] = []

    @property
    def artifacts(self) -> tuple[ExportArtifact, ...]:
        return tuple(self._artifacts)

    def text(self, relative_path: str | Path, content: str) -> Path:
        output = self.directory / relative_path
        write_text(output, content)
        self._record(output)
        return output

    def json(self, relative_path: str | Path, content: object) -> Path:
        output = self.directory / relative_path
        write_json(output, content)
        self._record(output)
        return output

    def finalize(self) -> Path:
        """Write an auditable inventory after every regular artifact succeeds."""
        manifest = self.directory / "manifest.json"
        payload = {
            "format": "ChatGPT Export V2",
            "product": "NOISYNE",
            "distribution": "phasenox",
            "project": str(self.project),
            "git_commit": self._git_value("rev-parse", "HEAD"),
            "git_branch": self._git_value("branch", "--show-current"),
            "python_version": platform.python_version(),
            "os": platform.platform(),
            "generated_at": self.generated_at,
            "artifact_count": len(self._artifacts),
            "artifacts": [asdict(item) for item in self._artifacts],
        }
        write_json(manifest, payload)
        self._record(manifest)
        return manifest

    def _git_value(self, *args: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(self.project), *args],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout.strip()

    def _record(self, output: Path) -> None:
        relative = output.relative_to(self.directory).as_posix()
        artifact = ExportArtifact(path=relative, bytes=output.stat().st_size)
        self._artifacts = [item for item in self._artifacts if item.path != relative]
        self._artifacts.append(artifact)
