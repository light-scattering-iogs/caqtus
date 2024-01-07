import uuid
from collections.abc import Set
from contextlib import AbstractContextManager
from typing import Optional

from core.session import PureSequencePath, ExperimentSessionMaker
from core.session.sequence import State


class SequenceManager(AbstractContextManager):
    def __init__(
        self,
        sequence_path: PureSequencePath,
        session_maker: ExperimentSessionMaker,
        device_configurations_uuid: Optional[Set[uuid.UUID]] = None,
        constant_tables_uuid: Optional[Set[uuid.UUID]] = None,
    ) -> None:
        self._session_maker = session_maker
        self._sequence_path = sequence_path

    def __enter__(self):
        try:
            self._set_sequence_state(State.PREPARING)
            self._prepare()
            self._set_sequence_state(State.RUNNING)
        except Exception:
            self._set_sequence_state(State.CRASHED)
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        error_occurred = exc_val is not None

        if error_occurred:
            self._set_sequence_state(State.CRASHED)
        else:
            self._set_sequence_state(State.FINISHED)

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            session.sequence_collection.set_state(self._sequence_path, state)

    def _prepare(self):
        pass
