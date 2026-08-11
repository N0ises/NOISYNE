DEFAULT_PROVIDER = "chroma"

DEFAULT_COLLECTION = "soundbrain"

DEFAULT_TOP_K = 5

from brain.infrastructure.config import get_application_root

PERSIST_DIRECTORY = str(get_application_root() / "data" / "vector_db")