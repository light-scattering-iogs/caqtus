import typing
from typing import Any, Callable, Iterable, Optional

import pandas
from tqdm import tqdm

from experiment.session import (
    ExperimentSessionMaker,
    ExperimentSession,
    get_standard_experiment_session_maker,
)
from sequence.runtime import Sequence, Shot


def build_dataframe_from_sequences(
    sequences: Iterable[Sequence],
    importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session_maker: Optional[ExperimentSessionMaker] = None,
    show_progress: bool = False,
) -> pandas.DataFrame:
    """Constructs a pandas dataframe from multiple experiment sequences

    Args:
        sequences: The sequences to construct the dataframe from
        importer: A function that takes a shot and a session and returns a dictionary. The keys of the returned
        dictionary will be the columns of the dataframe.
        session_maker: The session maker used to create the session to read the shot data. If None, a standard session
            maker will be used.
        show_progress: If True, a progress bar will be shown.

    Returns:
        A pandas dataframe with the data from the shots. The dataframe will have a multi-index with the sequence path as
        the first level, the shot name as the second level and the shot index as the third level. The columns will be
        the keys of the dictionaries returned by the importer function.
    """

    if session_maker is None:
        session_maker = get_standard_experiment_session_maker()

    session = session_maker()

    with session.activate():
        shots = []
        for sequence in sequences:
            shots.extend(sequence.get_shots(session))

    return build_dataframe_from_shots(shots, importer, session_maker, show_progress)


def build_dataframe_from_sequence(
    sequence: Sequence,
    importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session_maker: Optional[ExperimentSessionMaker] = None,
    show_progress: bool = False,
) -> pandas.DataFrame:
    """Constructs a pandas dataframe from an experiment sequence

    Args:
        sequence: The shots to construct the dataframe from
        importer: A function that takes a shot and a session and returns a dictionary. The keys of the returned
        dictionary will be the columns of the dataframe.
        session_maker: The session maker used to create the session to read the shot data. If None, a standard session
            maker will be used.
        show_progress: If True, a progress bar will be shown.

    Returns:
        A pandas dataframe with the data from the shots. The dataframe will have a multi-index with the sequence path as
        the first level, the shot name as the second level and the shot index as the third level. The columns will be
        the keys of the dictionaries returned by the importer function.
    """

    if session_maker is None:
        session_maker = get_standard_experiment_session_maker()

    session = session_maker()

    with session.activate():
        shots = sequence.get_shots(session)

    return build_dataframe_from_shots(shots, importer, session_maker, show_progress)


def build_dataframe_from_shots(
    shots: typing.Sequence[Shot],
    importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
    session_maker: Optional[ExperimentSessionMaker] = None,
    show_progress: bool = False,
) -> pandas.DataFrame:
    """Constructs a pandas dataframe from a sequence of shot

    Args:
        shots: The shots to construct the dataframe from
        importer: A function that takes a shot and a session and returns a dictionary. The keys of the returned
        dictionary will be the columns of the dataframe.
        session_maker: The session maker used to create the session to read the shot data. If None, a standard session
            maker will be used.
        show_progress: If True, a progress bar will be shown.

    Returns:
        A pandas dataframe with the data from the shots. The dataframe will have a multi-index with the sequence path as
        the first level, the shot name as the second level and the shot index as the third level. The columns will be
        the keys of the dictionaries returned by the importer function.
    """

    if session_maker is None:
        session_maker = get_standard_experiment_session_maker()

    session = session_maker()

    def map_shot_to_row(shot):
        with session:
            return importer(shot, session)

    indices = [(str(shot.sequence.path), shot.index) for shot in shots]
    index = pandas.MultiIndex.from_tuples(indices, names=["sequence", "shot"])
    if show_progress:
        rows = list(tqdm(map(map_shot_to_row, shots), total=len(shots)))
    else:
        rows = list(map(map_shot_to_row, shots))
    return pandas.DataFrame(rows, index=index)
