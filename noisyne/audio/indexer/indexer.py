from __future__ import annotations

from pathlib import Path

from noisyne.audio.catalog import AudioCatalog
from noisyne.audio.catalog.models import IndexedAudio
from noisyne.audio.pipeline import AudioPipeline

from .duplicates import DuplicateDetector
from .filters import AudioFilter
from .metadata import MetadataExtractor
from .progress import ProgressPrinter
from .scanner import AudioScanner


class AudioIndexer:

    def __init__(
        self,
        pipeline: AudioPipeline | None = None,
    ) -> None:

        self.pipeline = pipeline or AudioPipeline()

        self.scanner = AudioScanner()

        self.metadata = MetadataExtractor()

        self.duplicates = DuplicateDetector()

        self.progress = ProgressPrinter()

        self.filter = AudioFilter()

        self.catalog = AudioCatalog()

    def index_directory(
        self,
        directory: str | Path,
    ) -> None:

        files = self.scanner.scan(directory)

        total = len(files)

        hashes: set[str] = set()

        for index, audio_path in enumerate(files, start=1):

            if not self.filter.accept(audio_path):
                continue

            file_hash = self.duplicates.file_hash(audio_path)

            # Duplicate داخل همین اجرا
            if file_hash in hashes:
                continue

            hashes.add(file_hash)

            # قبلاً ایندکس شده؟
            if self.catalog.exists(file_hash):

                print(f"[SKIP] {audio_path.name}")

                continue

            metadata = self.metadata.extract(audio_path)

            self.progress.update(
                index=index,
                total=total,
                filename=audio_path.name,
            )

            self.pipeline.index(
                audio_path=audio_path,
                audio_id=file_hash,
                metadata=metadata,
                document=audio_path.stem,
            )

            self.catalog.add(
                IndexedAudio(
                    file_hash=file_hash,
                    path=str(audio_path),
                    modified_time=audio_path.stat().st_mtime,
                    embedding_model="clap",
                )
            )