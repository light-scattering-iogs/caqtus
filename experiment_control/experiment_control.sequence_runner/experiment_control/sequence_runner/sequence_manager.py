from contextlib import AbstractContextManager, ExitStack

from experiment.configuration import ExperimentConfig
from experiment.session import ExperimentSessionMaker
from sequence.runtime import SequencePath, Sequence, State
from .sequence_runner import SequenceInterruptedException


class SequenceManager(AbstractContextManager):
    def __init__(
        self,
        experiment_config: ExperimentConfig,
        sequence_path: SequencePath,
        session_maker: ExperimentSessionMaker,
    ):
        self._experiment_config = experiment_config
        self._sequence = Sequence(sequence_path)
        self._session_maker = session_maker
        self._exit_stack = ExitStack()

    def __enter__(self):
        self._exit_stack.__enter__()
        with self._session_maker() as session:
            self._sequence.set_state(State.PREPARING, session)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        exception_swallowed = None
        if exc_value is None:
            self._set_sequence_state(State.FINISHED)
        elif isinstance(exc_value, SequenceInterruptedException):
            self._set_sequence_state(State.INTERRUPTED)
            exception_swallowed = True
        else:
            self._set_sequence_state(State.CRASHED)
            exception_swallowed = False
        self._exit_stack.__exit__(exc_type, exc_value, traceback)
        return exception_swallowed

    def interrupt_sequence(self):
        raise SequenceInterruptedException()

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            self._sequence.set_state(state, session)
