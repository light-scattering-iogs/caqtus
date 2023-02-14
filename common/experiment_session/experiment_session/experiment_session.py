from threading import Lock

import sqlalchemy
import sqlalchemy.orm


class ExperimentSession:
    def __init__(self, database_url: str, commit: bool = True):
        self._database_url = database_url

        self._engine = sqlalchemy.create_engine(database_url)
        self._session_maker = sqlalchemy.orm.sessionmaker(self._engine)
        self._sql_session = None
        self._commit = commit
        self._level = 0

        self._lock = Lock()

    def __enter__(self):
        with self._lock:
            if self._sql_session is not None:
                self._level += 1
            else:
                self._sql_session = self._session_maker().__enter__()
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._lock:
            if self._commit:
                self._sql_session.commit()
            self._level -= 1
            if self._level == 0:
                self._sql_session.__exit__(exc_type, exc_val, exc_tb)
                self._sql_session = None

    def get_sql_session(self) -> sqlalchemy.orm.Session:
        return self._sql_session


class ExperimentSessionMaker:
    def __init__(self, database_url: str, commit: bool = True):
        self._database_url = database_url
        self._commit = commit

    def __call__(self) -> ExperimentSession:
        return ExperimentSession(database_url=self._database_url, commit=self._commit)
