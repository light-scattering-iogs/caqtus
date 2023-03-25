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

