from abc import ABC
from typing import Any, Callable, Generic, TypeVar, ParamSpec

import numpy
import pandas
from tqdm.notebook import tqdm

from experiment.session import ExperimentSession
from sequence.runtime import Sequence, Shot


# pint_pandas.PintType.ureg = ureg
# pint_pandas.PintType.ureg.default_format = "P~"
#
# tqdm.pandas()


def build_dataframe_from_sequence(
    sequence: Sequence,
    importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session: ExperimentSession,
) -> pandas.DataFrame:
    """Constructs a pandas dataframe from a sequence of shot

    Args:
        sequence: The sequence to construct the dataframe from
        importer: A function that takes a shot and a session and returns a dictionary. The keys of the dictionary will
        be the columns of the dataframe.
        session: The session to use to read the sequence data

    """
    with session.activate():
        shots = sequence.get_shots(session)

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


def _import_parameters(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return shot.get_parameters(session)


def _import_measures(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    result = {}
    data = shot.get_measures(session)
    for device, device_date in data.items():
        for key, value in device_date.items():
            result[f"{device}.{key}"] = value
    return result


def _import_all(shot: Shot, session: ExperimentSession) -> dict[str, Any]:
    return _import_parameters(shot, session) | _import_measures(shot, session)


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
to_base_units = ChainableImporter(_to_base_units)
split_units = ChainableImporter(_split_units)
array_as_float = ChainableImporter(_array_as_float)
strip_units = ChainableImporter(_strip_units)
