from typing import Mapping, Optional

import sqlalchemy
import sqlalchemy.orm
from ._experiment_session import (
    SQLExperimentSession,
    DeviceConfigurationSerializer,
)
from ._sequence_collection import (
    IterationConfigurationJSONSerializer,
    default_iteration_configuration_serializer,
)
from ..experiment_session import ExperimentSession
from ..session_maker import ExperimentSessionMaker


class SQLExperimentSessionMaker(ExperimentSessionMaker):
    """Used to create a new experiment session with a predefined sqlalchemy engine.

    This session maker can create session that connects to a database using sqlalchemy.

    This object is pickleable and can be passed to other processes, assuming that the
    database referenced by the engine is accessible from the other processes.
    In particular, in-memory sqlite databases are not accessible from other processes.
    """

    def __init__(
        self,
        engine: sqlalchemy.Engine,
        device_configuration_serializers: Mapping[str, DeviceConfigurationSerializer],
        iteration_config_serializer: Optional[
            IterationConfigurationJSONSerializer
        ] = None,
    ) -> None:
        self._engine = engine
        self._session_maker = sqlalchemy.orm.sessionmaker(self._engine)
        self._device_configuration_serializers = dict(device_configuration_serializers)
        if iteration_config_serializer is None:
            iteration_config_serializer = default_iteration_configuration_serializer
        self._iteration_config_serializer = iteration_config_serializer

    def __call__(self) -> ExperimentSession:
        """Create a new ExperimentSession with the engine used at initialization."""

        return SQLExperimentSession(
            self._session_maker(),
            self._device_configuration_serializers,
            self._iteration_config_serializer,
        )

    # The following methods are required to make ExperimentSessionMaker pickleable since
    # sqlalchemy engine is not pickleable.
    # Only the engine url is pickled so the engine created upon unpickling might not be
    # exactly the same as the original one.
    def __getstate__(self):
        return {
            "url": self._engine.url,
            "device_configuration_serializers": self._device_configuration_serializers,
            "iteration_config_serializer": self._iteration_config_serializer,
        }

    def __setstate__(self, state):
        engine = sqlalchemy.create_engine(state["url"])
        serializers = state["device_configuration_serializers"]
        iteration_config_serializer = state["iteration_config_serializer"]
        self.__init__(engine, serializers, iteration_config_serializer)
