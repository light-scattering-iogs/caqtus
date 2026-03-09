from __future__ import annotations

from typing import Any

from typing_extensions import TypeIs

type JSON = JsonDict | JsonList | str | int | float | bool | None
type JsonDict = dict[str, JSON]
type JsonList = list[JSON]


def is_valid_json_dict(data: Any) -> TypeIs[JsonDict]:
    if not isinstance(data, dict):
        return False
    valid_keys = all(isinstance(key, str) for key in data.keys())
    valid_values = all(is_valid_json(value) for value in data.values())
    return valid_keys and valid_values


def is_valid_json_list(data: Any) -> TypeIs[JsonList]:
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
