import logging
from datetime import datetime
from itertools import islice
from typing import Optional, Callable, Iterable, TypeVar, ParamSpec, Concatenate

from concurrent_updater import ConcurrentUpdater
from experiment.session import (
    ExperimentSession,
    get_standard_experiment_session,
)
from sequence.runtime import Sequence, Shot

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

DEFAULT_WATCH_INTERVAL = 1
DEFAULT_CHUNK_SIZE = 10

T = TypeVar("T")
P = ParamSpec("P")


class SequenceWatcher(ConcurrentUpdater):
    """Class that watches a sequence in a separate thread

    When new shots are added to the sequence, the target function is called with the new shots as an argument.
    If the sequence is reset, a SequenceChangedError is raised.
    """

    def __init__(
        self,
        sequence: Sequence,
        target: Callable[Concatenate[list[Shot], P], None],
        session: Optional[ExperimentSession] = None,
        watch_interval: float = DEFAULT_WATCH_INTERVAL,
        name: Optional[str] = None,
        chunk_size: Optional[int] = DEFAULT_CHUNK_SIZE,
        *args,
        **kwargs,
    ):
        self._sequence = sequence
        self._sequence_start_time: Optional[datetime] = None
        if session is None:
            session = get_standard_experiment_session()
        self._session = session
        self._processed_shots: set[Shot] = set()
        self._target = target
        self._chunk_size = chunk_size

        super().__init__(
            target=self._look_at_sequence,
            watch_interval=watch_interval,
            name=name,
            *args,
            **kwargs,
        )

    def _look_at_sequence(self, *args: P.args, **kwargs: P.kwargs):
        with self._session.activate() as session:
            stats = self._sequence.get_stats(session)
        if stats.start_date != self._sequence_start_time:
            if self._sequence_start_time is not None:
                raise SequenceResetError("Sequence has been reset")
            else:
                self._sequence_start_time = stats.start_date
        if len(self._processed_shots) < stats.number_completed_shots:
            with self._session.activate() as session:
                shots = self._sequence.get_shots(session)
            new_shots = [shot for shot in shots if shot not in self._processed_shots]
            for chunk in iterate_in_chunks(new_shots, self._chunk_size):
                self._target(chunk, *args, **kwargs)
                self._processed_shots.update(chunk)
                if self._must_stop.is_set():
                    break


class SequenceResetError(RuntimeError):
    pass


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
