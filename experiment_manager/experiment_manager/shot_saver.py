from copy import deepcopy, copy
from datetime import datetime
from queue import Queue, Empty
from threading import Event, Thread
from typing import Any

from experiment.session import ExperimentSessionMaker, ExperimentSession
from sequence.runtime import Sequence
from variable import VariableNamespace


class ShotSaver:
    """Maintain a queue of shots to save in arrival order and saves them in a separate thread

    It is necessary to store one shot after the other, otherwise there is a risk of mixing the shots order.
    When used as a context manager, it will start a thread that will save the shots in the queue.
    When the context manager is exited, the queue will be emptied before returning.
    """

    def __init__(self, sequence: Sequence, session_maker: ExperimentSessionMaker):
        """Create a new ShotSaver

        Args:
            sequence: The sequence to save the shots to
            session_maker: The session maker to use to create save sessions
        """
        self._sequence = sequence
        self._session_maker = session_maker
        self._queue = Queue()
        self._active = Event()

        self._save_thread = Thread(target=self._save_thread_func)

    def __enter__(self):
        self._queue = Queue()
        self._active.set()
        self._save_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._active.clear()
        self._save_thread.join()

    def push_shot(
        self,
        shot_name: str,
        start_time: datetime,
        end_time: datetime,
        parameters: VariableNamespace,
        measures: dict[str, Any],
    ):
        """Push a shot to the save queue

        Args:
            shot_name: The qualified name of the shot
            start_time: The start time of the shot, just before starting the sequencer
            end_time: The end time of the shot, just after the sequencer has finished
            parameters: The values of the parameters used for this shot
            measures: The values of the measures taken during this shot
        """

        if not self._active.is_set():
            raise RuntimeError("ShotSaver is not active")
        self._queue.put(
            {
                "shot_name": shot_name,
                "start_time": copy(start_time),
                "end_time": copy(end_time),
                "parameters": deepcopy(parameters),
                "measures": deepcopy(measures),
            },
            block=True,
        )

    def _save_thread_func(self):
        while self._active.is_set():
            try:
                shot = self._queue.get(timeout=0.1)
                _save_shot(
                    sequence=self._sequence, session=self._session_maker(), **shot
                )
                self._queue.task_done()
            except Empty:
                continue

    def wait(self):
        """Wait for the queue to be empty"""
        self._queue.join()


def _save_shot(
    sequence: Sequence,
    shot_name: str,
    start_time: datetime,
    end_time: datetime,
    parameters: VariableNamespace,
    measures: dict[str, Any],
    session: ExperimentSession,
):
    with session:
        parameters = {name: value for name, value in parameters.items()}
        sequence.create_shot(
            shot_name, start_time, end_time, parameters, measures, session
        )
