from __future__ import annotations

from typing import TypeAlias, Any

from typing_extensions import TypeIs

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None


def is_valid_json_dict(data: Any) -> TypeIs[dict[str, JSON]]:
    if not isinstance(data, dict):
        return False
    valid_keys = all(isinstance(key, str) for key in data.keys())
    valid_values = all(is_valid_json(value) for value in data.values())
    return valid_keys and valid_values


def is_valid_json_list(data: Any) -> TypeIs[list[JSON]]:
    if not isinstance(data, list):
        return False
    return all(is_valid_json(value) for value in data)


def is_valid_json(data) -> TypeIs[JSON]:
    if isinstance(data, dict):
        return is_valid_json_dict(data)
    elif isinstance(data, list):
        return is_valid_json_list(data)
    elif data is None:
        return True
    elif isinstance(data, (str, int, float, bool)):
        return True
    else:
        return False
