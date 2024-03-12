from typing import Mapping

import attrs
import sqlalchemy.orm
from core.session import ParameterNamespace
from core.session.sql.parameters_table import SQLParameters
from util import serialization

from ._device_configuration_collection import SQLDeviceConfigurationCollection
from ._path_hierarchy import SQLPathHierarchy
from ._sequence_collection import (
    SQLSequenceCollection,
    SequenceSerializer,
    DeviceConfigurationSerializer,
    default_sequence_serializer,
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


default_serializer = Serializer(
    sequence_serializer=default_sequence_serializer, device_configuration_serializers={}
)
"""A default serializer object for SQLExperimentSessionMaker,
It can read and store sequences that use steps to iterate over parameters and with shots 
containing digital, analog and camera time lanes. 
"""


@attrs.define(init=False)
class SQLExperimentSession(ExperimentSession):
    paths: SQLPathHierarchy
    sequences: SQLSequenceCollection
    default_device_configurations: SQLDeviceConfigurationCollection

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
            device_configuration_serializers=serializer.device_configuration_serializers,
        )
        self.default_device_configurations = SQLDeviceConfigurationCollection(
            parent_session=self,
            device_configuration_serializers=serializer.device_configuration_serializers,
        )

    def get_global_parameters(self) -> ParameterNamespace:
        stmt = sqlalchemy.select(SQLParameters).where(SQLParameters.name == "global")
        result = self._get_sql_session().execute(stmt)
        if found := result.scalar():
            return serialization.converters["json"].structure(
                found.content, ParameterNamespace
            )
        else:
            # It could be that the table is empty if set_global_parameters was never
            # called before, in which case we return an empty ParameterNamespace.
            return ParameterNamespace.empty()

    def set_global_parameters(self, parameters: ParameterNamespace) -> None:
        if not isinstance(parameters, ParameterNamespace):
            raise TypeError(
                f"Expected a ParameterNamespace, got {type(parameters).__name__}"
            )
        query = sqlalchemy.select(SQLParameters).where(SQLParameters.name == "global")
        result = self._get_sql_session().execute(query)
        content = serialization.converters["json"].unstructure(
            parameters, ParameterNamespace
        )
        if found := result.scalar():
            found.content = content
        else:
            new_parameters = SQLParameters(name="global", content=content)
            self._get_sql_session().add(new_parameters)

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
