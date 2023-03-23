import logging
from typing import Callable, Optional

from experiment.session import ExperimentSessionMaker
from sequence.runtime import Sequence, State
from .concurrent_updater import ConcurrentUpdater

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SequenceStateWatcher(ConcurrentUpdater):
    """Watches the state of a sequence at regular intervals

    Args:
        sequence: The sequence to watch
        session_maker: A function that returns a new session
        on_state_changed: A callback that is called when the state changes
        watch_interval: The interval at which to check the state, in seconds
    """

    def __init__(
        self,
        sequence: Sequence,
        session_maker: ExperimentSessionMaker,
        on_state_changed: Optional[Callable[[State], None]] = None,
        watch_interval: float = 1.0,
    ):
        self._sequence = sequence
        self._on_state_changed = on_state_changed
        self._session = session_maker()
        self._sequence_state = None
        super().__init__(target=self._update_state, watch_interval=watch_interval)

    def start(self):
        self._update_state()
        super().start()

    def _read_state(self) -> State:
        with self._session as session:
            return self._sequence.get_state(session)

    def _update_state(self):
        new_state = self._read_state()
        changed = new_state != self._sequence_state
        self._sequence_state = new_state
        if changed and self._on_state_changed:
            self._on_state_changed(new_state)

    @property
    def sequence_state(self) -> Optional[State]:
        return self._sequence_state
