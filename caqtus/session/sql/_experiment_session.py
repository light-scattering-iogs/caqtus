import contextlib

import attrs
import sqlalchemy.orm

from caqtus.types.parameter import ParameterNamespace
from caqtus.utils import serialization
from ._device_configuration_collection import SQLDeviceConfigurationCollection
from ._path_hierarchy import SQLPathHierarchy
from ._sequence_collection import (
    SQLSequenceCollection,
)
from ._serializer import SerializerProtocol
from .parameters_table import SQLParameters
from ..experiment_session import (
    ExperimentSession,
    ExperimentSessionNotActiveError,
)


@attrs.frozen
class Active:
    session: sqlalchemy.orm.Session
    session_context: contextlib.AbstractContextManager[sqlalchemy.orm.Session]

    def __str__(self):
        return f"active"


@attrs.frozen
class Inactive:
    session_context: contextlib.AbstractContextManager[sqlalchemy.orm.Session]

    def __str__(self):
        return f"inactive"


@attrs.frozen
class Closed:
    def __str__(self):
        return f"closed"


SessionState = Inactive | Active | Closed


class SQLExperimentSession(ExperimentSession):
    """Used to store experiment data in a SQL database.

    This class implements the :class:`ExperimentSession` interface and the documentation
    of the related methods can be found in the :class:`ExperimentSession`documentation.
    """

    def __init__(
        self,
        session_context: contextlib.AbstractContextManager[sqlalchemy.orm.Session],
        serializer: SerializerProtocol,
        *args,
        **kwargs,
    ):
        """Create a new experiment session.

        This constructor is not meant to be called directly.
        Instead, use a :py:class:`SQLExperimentSessionMaker` to create a new session.
        """

        super().__init__(*args, **kwargs)
        self._state = Inactive(session_context=session_context)
        self.paths = SQLPathHierarchy(parent_session=self)
        self.sequences = SQLSequenceCollection(
            parent_session=self, serializer=serializer
        )
        self.default_device_configurations = SQLDeviceConfigurationCollection(
            parent_session=self, serializer=serializer
        )

    def get_global_parameters(self) -> ParameterNamespace:
        return _get_global_parameters(self._get_sql_session())

    def set_global_parameters(self, parameters: ParameterNamespace) -> None:
        return _set_global_parameters(self._get_sql_session(), parameters)

    def __repr__(self):
        return f"<{self.__class__.__name__} ({self._state})>"

    def __enter__(self):
        if not isinstance(self._state, Inactive):
            error = RuntimeError("Session has already been activated")
            error.add_note(
                "You cannot reactivate a session, you must create a new one."
            )
            raise error
        context = self._state.session_context
        sql_session = context.__enter__()
        self._state = Active(session=sql_session, session_context=context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not isinstance(self._state, Active):
            raise ExperimentSessionNotActiveError(
                "Experiment session is not active and cannot be exited"
            )
        context = self._state.session_context
        context.__exit__(exc_type, exc_val, exc_tb)
        self._state = Closed()

    def _get_sql_session(self) -> sqlalchemy.orm.Session:
        if not isinstance(self._state, Active):
            raise ExperimentSessionNotActiveError(
                "Experiment session is not active and cannot be used"
            )
        return self._state.session


def _get_global_parameters(session: sqlalchemy.orm.Session) -> ParameterNamespace:
    stmt = sqlalchemy.select(SQLParameters).where(SQLParameters.name == "global")
    result = session.execute(stmt)
    if found := result.scalar():
        return serialization.converters["json"].structure(
            found.content, ParameterNamespace
        )
    else:
        # It could be that the table is empty if set_global_parameters was never
        # called before, in which case we return an empty ParameterNamespace.
        return ParameterNamespace.empty()


def _set_global_parameters(
    session: sqlalchemy.orm.Session, parameters: ParameterNamespace
) -> None:
    if not isinstance(parameters, ParameterNamespace):
        raise TypeError(
            f"Expected a ParameterNamespace, got {type(parameters).__name__}"
        )
    query = sqlalchemy.select(SQLParameters).where(SQLParameters.name == "global")
    result = session.execute(query)
    content = serialization.converters["json"].unstructure(
        parameters, ParameterNamespace
    )
    if found := result.scalar():
        found.content = content
    else:
        new_parameters = SQLParameters(name="global", content=content)
        session.add(new_parameters)
