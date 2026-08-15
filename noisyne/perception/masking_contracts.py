from __future__ import annotations

from dataclasses import dataclass

from ._serialization import JsonContract
from .common import _require_identifier

SIMULTANEOUS_MASKING_METHOD_ID = "noisyne.relative_simultaneous_masking_foundation"
SIMULTANEOUS_MASKING_METHOD_VERSION = "1.0.0"
SIMULTANEOUS_MASKING_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class RelativeMaskingPairContext(JsonContract):
    """Caller declarations required to compare separate masker and target signals."""

    gain_relationship_reference: str
    alignment_reference: str
    masker_source_id: str | None = None
    target_source_id: str | None = None
    alignment_policy: str = "sample_synchronous_equal_length"
    channel_policy: str = "matched_channels_independent"
    level_basis: str = "common_digital_gain_uncalibrated"
    schema_version: str = SIMULTANEOUS_MASKING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_identifier(self.gain_relationship_reference, "gain_relationship_reference")
        _require_identifier(self.alignment_reference, "alignment_reference")
        if self.masker_source_id is not None:
            _require_identifier(self.masker_source_id, "masker_source_id")
        if self.target_source_id is not None:
            _require_identifier(self.target_source_id, "target_source_id")
        if self.alignment_policy != "sample_synchronous_equal_length":
            raise ValueError(
                "only sample_synchronous_equal_length alignment is supported in version 1.0.0"
            )
        if self.channel_policy != "matched_channels_independent":
            raise ValueError(
                "only matched_channels_independent channels are supported in version 1.0.0"
            )
        if self.level_basis != "common_digital_gain_uncalibrated":
            raise ValueError(
                "only common_digital_gain_uncalibrated level basis is supported in version 1.0.0"
            )
        if self.schema_version != SIMULTANEOUS_MASKING_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SIMULTANEOUS_MASKING_SCHEMA_VERSION}")
