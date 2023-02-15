import logging
from logging.handlers import QueueHandler
from multiprocessing import Queue
from threading import Lock, Event
from typing import Optional

from experiment.session import ExperimentSessionMaker
from sequence.runtime import SequencePath
from .sequence_runner import SequenceRunnerThread

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")

logs_queue = Queue()
logging.getLogger().addHandler(QueueHandler(logs_queue))


def get_logs_queue():
    return logs_queue


class ExperimentManager:
    """Manage execution of a sequence on the experiment

    It ensures that only one sequence can be launched. Only one instance should be created for a given setup.
    """

    def __init__(self):
        self._lock = Lock()
        self._waiting_to_interrupt = Event()
        self._sequence_runner_thread: Optional[SequenceRunnerThread] = None

    def start_sequence(
        self,
        experiment_config_name: str,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
    ) -> bool:
        """Attempts to start running the sequence on the setup

        This method is not blocking.

        Args:
            experiment_config_name: an identifier referring to the experiment
            configuration in the experiment session.
            sequence_path: a path identifying the sequence in the experiment session
            session_maker: a session maker to create sessions to the experiment
        Returns:
            True if the sequence was successfully started, False if a sequence is
            already running.

        """
        with self._lock:
            if self.is_running():
                return False
            else:
                self._waiting_to_interrupt.clear()
                self._sequence_runner_thread = SequenceRunnerThread(
                    experiment_config_name,
                    sequence_path,
                    session_maker,
                    self._waiting_to_interrupt,
                )
                self._sequence_runner_thread.start()
                return True

    def interrupt_sequence(self) -> bool:
        with self._lock:
            if self.is_running():
                self._waiting_to_interrupt.set()
                return True
            else:
                return False

    def is_waiting_to_interrupt(self):
        return self.is_running() and self._waiting_to_interrupt.is_set()

    def is_running(self) -> bool:
        return (
            self._sequence_runner_thread is not None
        ) and self._sequence_runner_thread.is_alive()
