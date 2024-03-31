from typing import Self

import sqlalchemy
import sqlalchemy.orm
from sqlalchemy import text

from ._experiment_session import SQLExperimentSession, Serializer, default_serializer
from ._table_base import create_tables
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
        serializer: Serializer = default_serializer,
    ) -> None:
        # By default, sqlite does not enforce foreign key constraints, so we need to
        # enable it explicitly.
        if engine.url.drivername == "sqlite":
            with engine.connect() as connection:
                connection.execute(text("pragma foreign_keys=on"))

        self._engine = engine
        self._session_maker = sqlalchemy.orm.sessionmaker(self._engine)
        self._serializer = serializer

    @classmethod
    def from_url(
        cls,
        url: str | sqlalchemy.URL,
        serializer: Serializer = default_serializer,
    ) -> Self:
        """Create a new SQLExperimentSessionMaker from a database url.

        Args:
            url: The database url to connect to.
            serializer: The serializer to use to store data in the database.
        """

        engine = sqlalchemy.create_engine(url)
        return cls(engine, serializer)

    def create_tables(self) -> None:
        """Create the tables in the database.

        This method is useful the first time the database is created.
        It will create missing tables and ignore existing ones.
        """

        create_tables(self._engine)

    def __call__(self) -> ExperimentSession:
        """Create a new ExperimentSession with the engine used at initialization."""

        return SQLExperimentSession(
            self._session_maker(),
            self._serializer,
        )

    # The following methods are required to make ExperimentSessionMaker pickleable since
    # sqlalchemy engine is not pickleable.
    # Only the engine url is pickled so the engine created upon unpickling might not be
    # exactly the same as the original one.
    def __getstate__(self):
        return {
            "url": self._engine.url,
            "serializer": self._serializer,
        }

    def __setstate__(self, state):
        engine = sqlalchemy.create_engine(state.pop("url"))
        self.__init__(engine, **state)
