from datetime import datetime
from threading import Lock
from typing import Optional

import sqlalchemy
import sqlalchemy.orm

from experiment.configuration import ExperimentConfig
from sql_model.model import ExperimentConfigModel


class ExperimentSessionNotActiveError(RuntimeError):
    pass


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
                raise RuntimeError("Session is already active")
            self._sql_session = self._session_maker()
            self._transaction = self._sql_session.begin().__enter__()
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self._lock:
            self._transaction.__exit__(exc_type, exc_val, exc_tb)
            self._sql_session = None
            self._transaction = None

    def get_sql_session(self) -> sqlalchemy.orm.Session:
        if self._sql_session is None:
            raise ExperimentSessionNotActiveError(
                "Every access to an experiment session must be wrapped in a single with"
                " block"
            )
        return self._sql_session

    def add_experiment_config(
        self, name: str, experiment_config: ExperimentConfig, comment: Optional[str]
    ):
        ExperimentConfigModel.add_config(
            name=name,
            yaml=experiment_config.to_yaml(),
            comment=comment,
            session=self.get_sql_session(),
        )

    def get_experiment_configs(
        self, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> dict[str, ExperimentConfig]:
        results = ExperimentConfigModel.get_configs(
            from_date,
            to_date,
            self.get_sql_session(),
        )

        return {
            name: ExperimentConfig.from_yaml(yaml) for name, yaml in results.items()
        }


class ExperimentSessionMaker:
    def __init__(self, database_url: str, commit: bool = True):
        self._database_url = database_url
        self._commit = commit

    def __call__(self) -> ExperimentSession:
        return ExperimentSession(database_url=self._database_url, commit=self._commit)
