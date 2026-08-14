DEFAULT_PROVIDER = "chroma"

# Stable persisted compatibility identifier. Renaming this collection would
# orphan existing vector data, so canonical and legacy runtimes share it.
DEFAULT_COLLECTION = "soundbrain"

DEFAULT_TOP_K = 5

from noisyne.infrastructure.config import get_application_root

PERSIST_DIRECTORY = str(get_application_root() / "data" / "vector_db")
