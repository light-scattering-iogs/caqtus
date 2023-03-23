import logging

from experiment.session import ExperimentSessionMaker
from sequence.runtime import Sequence, State
from .concurrent_updater import ConcurrentUpdater

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SequenceStateWatcher(ConcurrentUpdater):
    """Watches the state of a sequence at regular intervals"""

    def __init__(
        self,
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        watch_interval: float = 1.0,
    ):
        self._sequence = sequence
        self._session = session_maker()
        self._sequence_state = self._read_state()
        super().__init__(target=self._update_state, watch_interval=watch_interval)

    def _read_state(self) -> State:
        logger.debug("Reading sequence state")
        with self._session as session:
            return self._sequence.get_state(session)

    def _update_state(self):
        self._sequence_state = self._read_state()

    @property
    def sequence_state(self) -> State:
        return self._sequence_state
