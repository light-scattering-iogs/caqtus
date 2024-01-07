import uuid
from collections.abc import Set, Mapping
from contextlib import AbstractContextManager
from typing import Optional

from core.session import PureSequencePath, ExperimentSessionMaker, ConstantTable
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

        self.constant_tables: Mapping[str, ConstantTable]

        with self._session_maker() as session:
            if device_configurations_uuid is None:
                device_configurations_uuid = (
                    session.device_configurations.get_in_use_uuids()
                )
            self._device_configurations_uuid = device_configurations_uuid
            if constant_tables_uuid is None:
                constant_tables_uuid = session.constants.get_in_use_uuids()
            self._constant_tables_uuid = constant_tables_uuid

    def __enter__(self):
        self._prepare_sequence()
        try:
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

    def _prepare_sequence(self):
        with self._session_maker() as session:
            session.sequence_collection.set_state(self._sequence_path, State.PREPARING)
            session.sequence_collection.set_device_configuration_uuids(
                self._sequence_path, self._device_configurations_uuid
            )
            session.sequence_collection.set_constant_table_uuids(
                self._sequence_path, self._constant_tables_uuid
            )
            self.constant_tables = {
                session.constants.get_table_name(uuid_): session.constants.get_table(
                    uuid_
                )
                for uuid_ in self._constant_tables_uuid
            }

    def _set_sequence_state(self, state: State):
        with self._session_maker() as session:
            session.sequence_collection.set_state(self._sequence_path, state)

    def _prepare(self):
        pass
