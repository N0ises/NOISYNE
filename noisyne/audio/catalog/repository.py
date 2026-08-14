from __future__ import annotations

from .database import CatalogDatabase
from .models import IndexedAudio


class AudioCatalog:

    def __init__(self) -> None:

        self.db = CatalogDatabase()

    def exists(
        self,
        file_hash: str,
    ) -> bool:

        row = self.db.connection.execute(

            "SELECT 1 FROM indexed_audio WHERE file_hash=?",

            (file_hash,),

        ).fetchone()

        return row is not None

    def add(
        self,
        audio: IndexedAudio,
    ) -> None:

        self.db.connection.execute(

            """
            INSERT OR REPLACE INTO indexed_audio

            VALUES(?,?,?,?)
            """,

            (
                audio.file_hash,
                audio.path,
                audio.modified_time,
                audio.embedding_model,
            ),

        )

        self.db.connection.commit()