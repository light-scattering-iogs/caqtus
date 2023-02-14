import sqlalchemy
import sqlalchemy.orm


class ExperimentSession:
    def __init__(self, database_url: str):
        self._database_url = database_url

        self._engine = sqlalchemy.create_engine(database_url)
        self._session_maker = sqlalchemy.orm.sessionmaker(self._engine)
        self._sql_session = None

    def __enter__(self):
        if self._sql_session is not None:
            raise RuntimeError("ExperimentSession is already active")
        self._sql_session = self._session_maker.begin().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._sql_session.__exit__(exc_type, exc_val, exc_tb)
        self._sql_session = None

    def get_sql_session(self) -> sqlalchemy.orm.Session:
        return self._sql_session


class ExperimentSessionMaker:
    def __init__(self, database_url: str):
        self._database_url = database_url

    def __call__(self) -> ExperimentSession:
        return ExperimentSession(self._database_url)
