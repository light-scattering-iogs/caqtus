import logging
import re
from datetime import datetime
from threading import Lock
from typing import Optional

import sqlalchemy
import sqlalchemy.orm

from experiment.configuration import ExperimentConfig
from sql_model.model import ExperimentConfigModel, CurrentExperimentConfigModel

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        self,
        experiment_config: ExperimentConfig,
        name: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> str:
        if name is None:
            name = self._get_new_experiment_config_name()
        yaml = experiment_config.to_yaml()
        assert ExperimentConfig.from_yaml(yaml) == experiment_config
        ExperimentConfigModel.add_config(
            name=name,
            yaml=yaml,
            comment=comment,
            session=self.get_sql_session(),
        )
        return name

    def _get_new_experiment_config_name(self) -> str:
        session = self.get_sql_session()
        query_names = session.query(ExperimentConfigModel.name)
        numbers = []
        pattern = re.compile("config_(\\d+)")
        for name in session.scalars(query_names):
            if match := pattern.match(name):
                numbers.append(int(match.group(1)))
        return f"config_{_find_first_unused_number(numbers)}"

    def get_experiment_config(self, name: str) -> ExperimentConfig:
        return ExperimentConfig.from_yaml(
            ExperimentConfigModel.get_config(name, self.get_sql_session())
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

    def set_current_experiment_config(self, name: str):
        CurrentExperimentConfigModel.set_current_experiment_config(
            name=name, session=self.get_sql_session()
        )

    def get_current_experiment_config_name(self) -> Optional[str]:
        return CurrentExperimentConfigModel.get_current_experiment_config_name(
            session=self.get_sql_session()
        )

    def get_current_experiment_config(self) -> Optional[ExperimentConfig]:
        name = self.get_current_experiment_config_name()
        if name is None:
            return None
        return self.get_experiment_configs()[name]


def _find_first_unused_number(numbers: list[int]) -> int:
    for index, value in enumerate(sorted(numbers)):
        if index != value:
            return index
    return len(numbers)


class ExperimentSessionMaker:
    def __init__(self, database_url: str, commit: bool = True):
        self._database_url = database_url
        self._commit = commit

    def __call__(self) -> ExperimentSession:
        return ExperimentSession(database_url=self._database_url, commit=self._commit)


DATABASE_URL = "postgresql+psycopg2://caqtus:Deardear@localhost/test_database"


def get_standard_experiment_session_maker() -> ExperimentSessionMaker:
    return ExperimentSessionMaker(database_url=DATABASE_URL)


def get_standard_experiment_session() -> ExperimentSession:
    return get_standard_experiment_session_maker()()
