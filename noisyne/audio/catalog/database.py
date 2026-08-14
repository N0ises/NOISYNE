from __future__ import annotations

import sqlite3
from pathlib import Path

from noisyne.infrastructure.config import get_application_root


DATABASE_PATH = get_application_root() / "data" / "index.db"


class CatalogDatabase:

    def __init__(self) -> None:

        DATABASE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.connection = sqlite3.connect(
            DATABASE_PATH,
        )

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS indexed_audio(

                file_hash TEXT PRIMARY KEY,

                path TEXT NOT NULL,

                modified_time REAL NOT NULL,

                embedding_model TEXT NOT NULL
            )
            """
        )

        self.connection.commit()