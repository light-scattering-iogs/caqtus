from pathlib import Path
from typing import Protocol

import platformdirs
import sqlalchemy
import sqlalchemy.orm
import yaml

from .experiment_session import ExperimentSession


class ExperimentSessionMaker(Protocol):
    """Used to create a new experiment session with predefined parameters."""

    def __call__(self) -> ExperimentSession:
        ...


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

    return PostgreSQLExperimentSessionMaker(
        user=kwargs["user"],
        ip=kwargs["ip"],
        password=kwargs["password"],
        database=kwargs["database"],
    )


def get_standard_experiment_session() -> ExperimentSession:
    return get_standard_experiment_session_maker()()
