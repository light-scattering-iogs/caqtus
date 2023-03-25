import typing
from abc import ABC
from types import SimpleNamespace
from typing import Any, Callable, Generic, TypeVar, ParamSpec, Iterable

import numpy
import pandas
from tqdm import tqdm

from experiment.session import ExperimentSession
from sequence.runtime import Sequence, Shot


def build_dataframe_from_sequences(
    sequences: Iterable[Sequence],
    importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session: ExperimentSession,
) -> pandas.DataFrame:
    """Constructs a pandas dataframe from multiple experiment sequences

    Args:
        sequences: The sequences to construct the dataframe from
        importer: A function that takes a shot and a session and returns a dictionary. The keys of the returned
        dictionary will be the columns of the dataframe.
        session: The session to use to read the shot data. It must be inactive.

    Returns:
        A pandas dataframe with the data from the shots. The dataframe will have a multi-index with the sequence path as
        the first level, the shot name as the second level and the shot index as the third level. The columns will be
        the keys of the dictionaries returned by the importer function.
    """

    with session.activate():
        shots = []
        for sequence in sequences:
            shots.extend(sequence.get_shots(session))

    return build_dataframe_from_shots(shots, importer, session)


def build_dataframe_from_sequence(
    sequence: Sequence,
    importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session: ExperimentSession,
) -> pandas.DataFrame:
    """Constructs a pandas dataframe from an experiment sequence

    Args:
        sequence: The shots to construct the dataframe from
        importer: A function that takes a shot and a session and returns a dictionary. The keys of the returned
        dictionary will be the columns of the dataframe.
        session: The session to use to read the shot data. It must be inactive.

    Returns:
        A pandas dataframe with the data from the shots. The dataframe will have a multi-index with the sequence path as
        the first level, the shot name as the second level and the shot index as the third level. The columns will be
        the keys of the dictionaries returned by the importer function.
    """

    with session.activate():
        shots = sequence.get_shots(session)

    return build_dataframe_from_shots(shots, importer, session)


def build_dataframe_from_shots(
    shots: typing.Sequence[Shot],
    importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session: ExperimentSession,
) -> pandas.DataFrame:
    """Constructs a pandas dataframe from a sequence of shot

    Args:
        shots: The shots to construct the dataframe from
        importer: A function that takes a shot and a session and returns a dictionary. The keys of the returned
        dictionary will be the columns of the dataframe.
        session: The session to use to read the shot data. It must be inactive.

    Returns:
        A pandas dataframe with the data from the shots. The dataframe will have a multi-index with the sequence path as
        the first level, the shot name as the second level and the shot index as the third level. The columns will be
        the keys of the dictionaries returned by the importer function.
    """

    def map_shot_to_row(shot):
        with session:
            return importer(shot, session)

    indices = [(str(shot.sequence.path), shot.index) for shot in shots]
    index = pandas.MultiIndex.from_tuples(indices, names=["sequence", "shot"])
    rows = list(tqdm(map(map_shot_to_row, shots), total=len(shots)))
    return pandas.DataFrame(rows, index=index)


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
        else:
            result[key] = value
    return result


def _import_parameters(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return shot.get_parameters(session)


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


import_all = ChainableImporter(_import_all)
break_namespaces = ChainableImporter(_break_namespaces)
to_base_units = ChainableImporter(_to_base_units)
split_units = ChainableImporter(_split_units)
array_as_float = ChainableImporter(_array_as_float)
strip_units = ChainableImporter(_strip_units)
