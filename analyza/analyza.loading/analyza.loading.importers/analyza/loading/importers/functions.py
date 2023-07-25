import sys
from types import SimpleNamespace
from typing import (
    Any,
    Callable,
    TypeVar,
    ParamSpec,
    Iterable,
    Mapping,
)

import numpy
from benedict import benedict

from parameter_types import Parameter
from .chainable_function import ChainableFunction

P = ParamSpec("P")
S = TypeVar("S")
T = TypeVar("T")

K = TypeVar("K")
V = TypeVar("V")


class RenameFunction(ChainableFunction[[Mapping[K, V]], dict[K, V]]):
    """Renames a key in a dictionary."""

    def __init__(self, old_label: K, new_label: K):
        def _rename(values: Mapping[K, V]) -> dict[K, V]:
            result = dict(values)
            if old_label in result:
                result[new_label] = result.pop(old_label)
            return result

        super().__init__(_rename)


rename = RenameFunction


def apply(
    func: Callable[[Any], Any], result: str, args: str | Iterable[str]
) -> ChainableFunction:
    if isinstance(args, str):
        args = [args]

    def _apply(values: dict[str, Any]) -> dict[str, Any]:
        values[result] = func(*[values[arg] for arg in args])
        return values

    return ChainableFunction(_apply)


def remove(*keys: str) -> ChainableFunction:
    def _remove(values: dict[str, Any]) -> dict[str, Any]:
        for key in keys:
            values.pop(key, None)
        return values

    return ChainableFunction(_remove)


def subtract(operand1: str, operand2: str, result: str) -> ChainableFunction:
    def _subtract(values: dict[str, Any]) -> dict[str, Any]:
        values[result] = values[operand1] - values[operand2]
        return values

    return ChainableFunction(_subtract)


def _break_namespaces(values: dict[Any, Parameter]) -> dict[str, Parameter]:
    result = {}
    for key, value in values.items():
        if isinstance(value, SimpleNamespace):
            result |= {
                f"{key}.{sub_key}": v
                for sub_key, v in _break_namespaces(value.__dict__).items()
            }
        elif isinstance(value, benedict):
            result |= {
                f"{key}.{sub_key}": v for sub_key, v in _break_namespaces(value).items()
            }
        else:
            result[key] = value
    return result


def _to_base_units(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.to_base_units() if hasattr(value, "to_base_units") else value
        for key, value in values.items()
    }


def _split_units(values: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in values.items():
        if hasattr(value, "magnitude"):
            result[key] = value.magnitude
            result[f"{key}.units"] = value.units
        else:
            result[key] = value
    return result


def _strip_units(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.magnitude if hasattr(value, "magnitude") else value
        for key, value in values.items()
    }


def _array_as_float(values: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in values.items():
        if isinstance(value, numpy.ndarray):
            result[key] = value.astype(float)
        else:
            result[key] = value
    return result


def _drop_heavy(values: dict[str, Any], limit: float) -> dict[str, Any]:
    """Drop values that are heavier than the given limit in bytes."""

    return {key: value for key, value in values.items() if sys.getsizeof(value) < limit}


break_namespaces = ChainableFunction(_break_namespaces)
to_base_units = ChainableFunction(_to_base_units)
split_units = ChainableFunction(_split_units)
array_as_float = ChainableFunction(_array_as_float)
strip_units = ChainableFunction(_strip_units)
drop_heavy = ChainableFunction(_drop_heavy)
