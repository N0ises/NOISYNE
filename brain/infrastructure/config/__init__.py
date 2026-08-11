from .loader import get_application_root, load_settings
from .settings import DEFAULT_SETTINGS

settings = load_settings()

__all__ = [
    "settings",
    "load_settings",
    "DEFAULT_SETTINGS",
    "get_application_root",
]