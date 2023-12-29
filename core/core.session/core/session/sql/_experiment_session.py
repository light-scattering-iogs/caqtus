import sqlalchemy.orm
from attrs import define

from ..experiment_session import (
    ExperimentSession,
    ExperimentSessionNotActiveError,
)


# from ._experiment_config_collection import SQLExperimentConfigCollection
from ._sequence_hierarchy import SQLSequenceHierarchy
from ._sequence_collection import SQLSequenceCollection

# from .sql_sequence_hierarchy import SQLSequenceHierarchy
# from .sql_shot_collection import SQLShotCollection


@define(init=False)
class SQLExperimentSession(ExperimentSession):
    # shot_collection: SQLShotCollection
    sequence_hierarchy: SQLSequenceHierarchy
    sequence_collection: SQLSequenceCollection
    # experiment_configs: SQLExperimentConfigCollection

    _sql_session: sqlalchemy.orm.Session
    _is_active: bool

    def __init__(self, session: sqlalchemy.orm.Session, *args, **kwargs):
        """Create a new experiment session.

        This constructor is not meant to be called directly.
        Instead, use a :py:class:`SQLExperimentSessionMaker` to create a new session.
        """

        super().__init__(*args, **kwargs)
        self._sql_session = session
        self._is_active = False
        # self.shot_collection = SQLShotCollection(parent_session=self)
        self.sequence_hierarchy = SQLSequenceHierarchy(parent_session=self)
        self.sequence_collection = SQLSequenceCollection(parent_session=self)
        # self.experiment_configs = SQLExperimentConfigCollection(parent_session=self)

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
