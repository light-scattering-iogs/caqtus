import sys
from abc import ABC
from types import SimpleNamespace
from typing import Any, Callable, Generic, TypeVar, ParamSpec, Iterable

import numpy

from experiment.session import ExperimentSession
from sequence.runtime import Shot

InputTypes = ParamSpec("InputTypes")
OutputType = TypeVar("OutputType")
OtherOutputType = TypeVar("OtherOutputType")


class ChainableImporter(Generic[InputTypes, OutputType], ABC):
    def __init__(self, func: Callable[InputTypes, OutputType]):
        self._func = func

    def __call__(self, *args: InputTypes) -> OutputType:
        return self._func(*args)

    def __or__(
        self, other: "ChainableImporter[[OutputType], OtherOutputType]"
    ) -> "ChainableImporterInputTypes, OtherOutputType]":
        def _chain(*args: InputTypes) -> OtherOutputType:
            return other(self(*args))

        if isinstance(other, ChainableImporter):
            return ChainableImporter(_chain)
        else:
            raise TypeError(f"Can only chain ChainableImporters, not {type(other)}")


def rename(old_name: str, new_name: str) -> ChainableImporter:
    def _rename(values: dict[str, Any]) -> dict[str, Any]:
        values[new_name] = values.pop(old_name, None)
        return values

    return ChainableImporter(_rename)


def apply(
    func: Callable[[Any], Any], args: str | Iterable[str], result: str
) -> ChainableImporter:
    if isinstance(args, str):
        args = [args]

    def _apply(values: dict[str, Any]) -> dict[str, Any]:
        values[result] = func(*[values[arg] for arg in args])
        return values

    return ChainableImporter(_apply)


def remove(*keys: str) -> ChainableImporter:
    def _remove(values: dict[str, Any]) -> dict[str, Any]:
        for key in keys:
            values.pop(key, None)
        return values

    return ChainableImporter(_remove)


def subtract(operand1: str, operand2: str, result: str) -> ChainableImporter:
    def _subtract(values: dict[str, Any]) -> dict[str, Any]:
        values[result] = values[operand1] - values[operand2]
        return values

    return ChainableImporter(_subtract)


def _break_namespaces(values: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in values.items():
        if isinstance(value, SimpleNamespace):
            result |= {
                f"{key}.{sub_key}": v
                for sub_key, v in _break_namespaces(value.__dict__).items()
            }
        elif isinstance(value, dict):
            result |= {
                f"{key}.{sub_key}": v
                for sub_key, v in _break_namespaces(value).items()
            }
        else:
            result[key] = value
    return result


def _import_parameters(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return shot.get_parameters(session)


def _import_scores(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    scores = shot.get_scores(session)
    return {f"{key}.score": value for key, value in scores.items()}


def _import_measures(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    result = {}
    data = shot.get_measures(session)
    for device, device_date in data.items():
        for key, value in device_date.items():
            result[f"{device}.{key}"] = value
    return result


def _import_time(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return {
        "start_time": shot.get_start_time(session),
        "end_time": shot.get_end_time(session),
    }


def _import_all(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return (
        _import_time(shot, session)
        | _import_scores(shot, session)
        | _import_parameters(shot, session)
        | _import_measures(shot, session)
    )


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


import_all = ChainableImporter(_import_all)
import_parameters = ChainableImporter(_import_parameters)
import_scores = ChainableImporter(_import_scores)
import_measures = ChainableImporter(_import_measures)
import_time = ChainableImporter(_import_time)
break_namespaces = ChainableImporter(_break_namespaces)
to_base_units = ChainableImporter(_to_base_units)
split_units = ChainableImporter(_split_units)
array_as_float = ChainableImporter(_array_as_float)
strip_units = ChainableImporter(_strip_units)
drop_heavy = ChainableImporter(_drop_heavy)
