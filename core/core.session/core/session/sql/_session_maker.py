from ..session_maker import ExperimentSessionMaker
import sqlalchemy
import sqlalchemy.orm
from ..experiment_session import ExperimentSession
from ._experiment_session import SQLExperimentSession


class SQLExperimentSessionMaker(ExperimentSessionMaker):
    """Used to create a new experiment session with a predefined sqlalchemy engine.

    This session maker can create session that connects to a database using sqlalchemy.

    This object is pickleable and can be passed to other processes, assuming that the
    database referenced by the engine is accessible from the other processes.
    In particular, in-memory sqlite databases are not accessible from other processes.
    """

    def __init__(self, engine: sqlalchemy.Engine) -> None:
        self._engine = engine
        self._session_maker = sqlalchemy.orm.sessionmaker(self._engine)

    @classmethod
    def from_url(cls, url: sqlalchemy.engine.url.URL) -> "SQLExperimentSessionMaker":
        engine = sqlalchemy.create_engine(url)
        return cls(engine)

    def __call__(self) -> ExperimentSession:
        """Create a new ExperimentSession with the engine used at initialization."""

        return SQLExperimentSession(self._session_maker())

    # The following methods are required to make ExperimentSessionMaker pickleable since
    # sqlalchemy engine is not pickleable.
    # Only the engine url is pickled so the engine created upon unpickling might not be
    # exactly the same as the original one.
    def __getstate__(self) -> sqlalchemy.engine.url.URL:
        return self._engine.url

    def __setstate__(self, state: sqlalchemy.engine.url.URL):
        engine = sqlalchemy.create_engine(state)
        self.__init__(engine)
