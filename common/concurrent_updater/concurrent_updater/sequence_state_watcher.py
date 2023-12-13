import logging
from typing import Callable, Optional, Self

from core.session import ExperimentSessionMaker
from core.session.sequence import Sequence, State
from util.concurrent import BackgroundScheduler

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SequenceStateWatcher:
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
        self._watch_interval = watch_interval
        self._scheduler = BackgroundScheduler(max_workers=1)

    def __enter__(self) -> Self:
        self._update_state()
        self._scheduler.schedule_task(self._update_state, self._watch_interval)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self._scheduler.__exit__(exc_type, exc_value, traceback)

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
