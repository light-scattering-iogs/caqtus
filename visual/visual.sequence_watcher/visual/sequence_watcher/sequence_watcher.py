import logging
import threading
from datetime import datetime
from itertools import islice
from typing import Optional, Callable, Any, Iterable, TypeVar

import pandas

from concurrent_updater import ConcurrentUpdater
from experiment.session import (
    ExperimentSessionMaker,
    ExperimentSession,
    get_standard_experiment_session_maker,
)
from sequence.runtime import Sequence, Shot

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DEFAULT_WATCH_INTERVAL = 1
DEFAULT_CHUNK_SIZE = 10


class SequenceWatcher(ConcurrentUpdater):
    """Class that watches a sequence in a separate thread

    When new shots are added to the sequence, the target function is called with the new shots as an argument.
    If the sequence is reset, a SequenceChangedError is raised.
    """

    def __init__(
        self,
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        target: Callable[[list[Shot], ...], Any],
        watch_interval: float = DEFAULT_WATCH_INTERVAL,
        name: Optional[str] = None,
        chunk_size: Optional[int] = DEFAULT_CHUNK_SIZE,
        *args,
        **kwargs,
    ):
        self._sequence = sequence
        self._sequence_start_time: Optional[datetime] = None
        self.__session = session_maker()
        self._processed_shots: set[Shot] = set()
        self.__target = target
        self._chunk_size = chunk_size

        super().__init__(
            target=self._look_at_sequence,
            watch_interval=watch_interval,
            name=name,
            *args,
            **kwargs,
        )

    def _look_at_sequence(self, *args, **kwargs):
        with self.__session.activate() as session:
            stats = self._sequence.get_stats(session)
        if stats["start_date"] != self._sequence_start_time:
            if self._sequence_start_time is not None:
                raise SequenceChangedError("Sequence has been reset")
            else:
                self._sequence_start_time = stats["start_date"]
        if len(self._processed_shots) < stats["number_completed_shots"]:
            with self.__session.activate() as session:
                shots = self._sequence.get_shots(session)
            new_shots = [shot for shot in shots if shot not in self._processed_shots]
            for chunk in iterate_in_chunks(new_shots, self._chunk_size):
                self.__target(chunk, *args, **kwargs)
                self._processed_shots.update(chunk)
                if self._must_stop.is_set():
                    break


class DataframeSequenceWatcher(SequenceWatcher):
    """Class that watches an experimental sequence and stores the shots data in a pandas dataframe as they are come

    Args:
        sequence: The sequence to watch
        importer: A function that takes a shot and an experiment session and returns a dictionary with the data to store
            in the dataframe. The columns of the dataframe are the keys of the dictionary.
        session_maker: The session maker to use to get the session to use to get the shot data. If None, the standard
            session maker is used.
        watch_interval: The interval in seconds between each check of the sequence.
        chunk_size: The number of shots to process at once. If None, all the shots are processed at once. It is
            recommended to use a chunk of relatively small size to avoid blocking the thread for too long.
    """

    def __init__(
        self,
        sequence: Sequence,
        importer: Callable[[Shot, ExperimentSession], dict[str, Any]],
        session_maker: Optional[ExperimentSessionMaker] = None,
        watch_interval: float = DEFAULT_WATCH_INTERVAL,
        chunk_size: Optional[int] = DEFAULT_CHUNK_SIZE,
    ):
        if session_maker is None:
            session_maker = get_standard_experiment_session_maker()
        self._dataframe = pandas.DataFrame()
        self._importer = importer
        self._session = session_maker()
        self.__lock = threading.Lock()
        super().__init__(
            sequence=sequence,
            session_maker=session_maker,
            watch_interval=watch_interval,
            target=self.process_shots,
            name=f"DataframeSequenceWatcher(sequence={sequence.path})",
            chunk_size=chunk_size,
        )

    def process_shots(self, new_shots: list[Shot]) -> pandas.Index:
        """Processes the new shots and adds them to the dataframe"""

        shots_data = []
        indices = []
        for shot in new_shots:
            with self._session.activate() as session:
                shots_data.append(self._importer(shot, session))
            indices.append((str(shot.sequence.path), shot.name, shot.index))
        index = pandas.MultiIndex.from_tuples(
            indices, names=("sequence", "shot", "index")
        )
        data = pandas.DataFrame(shots_data, index=index)
        with self.__lock:
            self._dataframe = pandas.concat((self._dataframe, data))
        return index

    def get_current_dataframe(self) -> pandas.DataFrame:
        """Returns a dataframe with the shots processed so far

        This is a detached copy, so it can be used safely, but it will not be updated when new shots are added.
        """

        with self.__lock:
            return self._dataframe.copy(deep=True)


class SequenceChangedError(RuntimeError):
    pass


T = TypeVar("T")


def iterate_in_chunks(
    iterator: Iterable[T], chunk_size: Optional[int]
) -> Iterable[list[T]]:
    """Iterate over an iterator in chunks of a given size"""
    iterator = iter(iterator)
    while True:
        chunk = list(islice(iterator, chunk_size))
        if not chunk:
            return
        yield chunk
