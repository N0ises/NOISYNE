"""Desktop application boundary.

Qt presentation modules consume only the contracts and presentation state in
this package. Backend-specific imports belong in adapter implementations.
"""

from .branding import default_product_metadata
from .contracts import ProductMetadata

__all__ = ["ProductMetadata", "default_product_metadata"]

