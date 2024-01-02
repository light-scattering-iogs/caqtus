import logging
from threading import Lock, Event
from typing import Optional

from core.session import ExperimentSessionMaker, PureSequencePath
from core.session.sequence import State
from ..sequence_runner import SequenceRunnerThread

logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")


class ExperimentManager:
    """Manage execution of a sequence on the experiment

    It ensures that only one sequence can be launched. Only one instance should be
    created within a given session.
    This is the entry point for submitting sequences to run on the experiment.

    Instances of this class can be used from different threads simultaneously, because
    their inner resources are protected by a lock.
    """

    def __init__(self, session_maker: ExperimentSessionMaker) -> None:
        """Create an instance of the experiment manager.

        When creating a new instance of this class, all previously running sequences
        within the session are crashed.
        """

        self._lock = Lock()
        self._waiting_to_interrupt = Event()
        self._sequence_runner_thread: Optional[SequenceRunnerThread] = None
        self._session_maker = session_maker

        # Here we crash all previous running sequences. This has two goals:
        # First, it prevents two sequences from running in the same time, which could
        # have unexpected results. Second, this will clean up previous sequences that
        # might have been left in an inconsistent running state if the previous
        # ExperimentManager was abruptly shut down and didn't have time to interrupt the
        # previous sequence.
        self.crash_running_sequences()

    def crash_running_sequences(self) -> None:
        """Crash any running sequences

        This method is called when the experiment server is started to ensure that no
        previous sequence is running.
        """

        with self._lock, self._session_maker() as session:
            sequences = set()
            states_to_crash = {State.PREPARING, State.RUNNING}
            for state in states_to_crash:
                sequences.update(session.paths.get_sequences_in_state(state))
            for sequence in sequences:
                session.paths.set_sequence_state(sequence, State.CRASHED)

    def start_sequence(
        self,
        experiment_config_name: str,
        sequence_path: PureSequencePath,
    ) -> bool:
        """Attempts to start running the sequence on the setup

        This method is not blocking.

        Args:
            experiment_config_name: an identifier referring to the experiment
            configuration in the experiment session.
            sequence_path: a path identifying the sequence in the experiment session
        Returns:
            True if the sequence was successfully started, False if a previous sequence
            is already running.

        """
        with self._lock:
            if self.is_running():
                return False
            else:
                self._waiting_to_interrupt.clear()
                self._sequence_runner_thread = SequenceRunnerThread(
                    experiment_config_name,
                    sequence_path,
                    self._session_maker,
                    self._waiting_to_interrupt,
                )
                self._sequence_runner_thread.start()
                return True

    def interrupt_sequence(self) -> bool:
        """Inform the current running sequence that it should be interrupted.

        This method is not blocking.
        After calling this method, actual interruption of the sequence might take some
        time as it finishes the current shots, saves the data and performs cleanup.
        After calling this method, you should wait until `is_running` returns False.

        Returns:
            True, if a sequence is currently running, and it was marked for
            interruption.
            False, if no sequence is currently running.
        """

        with self._lock:
            if self.is_running():
                self._waiting_to_interrupt.set()
                return True
            else:
                return False

    def is_waiting_to_interrupt(self) -> bool:
        """Indicates if the current running sequence was requested to stop.

        Returns:
            True, if there is a sequence currently running, and it was marked for
            interruption.
            False, if the currently running sequence, was not marked for interruption or
            if no sequence is running.
        """

        return self.is_running() and self._waiting_to_interrupt.is_set()

    def is_running(self) -> bool:
        """Indicates if a sequence is currently running."""

        return (
            self._sequence_runner_thread is not None
        ) and self._sequence_runner_thread.is_alive()
