from pathlib import Path

import platformdirs
import sqlalchemy
import sqlalchemy.orm
import yaml

from .experiment_session import ExperimentSession


class ExperimentSessionMaker:
    def __init__(
        self,
        user: str,
        ip: str,
        password: str,
        database: str,
    ):
        self._kwargs = {
            "user": user,
            "ip": ip,
            "password": password,
            "database": database,
        }
        database_url = f"postgresql+psycopg2://{user}:{password}@{ip}/{database}"
        self._engine = sqlalchemy.create_engine(database_url)
        self._session_maker = sqlalchemy.orm.sessionmaker(self._engine)

    def __call__(self, async_session: bool = False) -> ExperimentSession:
        """Create a new ExperimentSession"""

        return ExperimentSession(self._session_maker())

    # The following methods are required to make ExperimentSessionMaker pickleable to
    # pass it to other processes. Since sqlalchemy engine is not pickleable, so we just
    # pickle the database info and create a new engine upon unpickling.
    def __getstate__(self) -> dict:
        return self._kwargs

    def __setstate__(self, state: dict):
        self.__init__(**state)


def get_standard_experiment_session_maker() -> ExperimentSessionMaker:
    """Create a default ExperimentSessionMaker.

        This function loads the parameters
    config file. The file must follow the
        format of the following example:

        user: the_name_of_the_database_user
        ip: 192.168.137.1  # The ip of the database server
        password: the_password_to_the_database
        database: the_name_of_the_database
    """

    config_folder = platformdirs.user_config_path(
        appname="ExperimentControl", appauthor="Caqtus"
    )
    path = Path(config_folder) / "default_experiment_session.yaml"
    if not path.exists():
        raise FileNotFoundError(
            "Could not find default_experiment_session.yaml. "
            f"Please create the file at {path}."
        )
    with open(path) as file:
        kwargs = yaml.safe_load(file)

    return ExperimentSessionMaker(**kwargs)


def get_standard_experiment_session() -> ExperimentSession:
    return get_standard_experiment_session_maker()()
