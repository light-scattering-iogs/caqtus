from typing import Mapping

import attrs
import sqlalchemy.orm

from ._constant_table_collection import SQLConstantTableCollection
from ._device_configuration_collection import (
    SQLDeviceConfigurationCollection,
    DeviceConfigurationSerializer,
)
from ._path_hierarchy import SQLPathHierarchy
from ._sequence_collection import (
    SQLSequenceCollection,
    SequenceSerializer,
)
from ..experiment_session import (
    ExperimentSession,
    ExperimentSessionNotActiveError,
)


@attrs.define
class Serializer:
    """Indicates how to serialize and deserialize objects for persistent storage."""

    sequence_serializer: SequenceSerializer
    device_configuration_serializers: Mapping[str, DeviceConfigurationSerializer]


@attrs.define(init=False)
class SQLExperimentSession(ExperimentSession):
    paths: SQLPathHierarchy
    sequences: SQLSequenceCollection
    device_configurations: SQLDeviceConfigurationCollection
    constants: SQLConstantTableCollection

    _sql_session: sqlalchemy.orm.Session
    _is_active: bool

    def __init__(
        self,
        session: sqlalchemy.orm.Session,
        serializer: Serializer,
        *args,
        **kwargs,
    ):
        """Create a new experiment session.

        This constructor is not meant to be called directly.
        Instead, use a :py:class:`SQLExperimentSessionMaker` to create a new session.
        """

        super().__init__(*args, **kwargs)
        self._sql_session = session
        self._is_active = False
        self.paths = SQLPathHierarchy(parent_session=self)
        self.sequences = SQLSequenceCollection(
            parent_session=self,
            serializer=serializer.sequence_serializer,
        )
        self.device_configurations = SQLDeviceConfigurationCollection(
            parent_session=self,
            device_configuration_serializers=serializer.device_configuration_serializers,
        )
        self.constants = SQLConstantTableCollection(parent_session=self)

    def __str__(self):
        return f"<{self.__class__.__name__} @ {self._sql_session.get_bind()}>"

    def __enter__(self):
        if self._is_active:
            raise RuntimeError("Session is already active")
        self._transaction = self._sql_session.begin().__enter__()
        self._is_active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._transaction.__exit__(exc_type, exc_val, exc_tb)
        self._transaction = None
        self._is_active = False

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        if not self._is_active:
            raise ExperimentSessionNotActiveError(
                "Experiment session was not activated"
            )
        return self._sql_session
