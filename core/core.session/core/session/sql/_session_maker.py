from ..session_maker import ExperimentSessionMaker
import sqlalchemy
import sqlalchemy.orm
from ..experiment_session import ExperimentSession


class SQLExperimentSessionMaker(ExperimentSessionMaker):
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
    def __getstate__(self) -> sqlalchemy.engine.url.URL:
        return self._engine.url

    def __setstate__(self, state: sqlalchemy.engine.url.URL):
        engine = sqlalchemy.create_engine(state)
        self.__init__(engine)
