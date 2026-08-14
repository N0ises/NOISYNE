from __future__ import annotations

import types
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any, Self, Union, get_args, get_origin, get_type_hints

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class JsonContract:
    """Mixin for deterministic, JSON-compatible dataclass serialization."""

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a JSON-compatible mapping with enum values encoded as strings."""
        encoded = _encode(self)
        if not isinstance(encoded, dict):  # pragma: no cover - defensive contract guard
            raise TypeError("Contract serialization must produce a mapping")
        return encoded

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Reconstruct a contract from its serialized mapping."""
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__} data must be a mapping")
        return _decode_dataclass(cls, data)


def _encode(value: Any) -> JsonValue:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _encode(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, list | tuple):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("JSON contract mapping keys must be strings")
        return {key: _encode(item) for key, item in value.items()}
    if value is None or isinstance(value, str | int | float | bool):
        return value
    raise TypeError(f"Unsupported contract value: {type(value).__name__}")


def _decode_dataclass[ContractT: JsonContract](
    cls: type[ContractT], data: dict[str, Any]
) -> ContractT:
    if not all(isinstance(key, str) for key in data):
        raise TypeError(f"Serialized {cls.__name__} field names must be strings")
    field_names = {item.name for item in fields(cls)}
    unknown = sorted(set(data) - field_names)
    if unknown:
        raise ValueError(f"Unknown {cls.__name__} field(s): {', '.join(unknown)}")

    hints = get_type_hints(cls)
    values = {
        item.name: _decode(hints[item.name], data[item.name])
        for item in fields(cls)
        if item.name in data
    }
    return cls(**values)


def _decode(annotation: Any, value: Any) -> Any:
    origin = get_origin(annotation)
    arguments = get_args(annotation)

    if annotation is Any:
        return value

    if origin in (types.UnionType, Union):
        if value is None and type(None) in arguments:
            return None
        for candidate in arguments:
            if candidate is type(None):
                continue
            try:
                return _decode(candidate, value)
            except (TypeError, ValueError):
                continue
        expected = " | ".join(_annotation_name(candidate) for candidate in arguments)
        raise TypeError(f"Serialized value does not match union {expected}")

    if value is None:
        raise TypeError(f"Serialized {_annotation_name(annotation)} field must not be null")

    if origin is list:
        if not isinstance(value, list):
            raise TypeError("Serialized list field must be a list")
        item_type = arguments[0] if arguments else Any
        return [_decode(item_type, item) for item in value]

    if origin is dict:
        if not isinstance(value, dict):
            raise TypeError("Serialized mapping field must be a mapping")
        key_type, value_type = arguments if arguments else (str, Any)
        return {_decode(key_type, key): _decode(value_type, item) for key, item in value.items()}

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(value)

    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, dict):
            raise TypeError(f"Serialized {annotation.__name__} must be a mapping")
        return _decode_dataclass(annotation, value)

    if annotation is bool:
        if type(value) is not bool:
            raise TypeError("Serialized bool field must be a bool")
        return value
    if annotation is int:
        if type(value) is not int:
            raise TypeError("Serialized int field must be an int")
        return value
    if annotation is float:
        if type(value) is not float:
            raise TypeError("Serialized float field must be a float")
        return value
    if annotation is str:
        if type(value) is not str:
            raise TypeError("Serialized str field must be a string")
        return value

    raise TypeError(f"Unsupported serialized annotation: {annotation!r}")


def _annotation_name(annotation: Any) -> str:
    return getattr(annotation, "__name__", repr(annotation))
