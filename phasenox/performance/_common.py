from __future__ import annotations

from math import isfinite

PERFORMANCE_SCHEMA_VERSION = "1.0.0"


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_finite_number(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field_name} must be a number")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError(f"{field_name} must be a finite number")


def _require_non_negative(value: float, field_name: str) -> None:
    _require_finite_number(value, field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative")


def _require_non_negative_integer(value: int, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _require_string_list(values: list[str], field_name: str) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must contain non-empty strings")
