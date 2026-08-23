from __future__ import annotations

from pathlib import Path


AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
}


class AudioScanner:

    def scan(
        self,
        directory: str | Path,
    ) -> list[Path]:

        directory = Path(directory)

        files: list[Path] = []

        for path in directory.rglob("*"):

            if (
                path.is_file()
                and path.suffix.lower() in AUDIO_EXTENSIONS
            ):
                files.append(path)

        files.sort()

        return files